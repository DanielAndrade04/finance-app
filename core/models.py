from django.db import models


class CreditCard(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome do Cartão")
    closing_day = models.PositiveIntegerField(verbose_name="Dia de Fechamento",
                                              help_text="Dia do mês em que a fatura fecha")
    due_day = models.PositiveIntegerField(verbose_name="Dia de Vencimento",
                                          help_text="Dia do mês em que a fatura vence")
    limit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Limite")
    active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_current_billing_cycle(self, reference_date=None):
        """Retorna o período de faturamento atual"""
        from datetime import datetime, timedelta
        if reference_date is None:
            reference_date = datetime.now()

        # Se a data atual é antes do dia de fechamento, a fatura é do mês atual
        if reference_date.day <= self.closing_day:
            start_date = datetime(reference_date.year,
                                  reference_date.month - 1 if reference_date.month > 1 else 12,
                                  self.closing_day + 1)
            end_date = datetime(reference_date.year, reference_date.month, self.closing_day)
        else:
            start_date = datetime(reference_date.year, reference_date.month, self.closing_day + 1)
            end_date = datetime(reference_date.year,
                                reference_date.month + 1 if reference_date.month < 12 else 1,
                                self.closing_day)

        return start_date, end_date

    def get_billing_month_for_date(self, transaction_date):
        """Determina em qual mês de fatura uma transação deve cair"""
        from datetime import datetime
        transaction_date = transaction_date if isinstance(transaction_date,
                                                          datetime) else datetime.combine(
            transaction_date, datetime.min.time())

        if transaction_date.day <= self.closing_day:
            # Transação entra na fatura do mês atual
            return transaction_date.month, transaction_date.year
        else:
            # Transação entra na fatura do próximo mês
            if transaction_date.month == 12:
                return 1, transaction_date.year + 1
            else:
                return transaction_date.month + 1, transaction_date.year


class Transaction(models.Model):
    """Dados de receitas ou gastos"""
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('gasto', 'Gasto')
    ]

    CATEGORY_CHOICES = [
        ("alimentacao", "Alimentação"),
        ("transporte", "Transporte"),
        ("salario", "Salário"),
        ("outros", "Outros"),
    ]

    PAYMENT_METHOD = [
        ('credito', 'Crédito'),
        ('debito', 'Debito')
    ]
    value = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TIPO_CHOICES)
    description = models.CharField(max_length=250, blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True)
    credit_card = models.ForeignKey(CreditCard, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name="Cartão de Crédito")
    billing_month = models.PositiveIntegerField(null=True, blank=True,
                                                verbose_name="Mês de Faturamento")
    billing_year = models.PositiveIntegerField(null=True, blank=True,
                                               verbose_name="Ano de Faturamento")
    date = models.DateField(null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'transações'

    def __str__(self):
        """Devolve uma representação em string do modelo"""
        return (f"Valor: R${self.value} - "
                f"Tipo: {self.transaction_type} - "
                f"Categoria: {self.category} - "
                f"Data: {self.date}")
