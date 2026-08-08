"""Módulo de infraestrutura para o auto-atualizador do Windows."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import platformdirs

APP_NAME = "tradutor-ebook"
GITHUB_REPO = "YuudaiNoboru/tradutor-ebook"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


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


def get_cache_dir() -> Path:
    """Retorna o diretório de cache do usuário para a aplicação."""
    return Path(platformdirs.user_cache_dir(APP_NAME))


def get_pending_update_paths() -> tuple[Path, Path]:
    """Retorna os caminhos dos arquivos de atualização pendente (.exe e .json)."""
    cache_dir = get_cache_dir()
    return cache_dir / "pending_update.exe", cache_dir / "pending_update.json"


def check_for_update(current_version: str, propagate_errors: bool = False) -> dict[str, str] | None:
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

            # Procurar pelo executável Windows (.exe) nos assets
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe"):
                    return {
                        "version": tag_name,
                        "download_url": asset.get("browser_download_url", ""),
                        "filename": name,
                    }
    except Exception:
        if propagate_errors:
            raise
        # Silencia exceções de rede/parse
        pass
    return None


def download_update(download_url: str, target_version: str, filename: str) -> bool:
    """Realiza o download seguro e atômico da nova versão.

    Salva como pending_update.exe e pending_update.json no cache após conclusão.
    """
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    pending_exe, pending_json = get_pending_update_paths()
    temp_exe = cache_dir / "pending_update.exe.tmp"

    try:
        # Remove lixo de tentativas anteriores
        if temp_exe.exists():
            temp_exe.unlink()

        with (
            httpx.Client(follow_redirects=True, timeout=httpx.Timeout(30.0, read=10.0)) as client,
            client.stream("GET", download_url) as response,
        ):
            response.raise_for_status()
            with open(temp_exe, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        # Download concluído com sucesso, faz a transição atômica
        if pending_exe.exists():
            pending_exe.unlink()
        temp_exe.rename(pending_exe)

        manifest = {
            "version": target_version,
            "filename": filename,
        }
        pending_json.write_text(json.dumps(manifest), encoding="utf-8")
        return True
    except Exception:
        if temp_exe.exists():
            with contextlib.suppress(Exception):
                temp_exe.unlink()
        return False


def check_delayed_update(current_version: str) -> dict[str, str] | None:
    """Checa se existe uma atualização pendente já baixada em cache que seja

    mais recente que a versão atual.
    """
    pending_exe, pending_json = get_pending_update_paths()
    if not pending_exe.exists() or not pending_json.exists():
        return None

    try:
        manifest = json.loads(pending_json.read_text(encoding="utf-8"))
        version = manifest.get("version", "")
        if parse_version(version) > parse_version(current_version):
            return {
                "version": version,
                "filename": manifest.get("filename", "tradutor.exe"),
                "exe_path": str(pending_exe),
                "json_path": str(pending_json),
            }
    except Exception:
        pass
    return None


def run_helper_and_exit(pending_exe: Path, pending_json: Path, current_exe: Path | None = None):
    """Gera o script batch update_helper.bat, executa-o de forma assíncrona/desconectada,

    e finaliza o processo atual.
    """
    if not is_frozen_windows():
        raise RuntimeError(
            "Auto-update is only supported when running as a frozen executable on Windows."
        )

    if current_exe is None:
        current_exe = Path(sys.executable)

    pid = os.getpid()
    bat_path = pending_exe.parent / "update_helper.bat"

    # Script batch robusto que:
    # 1. Espera o processo com o PID pai morrer
    # 2. Tenta copiar pending_exe sobre current_exe
    # 3. Se falhar (ex: acesso negado), tenta relançar o original, limpa o cache e sai
    # 4. Se der certo, deleta os arquivos temporários do cache e inicia o novo executável
    # 5. Deleta a si mesmo
    bat_content = f"""@echo off
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

copy /Y "{pending_exe}" "{current_exe}" >nul
if errorlevel 1 (
    start "" "{current_exe}"
    del /Q "{pending_exe}" >nul
    del /Q "{pending_json}" >nul
    (goto) 2>nul & del "%~f0" & exit
)

del /Q "{pending_exe}" >nul
del /Q "{pending_json}" >nul

start "" "{current_exe}"
(goto) 2>nul & del "%~f0" & exit
"""
    try:
        bat_path.write_text(bat_content, encoding="utf-8")

        # Executa o .bat desconectado sem abrir janela visível
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        subprocess.Popen(
            [str(bat_path)],
            shell=True,
            creationflags=creation_flags,
            close_fds=True,
        )
    except Exception:
        pass

    sys.exit(0)
