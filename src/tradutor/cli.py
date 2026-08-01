"""Entry point da CLI ``tradutor``.

A TUI completa (Textual) chega nas tarefas da secao 9; por ora este
modulo apenas confirma a instalacao.
"""

from __future__ import annotations

from tradutor import __version__


def main() -> int:
    print(f"tradutor-ebook {__version__} (instalado com sucesso)")
    print("A interface ainda esta em desenvolvimento.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
