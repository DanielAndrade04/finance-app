from datetime import datetime

from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.models import Transaction, CreditCard
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
        cartao_id = request.POST.get("cartao_credito")
        data = datetime.strptime(data_str, "%Y-%m-%d")

        # validações mínimas
        if not tipo or not valor or not data:
            messages.error(request, "Preencha todos os campos obrigatórios.")
            return redirect('new_transaction')

        # normaliza método de pagamento: só se for gasto
        payment_method = metodo if (tipo == 'gasto') else ''

        valor = limpar_mascara_moeda(valor)

        # Verifica se é transação de crédito e determina o mês de faturamento
        billing_month = None
        billing_year = None
        credit_card = None

        if metodo == 'credito' and cartao_id:
            credit_card = CreditCard.objects.get(id=cartao_id)
            billing_month, billing_year = credit_card.get_billing_month_for_date(data)

        # cria a transação
        transaction = Transaction.objects.create(
            transaction_type=tipo,
            description=descricao or '',
            value=valor,
            payment_method=payment_method,
            category=categoria,
            date=data,
            credit_card=credit_card,
            billing_month=billing_month,
            billing_year=billing_year
        )

        # Salva no Google Sheets no mês correto
        if billing_month and billing_year:
            sheets_service.save_transaction(transaction, billing_year, billing_month)
        else:
            sheets_service.save_transaction(transaction)

        messages.success(request, "Transação criada com sucesso!")
        return redirect('new_transaction')

    # GET - Busca cartões ativos
    cartoes = CreditCard.objects.filter(active=True)
    return render(request, 'new_transaction.html', {'cartoes': cartoes})


def edit_transaction(request, id):
    transacao = get_object_or_404(Transaction, id=id)

    # Salva os dados antigos para comparar depois
    old_date = transacao.date
    old_payment_method = transacao.payment_method
    old_credit_card = transacao.credit_card

    if request.method == "POST":
        # Atualiza no banco Django
        transacao.description = request.POST.get("descricao")
        transacao.value = limpar_mascara_moeda(request.POST.get("valor"))

        nova_data = datetime.strptime(request.POST.get("data"), "%Y-%m-%d").date()
        transacao.date = nova_data

        transacao.transaction_type = request.POST.get("tipo")
        transacao.category = request.POST.get("categoria")
        transacao.payment_method = request.POST.get("pagamento")

        # Atualiza cartão de crédito e mês de faturamento
        cartao_id = request.POST.get("cartao_credito")
        if cartao_id:
            transacao.credit_card = CreditCard.objects.get(id=cartao_id)
            # Recalcula o mês de faturamento baseado na nova data
            billing_month, billing_year = transacao.credit_card.get_billing_month_for_date(
                nova_data)
            transacao.billing_month = billing_month
            transacao.billing_year = billing_year
        else:
            transacao.credit_card = None
            transacao.billing_month = None
            transacao.billing_year = None

        transacao.save()

        # Determina se precisa mover a transação entre planilhas
        precisa_mover = False
        old_year, old_month = old_date.year, old_date.month
        new_year, new_month = nova_data.year, nova_data.month

        # Se é transação de crédito, usa o mês de faturamento
        if transacao.payment_method == 'credito' and transacao.credit_card:
            new_year, new_month = transacao.billing_year, transacao.billing_month
            # Para crédito, sempre verifica se o mês de faturamento mudou
            precisa_mover = True

        # Para débito ou mudança de ano/mês, verifica se a data mudou significativamente
        elif (old_year != new_year or old_month != new_month):
            precisa_mover = True

        # Se o método de pagamento mudou (de crédito para débito ou vice-versa)
        if old_payment_method != transacao.payment_method:
            precisa_mover = True

        if precisa_mover:
            # Move a transação para a planilha correta
            if sheets_service.move_transaction(transacao, old_year, old_month, new_year,
                                               new_month):
                messages.success(request, "Transação atualizada e movida para o mês correto!")
            else:
                messages.error(request,
                               "Transação atualizada, mas houve erro ao mover entre planilhas.")
        else:
            # Apenas atualiza a transação na planilha atual
            if sheets_service.update_transaction(transacao):
                messages.success(request, "Transação atualizada com sucesso!")
            else:
                messages.error(request, "Erro ao atualizar transação no Google Sheets.")

        return redirect("historical")

    # GET - Busca cartões ativos para o formulário
    cartoes = CreditCard.objects.filter(active=True)

    return render(request, "edit_transaction.html", {
        "transacao": transacao,
        "cartoes": cartoes
    })


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
    cartoes = CreditCard.objects.filter(active=True)
    return render(request, 'new_transaction.html', {'cartoes': cartoes})


