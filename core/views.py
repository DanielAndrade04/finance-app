from datetime import datetime

from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.models import Transaction
from core.services.sheets_service import GoogleSheetsService
from core.utils import limpar_mascara_moeda

sheets_service = GoogleSheetsService()

# mapeia o valor do front -> nome legível no banco
CATEGORY_MAP = {
    'alimentacao': 'Alimentação',
    'transporte': 'Transporte',
    'moradia': 'Moradia',
    'salario': 'Salário',
    'lazer': 'Lazer',
    'educacao': 'Educação',
}


def create_transaction(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo")
        descricao = request.POST.get("descricao")
        valor = request.POST.get("valor")
        metodo = request.POST.get("metodo_pagamento")
        categoria = request.POST.get("categoria")
        data_str = request.POST.get("data")
        data = datetime.strptime(data_str, "%Y-%m-%d")

        # validações mínimas
        if not tipo or not valor or not data:
            messages.error(request, "Preencha todos os campos obrigatórios.")
            return redirect('new_transaction')

        # normaliza método de pagamento: só se for gasto
        payment_method = metodo if (tipo == 'gasto') else ''

        valor = limpar_mascara_moeda(valor)

        # cria a transação
        transaction = Transaction.objects.create(
            transaction_type=tipo,
            description=descricao or '',
            value=valor,
            payment_method=payment_method,
            category=categoria,
            date=data
        )
        sheets_service.save_transaction(transaction)

        messages.success(request, "Transação criada com sucesso!")
        return redirect('new_transaction')   # volta para a tela de nova transação

    # GET
    return render(request, 'new_transaction.html')


def edit_transaction(request, id):
    transacao = get_object_or_404(Transaction, id=id)

    if request.method == "POST":
        # Atualiza no banco Django
        transacao.description = request.POST.get("descricao")
        transacao.value = limpar_mascara_moeda(request.POST.get("valor"))
        transacao.date = datetime.strptime(request.POST.get("data"), "%Y-%m-%d").date()
        transacao.transaction_type = request.POST.get("tipo")
        transacao.category = request.POST.get("categoria")
        transacao.payment_method = request.POST.get("pagamento")
        transacao.save()

        # Atualiza no Google Sheets
        if sheets_service.update_transaction(transacao):
            messages.success(request, "Transação atualizada com sucesso!")
        else:
            messages.error(request, "Erro ao atualizar transação no Google Sheets.")

        return redirect("historical")

    return render(request, "edit_transaction.html", {"transacao": transacao})


def delete_transaction(request, id):
    transacao = get_object_or_404(Transaction, id=id)

    if request.method == "POST":
        # Salva os dados antes de deletar para usar no Google Sheets
        transaction_id = transacao.id
        year = transacao.date.year
        month = transacao.date.month

        # Deleta do banco Django
        transacao.delete()

        # Deleta do Google Sheets
        if sheets_service.delete_transaction(transaction_id, year, month):
            messages.success(request, "Transação excluída com sucesso!")
        else:
            messages.error(request, "Erro ao excluir transação do Google Sheets.")

        return redirect("historical")

    return render(request, "delete_transaction.html", {"transacao": transacao})


def dashboard(request):
    return render(request, 'dashboard.html')


def new_trasaction(request):
    return render(request, 'new_transaction.html')


def historical(request):
    from datetime import datetime
    now = datetime.now()
    transactions = sheets_service.get_transactions(now.year, now.month)

    # aplica filtros
    busca = request.GET.get("busca")
    tipo = request.GET.get("tipo")
    categoria = request.GET.get("categoria")
    pagamento = request.GET.get("pagamento")

    # parâmetros de ordenação
    order_by = request.GET.get("order_by", "data")
    direction = request.GET.get("direction", "desc")

    if busca:
        transactions = [t for t in transactions if busca.lower() in str(t["descricao"]).lower()]
    if tipo and tipo != "todos":
        transactions = [t for t in transactions if t["tipo"] == tipo]
    if categoria and categoria != "todas":
        transactions = [t for t in transactions if t["categoria"] == categoria]
    if pagamento and pagamento != "todos":
        transactions = [t for t in transactions if t["pagamento"] == pagamento]

    # função de ordenação personalizada para valor
    def get_sort_key(item, field):
        if field == 'valor':
            # Remove "R$" e converte para float para ordenação numérica
            valor_str = str(item.get('valor', '0')).replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(valor_str)
            except ValueError:
                return 0.0
        elif field == 'data':
            # Converte string de data para objeto datetime para ordenação correta
            data_str = item.get('data', '')
            try:
                return datetime.strptime(data_str, '%d/%m/%Y')
            except ValueError:
                return datetime.min
        else:
            return item.get(field, '')

    # aplica ordenação
    reverse = direction == 'desc'
    transactions.sort(key=lambda x: get_sort_key(x, order_by), reverse=reverse)

    # mantém os parâmetros de filtro na paginação
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    query_string = params.urlencode()

    # paginação
    paginator = Paginator(transactions, 10)  # 10 por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "historical.html",
        {
            "transactions": page_obj,
            "paginator": paginator,
            "page_obj": page_obj,
            "order_by": order_by,
            "direction": direction,
            "query_string": query_string
        }
    )


def reports(request):
    return render(request, 'reports.html')


def cards(request):
    return render(request, 'cards.html')
