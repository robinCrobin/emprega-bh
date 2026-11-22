"""Normalização de texto usada na carga e na busca (mesma regra nos dois lados)."""
import re
import unicodedata


def normalizar_texto(valor: str) -> str:
    """Minúsculas, sem acentos e com pontuação reduzida a espaços simples."""
    sem_acento = ''.join(
        c for c in unicodedata.normalize('NFKD', valor or '')
        if not unicodedata.combining(c)
    )
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', sem_acento.lower()).split())
