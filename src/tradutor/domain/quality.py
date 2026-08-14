"""Qualidade da saida: deteccao de marcas de traducao automatica.

O texto de saida deve fluir como livro publicado: sem colchetes, notas,
rotulos de traducao ou outras marcas de IA (spec "Saida apenas
traduzida"). ``has_ai_mark`` e uma funcao pura usada nos testes (5.6) e
pela orquestracao para rejeitar respostas sujas.
"""

from __future__ import annotations

import re
import unicodedata

_AI_MARK_PATTERNS = (
    re.compile(r"\[[^\]]*(?:tradu[çc][aã]o|original|nt\.)[^\]]*\]", re.IGNORECASE),
    re.compile(r"\(\s*n\.?\s*t\.?\s*\)", re.IGNORECASE),
    re.compile(r"nota\s+(?:do|da)\s+tradutor", re.IGNORECASE),
    re.compile(r"traduzid[oa]\s+(?:por|com)\s+(?:ia|intelig[eê]ncia\s+artificial)", re.IGNORECASE),
    re.compile(
        r"tradu[çc][aã]o\s+(?:automatica|automática|gerada|feita)\s+(?:por|com|via)", re.IGNORECASE
    ),
    re.compile(r"^\s*original:", re.IGNORECASE | re.MULTILINE),
)

_MOJIBAKE_MAP: tuple[tuple[str, str], ...] = (
    # Traços e pontuação tipográfica (double encoding Windows-1252 e ISO-8859-1 / Latin-1)
    ("â€“", "–"),
    ("â\x80\x93", "–"),
    ("â€”", "—"),
    ("â\x80\x94", "—"),
    ("â€œ", "“"),
    ("â€\x9c", "“"),
    ("â\x80\x9c", "“"),
    ("â€ ", "”"),
    ("â€\x9d", "”"),
    ("â\x80\x9d", "”"),
    ("â€˜", "‘"),
    ("â€\x98", "‘"),
    ("â\x80\x98", "‘"),
    ("â€™", "’"),
    ("â€\x99", "’"),
    ("â\x80\x99", "’"),
    ("â€¦", "…"),
    ("â\x80\xa6", "…"),
    ("â€¢", "•"),
    ("â\x80\xa2", "•"),
    ("â€º", "›"),
    ("â\x80\xba", "›"),
    ("â€‹", "‹"),
    ("â\x80\xb9", "‹"),
    ("â„¢", "™"),
    ("â\x84\xa2", "™"),
    # Espaços e símbolos com Â (U+00C2)
    ("Â\xa0", "\xa0"),
    ("Â ", " "),
    ("Â«", "«"),
    ("Â»", "»"),
    ("Â°", "°"),
    ("Â©", "©"),
    ("Â®", "®"),
    ("Â±", "±"),
    ("Â§", "§"),
    ("Âµ", "µ"),
    ("Â¿", "¿"),
    ("Â¡", "¡"),
    # Letras minúsculas acentuadas e cedilha com Ã (U+00C3)
    ("Ã¡", "á"),
    ("Ã ", "à"),
    ("Ã¢", "â"),
    ("Ã£", "ã"),
    ("Ã¤", "ä"),
    ("Ã¥", "å"),
    ("Ã¦", "æ"),
    ("Ã§", "ç"),
    ("Ã©", "é"),
    ("Ã¨", "è"),
    ("Ãª", "ê"),
    ("Ã«", "ë"),
    ("Ã­", "í"),
    ("Ã¬", "ì"),
    ("Ã®", "î"),
    ("Ã¯", "ï"),
    ("Ã±", "ñ"),
    ("Ã³", "ó"),
    ("Ã²", "ò"),
    ("Ã´", "ô"),
    ("Ãµ", "õ"),
    ("Ã¶", "ö"),
    ("Ã¸", "ø"),
    ("Ãº", "ú"),
    ("Ã¹", "ù"),
    ("Ã»", "û"),
    ("Ã¼", "ü"),
    ("Ã½", "ý"),
    ("Ã¿", "ÿ"),
    # Letras maiúsculas acentuadas e cedilha com Ã (U+00C3)
    ("Ã\x81", "Á"),
    ("Ã€", "À"),
    ("Ã‚", "Â"),
    ("Ãƒ", "Ã"),
    ("Ã„", "Ä"),
    ("Ã…", "Å"),
    ("Ã†", "Æ"),
    ("Ã‡", "Ç"),
    ("Ã‰", "É"),
    ("Ãˆ", "È"),
    ("ÃŠ", "Ê"),
    ("Ã‹", "Ë"),
    ("Ã\x8d", "Í"),
    ("ÃŒ", "Ì"),
    ("ÃŽ", "Î"),
    ("Ã\x8f", "Ï"),
    ("Ã‘", "Ñ"),
    ("Ã“", "Ó"),
    ("Ã’", "Ò"),
    ("Ã”", "Ô"),
    ("Ã•", "Õ"),
    ("Ã–", "Ö"),
    ("Ã˜", "Ø"),
    ("Ãš", "Ú"),
    ("Ã™", "Ù"),
    ("Ã›", "Û"),
    ("Ãœ", "Ü"),
    ("Ã\x9d", "Ý"),
)


def has_ai_mark(text: str) -> bool:
    """True se o texto contem padrao tipico de saida de IA/tradutor."""
    return any(pattern.search(text) for pattern in _AI_MARK_PATTERNS)


def sanitize_pre_send(text: str) -> str:
    """Normaliza texto em Unicode NFC e sanitiza espacos nao-quebraveis (\xa0) e caracteres nulos."""
    if not text:
        return ""
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\x00", "")
    text = text.replace("\u00a0", " ")
    return unicodedata.normalize("NFC", text)


def has_mojibake(text: str) -> bool:
    """True se o texto contem sequencias tipicas de mojibake/double-encoding."""
    if not text:
        return False
    return any(wrong in text for wrong, _ in _MOJIBAKE_MAP)


def fix_mojibake(text: str) -> str:
    """Corrige deterministicamente sequencias tipicas de mojibake e double-encoding."""
    if not text:
        return ""
    for wrong, right in _MOJIBAKE_MAP:
        if wrong in text:
            text = text.replace(wrong, right)
    return unicodedata.normalize("NFC", text)
