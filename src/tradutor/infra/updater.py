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


def clear_pending_update() -> None:
    """Remove os arquivos de atualização pendente e scripts temporários do cache."""
    cache_dir = get_cache_dir()
    for fname in (
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


def run_helper_and_exit(
    pending_exe: Path, pending_json: Path, current_exe: Path | None = None
) -> None:
    """Gera o script auxiliar PowerShell update_helper.ps1, executa-o de forma assíncrona

    e encerra o processo atual imediatamente.
    """
    if not is_frozen_windows():
        raise RuntimeError(
            "Auto-update is only supported when running as a frozen executable on Windows."
        )

    if current_exe is None:
        current_exe = Path(sys.executable)

    pid = os.getpid()
    ps_path = pending_exe.parent / "update_helper.ps1"

    # Script PowerShell robusto que:
    # 1. Espera o processo pai morrer
    # 2. Tenta mover current_exe -> current_exe.old e pending_exe -> current_exe
    # 3. Se tiver sucesso, deleta os arquivos temporários do cache e inicia o novo executável
    # 4. Se falhar, restaura o original se necessário, limpa o cache pendente e relança o app
    # 5. Deleta o script auxiliar
    ps_content = f"""# Script auxiliar de auto-atualizacao tradutor-ebook
$pidToWait = {pid}
$pendingExe = "{pending_exe}"
$pendingJson = "{pending_json}"
$currentExe = "{current_exe}"
$oldExe = "{current_exe}.old"

# 1. Aguarda o processo pai finalizar
try {{
    $process = Get-Process -Id $pidToWait -ErrorAction SilentlyContinue
    if ($process) {{
        $process.WaitForExit(15000)
    }}
}} catch {{}}

Start-Sleep -Seconds 1

# 2. Loop de substituicao atomica
$success = $false
for ($i = 0; $i -lt 15; $i++) {{
    try {{
        if (Test-Path -LiteralPath $oldExe) {{
            Remove-Item -LiteralPath $oldExe -Force -ErrorAction SilentlyContinue
        }}
        if (Test-Path -LiteralPath $currentExe) {{
            Move-Item -LiteralPath $currentExe -Destination $oldExe -Force -ErrorAction Stop
        }}
        Move-Item -LiteralPath $pendingExe -Destination $currentExe -Force -ErrorAction Stop
        $success = $true
        break
    }} catch {{
        Start-Sleep -Seconds 1
    }}
}}

if ($success) {{
    if (Test-Path -LiteralPath $oldExe) {{
        Remove-Item -LiteralPath $oldExe -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path -LiteralPath $pendingJson) {{
        Remove-Item -LiteralPath $pendingJson -Force -ErrorAction SilentlyContinue
    }}
    Start-Process -FilePath $currentExe
}} else {{
    # Fallback em caso de erro: restaura se moveu e limpa o cache pendente
    if (-not (Test-Path -LiteralPath $currentExe) -and (Test-Path -LiteralPath $oldExe)) {{
        Move-Item -LiteralPath $oldExe -Destination $currentExe -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path -LiteralPath $pendingExe) {{
        Remove-Item -LiteralPath $pendingExe -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path -LiteralPath $pendingJson) {{
        Remove-Item -LiteralPath $pendingJson -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path -LiteralPath $currentExe) {{
        Start-Process -FilePath $currentExe
    }}
}}

# 3. Auto-remocao do script
try {{
    Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
}} catch {{}}
"""
    try:
        ps_path.write_text(ps_content, encoding="utf-8")

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps_path),
            ],
            creationflags=creation_flags,
            close_fds=True,
        )
    except Exception:
        clear_pending_update()
        raise

    os._exit(0)
