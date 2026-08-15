"""Módulo de infraestrutura para o auto-atualizador do Windows."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

import httpx
import platformdirs

APP_NAME = "tradutor-ebook"
GITHUB_REPO = "YuudaiNoboru/tradutor-ebook"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SETUP_FILENAME = "tradutor-ebook-setup.exe"


def parse_version(v_str: str) -> tuple[int, ...]:
    """Converte uma string de versão (ex: 'v0.4.0' ou '0.3.1') em uma tupla de inteiros."""
    cleaned = v_str.lstrip("vV")
    try:
        return tuple(int(x) for x in cleaned.split("."))
    except ValueError:
        return (0,)


def is_frozen_windows() -> bool:
    """Retorna True se estiver rodando como executável compilado no Windows."""
    return getattr(sys, "frozen", False) and sys.platform == "win32"


def is_installed_mode(executable_path: Path | None = None) -> bool:
    """Retorna True se o aplicativo estiver instalado via instalador (com desinstalador unins000.exe)."""
    if not is_frozen_windows() and executable_path is None:
        return False
    exe = executable_path if executable_path is not None else Path(sys.executable)
    return (exe.parent / "unins000.exe").is_file()


def get_cache_dir() -> Path:
    """Retorna o diretório de cache do usuário para a aplicação."""
    return Path(platformdirs.user_cache_dir(APP_NAME))


def get_installer_path(filename: str = SETUP_FILENAME) -> Path:
    """Retorna o caminho do instalador baixado no cache."""
    return get_cache_dir() / filename


def clear_pending_update() -> None:
    """Remove os arquivos de atualização temporários e instaladores do cache."""
    cache_dir = get_cache_dir()
    for fname in (
        SETUP_FILENAME,
        f"{SETUP_FILENAME}.tmp",
        "pending_update.exe",
        "pending_update.json",
        "pending_update.exe.tmp",
        "update_helper.ps1",
        "update_helper.bat",
    ):
        f = cache_dir / fname
        if f.exists():
            with contextlib.suppress(Exception):
                f.unlink()


def check_for_update(
    current_version: str,
    propagate_errors: bool = False,
    executable_path: Path | None = None,
) -> dict[str, Any] | None:
    """Consulta o GitHub Releases para checar se há uma versão mais recente.

    Retorna um dicionário com informações se houver nova versão, senão None.
    """
    headers = {"User-Agent": "tradutor-ebook-updater"}
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(GITHUB_API_URL, headers=headers)
            response.raise_for_status()
            data = response.json()

            tag_name = data.get("tag_name", "")
            if not tag_name:
                return None

            if parse_version(tag_name) <= parse_version(current_version):
                return None

            installed = is_installed_mode(executable_path)
            release_url = data.get(
                "html_url", f"https://github.com/{GITHUB_REPO}/releases/tag/{tag_name}"
            )

            download_url = ""
            filename = ""

            # Se estiver no modo instalado, busca o instalador nos assets
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.lower().endswith("setup.exe") or name == SETUP_FILENAME:
                    download_url = asset.get("browser_download_url", "")
                    filename = name
                    break

            # Se não encontrou o setup específico, mas achou outro .exe instalador
            if installed and not download_url:
                for asset in data.get("assets", []):
                    name = asset.get("name", "")
                    if name.lower().endswith(".exe") and "setup" in name.lower():
                        download_url = asset.get("browser_download_url", "")
                        filename = name
                        break

            return {
                "version": tag_name,
                "is_installed": installed and bool(download_url),
                "release_url": release_url,
                "download_url": download_url,
                "filename": filename or SETUP_FILENAME,
            }
    except Exception:
        if propagate_errors:
            raise
        pass
    return None


def download_update(
    download_url: str,
    target_version: str = "",
    filename: str = SETUP_FILENAME,
) -> bool:
    """Realiza o download seguro e atômico do instalador de atualização.

    Salva no diretório de cache e valida integridade básica (cabeçalho MZ e tamanho).
    """
    if not download_url:
        return False

    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    dest_file = cache_dir / filename
    temp_file = cache_dir / f"{filename}.tmp"

    try:
        if temp_file.exists():
            temp_file.unlink()

        with (
            httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60.0, read=15.0)) as client,
            client.stream("GET", download_url) as response,
        ):
            response.raise_for_status()
            with open(temp_file, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=16384):
                    f.write(chunk)

        # Validação básica de integridade do executável Windows (tamanho > 0 e cabeçalho PE "MZ")
        if not temp_file.exists() or temp_file.stat().st_size < 1024:
            raise ValueError("Arquivo de instalador baixado é inválido ou está vazio.")

        with open(temp_file, "rb") as f:
            header = f.read(2)
            if header != b"MZ":
                raise ValueError(
                    "Arquivo baixado não possui cabeçalho de executável Windows válido."
                )

        if dest_file.exists():
            dest_file.unlink()
        temp_file.rename(dest_file)
        return True
    except Exception:
        if temp_file.exists():
            with contextlib.suppress(Exception):
                temp_file.unlink()
        return False


def launch_installer_and_exit(installer_path: Path | None = None) -> None:
    """Dispara o instalador oficial de atualização e encerra o processo da aplicação."""
    if installer_path is None:
        installer_path = get_installer_path()

    if not installer_path.is_file():
        raise FileNotFoundError(f"Instalador não encontrado em: {installer_path}")

    # Executa o instalador diretamente sem janelas ocultas ou scripts PowerShell
    subprocess.Popen([str(installer_path)], close_fds=True)

    # Encerra o processo atual para liberar os arquivos para o instalador
    os._exit(0)


def open_release_url(url: str) -> bool:
    """Abre a URL da release no navegador padrão do usuário."""
    try:
        return webbrowser.open(url)
    except Exception:
        return False
