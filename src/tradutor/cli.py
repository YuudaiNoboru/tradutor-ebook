"""Entry point da CLI ``tradutor``.

Sem argumentos, inicia a TUI (Textual) com o fluxo guiado: boas-vindas,
configuracao, selecao de livro, estimativa, progresso e relatorio.
``--version`` imprime a versao e sai.
"""

from __future__ import annotations

import sys

from tradutor import __version__


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if "--version" in args or "-V" in args:
        print(f"tradutor-ebook {__version__}")
        return 0
    from tradutor.tui.app import TradutorApp

    return TradutorApp().run() or 0


if __name__ == "__main__":
    raise SystemExit(main())
