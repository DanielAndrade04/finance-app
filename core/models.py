from django.db import models


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
