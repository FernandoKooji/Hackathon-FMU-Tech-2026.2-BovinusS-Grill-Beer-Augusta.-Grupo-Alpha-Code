import unicodedata


def chave_prato(nome: str) -> str:
    """Compara nomes equivalentes sem alterar a grafia usada na apresentação."""
    return unicodedata.normalize("NFC", nome).casefold()
