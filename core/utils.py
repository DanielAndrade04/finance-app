def limpar_mascara_moeda(valor_formatado):
    valor_limpo = valor_formatado.replace("R$", "").replace(" ", "").replace(".", "")
    valor_limpo = valor_limpo.replace(",", ".")
    return float(valor_limpo)
