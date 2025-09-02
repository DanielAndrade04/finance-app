from datetime import datetime

from django import template

register = template.Library()


@register.filter
def moeda(valor):
    try:
        valor = float(valor)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"


@register.filter()
def data(data):
    try:
        data_obj = datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
        return data_obj.strftime("%d/%m/%Y")
    except ValueError:
        return "Data inválida"


@register.simple_tag
def current_filters(get_params, exclude=None):
    """
    Retorna os filtros atuais da querystring sem o parâmetro 'exclude'
    """
    if not get_params:
        return ""

    exclude = exclude or ""
    filters = get_params.copy()

    if exclude in filters:
        filters.pop(exclude)

    if filters:
        return "&".join([f"{key}={value}" for key, value in filters.items() if value])
    return ""


@register.filter
def get_item(dictionary, key):
    """Retorna o valor de um dicionário pela chave"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)

    # Para a lista de meses, que é uma lista de tuplas
    for item in dictionary:
        if item[0] == key:
            return item[1]
    return ""
