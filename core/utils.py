def limpar_mascara_moeda(valor):
    """
    Converte valor formatado (R$ 1.234,56) para float (1234.56)
    """
    if isinstance(valor, (int, float)):
        return float(valor)

    # Remove R$, pontos e espaços
    valor_limpo = valor.replace('R$', '').replace('.', '').replace(' ', '').strip()

    # Substitui vírgula por ponto para converter para float
    valor_limpo = valor_limpo.replace(',', '.')

    try:
        return float(valor_limpo)
    except ValueError:
        return 0.0