"""Teste de arquitetura: o nucleo do dominio nunca recebe chaves (tarefa 8.7).

Escaneia a arvore sintatica de cada modulo de ``tradutor.domain`` e
garante que nenhum importe adaptadores (infra, providers, tui, epub),
bibliotecas de segredo/IO (keyring, cryptography, httpx, os) nem leia
variaveis de ambiente. A porta ``SecretStore`` e o unico canal de
acesso a chaves, e os testes de ``tests/providers`` provam que o
adapter a consome.
"""

from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_DIR = Path(__file__).resolve().parents[1] / "src" / "tradutor" / "domain"

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


def test_domain_nao_importa_adaptadores_ou_segredos():
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


def test_domain_nao_le_variaveis_de_ambiente():
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


def test_domain_declara_apenas_a_porta_de_segredos():
    port_file = DOMAIN_DIR / "secrets.py"
    tree = ast.parse(port_file.read_text(encoding="utf-8"), filename=str(port_file))

    method_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name != "get"
    ]
    assert method_names == [], f"porta SecretStore expoe metodos extras: {method_names}"
