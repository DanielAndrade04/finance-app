from core.models import Transaction


def create(request):
    transaction_obj = Transaction(
        valor=request.valor,
        transaction_type=request.transaction_type,
        description=request.description,
        payment_method=request.payment_method,
        name=request.name,
        data=request.data,
        date_added=request.date_added
    )
    return Transaction.save(transaction_obj)
