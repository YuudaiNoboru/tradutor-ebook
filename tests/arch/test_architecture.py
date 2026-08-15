"""Testes de arquitetura: isolamento hexagonal e ausência de vazamento de segredos.

- Escaneia a árvore sintática de cada módulo de ``tradutor.domain`` e
  garante que nenhum importe adaptadores (infra, providers, tui, epub),
  bibliotecas de segredo/IO (keyring, cryptography, httpx, os) nem leia
  variáveis de ambiente.
- Executa os contratos declarativos de ``import-linter`` (definidos em ``pyproject.toml``)
  assegurando que o domínio esteja 100% desacoplado de adaptadores externos e
  que as camadas de core não dependam de interfaces de usuário (TUI/CLI).
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from importlinter.cli import lint_imports

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "src" / "tradutor" / "domain"

FORBIDDEN_MODULES = {
    "keyring",
    "cryptography",
    "httpx",
    "os",
    "sys",
    "platformdirs",
    "tomllib",
    "tradutor.infra",
    "tradutor.providers",
    "tradutor.tui",
    "tradutor.epub",
    "tradutor.translate",
}

ALLOWED_STDLIB = {"dataclasses", "typing", "re", "enum", "collections"}


def _domain_sources() -> list[tuple[Path, ast.Module]]:
    sources = []
    for path in sorted(DOMAIN_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        sources.append((path, tree))
    return sources


def test_domain_nao_importa_adaptadores_ou_segredos() -> None:
    for path, tree in _domain_sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_MODULES, (
                        f"{path.name}: importa {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert module.split(".")[0] not in FORBIDDEN_MODULES, (
                    f"{path.name}: importa {module}"
                )
                if module.startswith("tradutor"):
                    assert module.startswith("tradutor.domain"), f"{path.name}: importa {module}"


def test_domain_nao_le_variaveis_de_ambiente() -> None:
    for path, tree in _domain_sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                assert not (node.value.id == "os" and node.attr == "environ"), (
                    f"{path.name}: acessa os.environ"
                )
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in {"getenv", "environ"}:
                    raise AssertionError(f"{path.name}: chama {func.id}()")


def test_domain_declara_apenas_a_porta_de_segredos() -> None:
    port_file = DOMAIN_DIR / "secrets.py"
    tree = ast.parse(port_file.read_text(encoding="utf-8"), filename=str(port_file))

    method_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name != "get"
    ]
    assert method_names == [], f"porta SecretStore expoe metodos extras: {method_names}"


def test_import_linter_hexagonal_contracts() -> None:
    """Valida programaticamente que todos os contratos do import-linter estão cumpridos."""
    existing_loggers = {
        name: logger.disabled
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    try:
        exit_code = lint_imports()
        assert exit_code == 0, "Contratos de camadas do import-linter violados."
    finally:
        for name, was_disabled in existing_loggers.items():
            logger = logging.root.manager.loggerDict.get(name)
            if isinstance(logger, logging.Logger):
                logger.disabled = was_disabled