def historical(request):
    from datetime import datetime
    now = datetime.now()

    # Obtém parâmetros de filtro de data
    ano = request.GET.get("ano", now.year)
    mes = request.GET.get("mes", now.month)

    # Converte para inteiros
    try:
        ano = int(ano)
        mes = int(mes)
    except (ValueError, TypeError):
        ano = now.year
        mes = now.month

    # Garante que os valores estão dentro dos limites
    if mes < 1 or mes > 12:
        mes = now.month
    if ano < 2000 or ano > 2100:
        ano = now.year

    # Busca transações do mês/ano selecionado
    transactions = sheets_service.get_transactions(ano, mes)

    # aplica filtros adicionais
    busca = request.GET.get("busca")
    tipo = request.GET.get("tipo")
    categoria = request.GET.get("categoria")
    pagamento = request.GET.get("pagamento")

    # parâmetros de ordenação
    order_by = request.GET.get("order_by", "data")
    direction = request.GET.get("direction", "desc")

    if busca:
        transactions = [t for t in transactions if
                        busca and busca.lower() in str(t.get("descricao", "")).lower()]
    if tipo and tipo != "todos":
        transactions = [t for t in transactions if t.get("tipo") == tipo]
    if categoria and categoria != "todas":
        transactions = [t for t in transactions if t.get("categoria") == categoria]
    if pagamento and pagamento != "todos":
        transactions = [t for t in transactions if t.get("pagamento") == pagamento]

    # função de ordenação personalizada para valor
    def get_sort_key(item, field):
        if field == 'valor':
            # Remove "R$" e converte para float para ordenação numérica
            valor_str = str(item.get('valor', '0')).replace('R$', '').replace('.', '').replace(',',
                                                                                               '.').strip()
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

    # Gera lista de anos disponíveis (últimos 10 anos + próximos 2)
    anos_disponiveis = list(range(now.year - 0, now.year + 2))

    return render(
        request,
        "historical.html",
        {
            "transactions": page_obj,
            "paginator": paginator,
            "page_obj": page_obj,
            "order_by": order_by,
            "direction": direction,
            "query_string": query_string,
            "ano_selecionado": ano,
            "mes_selecionado": mes,
            "anos_disponiveis": anos_disponiveis,
            "meses_disponiveis": [
                (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
                (4, "Abril"), (5, "Maio"), (6, "Junho"),
                (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
                (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
            ]
        }
    )


def reports(request):
    return render(request, 'reports.html')


# def cards(request):
#     return render(request, 'cards.html')


def cards(request):
    cartoes = CreditCard.objects.filter(active=True)
    return render(request, 'cards.html', {'cartoes': cartoes})


def create_card(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        closing_day = int(request.POST.get('closing_day'))
        due_day = int(request.POST.get('due_day'))
        limit = request.POST.get('limit').replace('R$', '').replace('.', '').replace(',',
                                                                                     '.').strip()

        try:
            CreditCard.objects.create(
                name=name,
                closing_day=closing_day,
                due_day=due_day,
                limit=float(limit)
            )
            messages.success(request, 'Cartão criado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao criar cartão: {str(e)}')

        return redirect('cards')

    return render(request, 'create_card.html')


def edit_card(request, id):
    cartao = get_object_or_404(CreditCard, id=id)

    if request.method == 'POST':
        cartao.name = request.POST.get('name')
        cartao.closing_day = int(request.POST.get('closing_day'))
        cartao.due_day = int(request.POST.get('due_day'))
        limit = request.POST.get('limit').replace('R$', '').replace('.', '').replace(',',
                                                                                     '.').strip()
        cartao.limit = float(limit)
        cartao.save()

        messages.success(request, 'Cartão atualizado com sucesso!')
        return redirect('cards')

    return render(request, 'edit_card.html', {'cartao': cartao})


def delete_card(request, id):
    cartao = get_object_or_404(CreditCard, id=id)

    if request.method == 'POST':
        cartao.active = False
        cartao.save()
        messages.success(request, 'Cartão excluído com sucesso!')
        return redirect('cards')

    return render(request, 'delete_card.html', {'cartao': cartao})