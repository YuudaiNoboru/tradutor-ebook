"""Excecoes da camada EPUB (leitura e escrita)."""


class EpubError(Exception):
    """Erro generico da camada EPUB."""


class NotEpubError(EpubError):
    """O arquivo nao e um EPUB (nao e um ZIP valido)."""


class MalformedEpubError(EpubError):
    """EPUB estruturalmente invalido; o modo reparo pode reconstrui-lo."""


class DrmError(EpubError):
    """Livro protegido por DRM (ou com conteudo criptografado)."""
