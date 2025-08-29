import gspread
from google.oauth2.service_account import Credentials


class GoogleSheetsService:
    def __init__(self):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        self.client = gspread.authorize(creds)

    def get_or_create_sheet(self, year, month):
        """Abre ou cria uma sheet para o mês"""
        sheet_name = f"{month:02d}-{year}"
        spreadsheet = self.client.open("Financeiro")

        try:
            return spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")

    def save_transaction(self, transaction):
        """Salva uma transação no mês correspondente"""
        year = transaction.date.year
        month = transaction.date.month
        worksheet = self.get_or_create_sheet(year, month)

        # Cabeçalho (se estiver vazio)
        if not worksheet.row_values(1):
            worksheet.append_row([
                "ID", "Valor", "Tipo", "Descrição",
                "Método Pagamento", "Categoria", "Data", "Data Registro"
            ])

        worksheet.append_row([
            transaction.id,
            float(transaction.value),
            transaction.transaction_type,
            transaction.description,
            transaction.payment_method,
            transaction.category,
            str(transaction.date),
            str(transaction.date_added)
        ])

    def update_transaction(self, transaction):
        """Atualiza uma transação existente no Google Sheets"""
        year = transaction.date.year
        month = transaction.date.month

        try:
            worksheet = self.get_or_create_sheet(year, month)
            records = worksheet.get_all_records()

            # Encontra a linha pelo ID
            for i, record in enumerate(records, start=2):  # start=2 porque a linha 1 é cabeçalho
                if record.get("ID") == transaction.id:
                    # Atualiza a linha
                    worksheet.update(f"A{i}:H{i}", [[
                        transaction.id,
                        float(transaction.value),
                        transaction.transaction_type,
                        transaction.description,
                        transaction.payment_method,
                        transaction.category,
                        str(transaction.date),
                        str(transaction.date_added)
                    ]])
                    return True
            return False
        except Exception as e:
            print(f"Erro ao atualizar transação: {e}")
            return False

    def delete_transaction(self, transaction_id, year, month):
        """Exclui uma transação do Google Sheets"""
        try:
            worksheet = self.get_or_create_sheet(year, month)
            records = worksheet.get_all_records()

            # Encontra a linha pelo ID
            for i, record in enumerate(records, start=2):  # start=2 porque a linha 1 é cabeçalho
                if record.get("ID") == transaction_id:
                    # Deleta a linha
                    worksheet.delete_rows(i)
                    return True
            return False
        except Exception as e:
            print(f"Erro ao excluir transação: {e}")
            return False

    def get_transactions(self, year, month):
        """Retorna todas transações de um mês"""
        sheet_name = f"{month:02d}-{year}"
        try:
            sheet = self.client.open("Financeiro").worksheet(sheet_name)
            data = sheet.get_all_records()

            transactions = []
            for row in data:
                # Formata o valor corretamente
                valor = row.get('Valor', 0)
                if isinstance(valor, (int, float)):
                    valor_formatado = f"R$ {valor:,.2f}".replace(',', 'X').replace('.',
                                                                                   ',').replace(
                        'X', '.')
                else:
                    valor_formatado = f"R$ {valor}"

                transactions.append({
                    "id": row.get("ID"),
                    "descricao": row.get("Descrição"),
                    "valor": valor_formatado,
                    "tipo": row.get("Tipo"),
                    "categoria": row.get("Categoria"),
                    "pagamento": row.get("Método Pagamento"),
                    "data": row.get("Data"),
                    "data_registro": row.get("Data Registro"),
                })
            return transactions
        except Exception as e:
            print(f"Erro ao buscar transações: {e}")
            return []

    def get_transaction_by_id(self, transaction_id, year, month):
        """Busca uma transação específica pelo ID"""
        try:
            worksheet = self.get_or_create_sheet(year, month)
            records = worksheet.get_all_records()

            for record in records:
                if record.get("ID") == transaction_id:
                    return record
            return None
        except Exception as e:
            print(f"Erro ao buscar transação: {e}")
            return None
