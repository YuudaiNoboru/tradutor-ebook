"""Script utilitário para compilação do instalador Windows oficial via Inno Setup.

Localiza o compilador ISCC.exe, verifica os pré-requisitos (dist/tradutor.exe)
e gera o instalador dist/tradutor-ebook-setup.exe.
"""

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ISS_SCRIPT = PROJECT_ROOT / "installer" / "tradutor-setup.iss"
DIST_DIR = PROJECT_ROOT / "dist"
EXE_PATH = DIST_DIR / "tradutor.exe"
ASSETS_ICO = PROJECT_ROOT / "assets" / "app.ico"


def get_version() -> str:
    """Obtém a versão atual do pacote a partir de tradutor.__version__."""
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    try:
        import tradutor

        return str(getattr(tradutor, "__version__", "0.6.0"))
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


def find_iscc() -> Path | None:
    """Busca o compilador ISCC.exe no PATH ou em locais padrão do Windows."""
    # 1. Checa se iscc está no PATH do sistema
    which_path = shutil.which("ISCC.exe") or shutil.which("iscc")
    if which_path:
        return Path(which_path)

    # 2. Locais de instalação comuns no Windows
    candidate_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
        Path.home() / r"AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    ]

    for path in candidate_paths:
        if path.is_file():
            return path

    return None


def build_installer() -> int:
    """Executa a compilação do instalador Inno Setup."""
    version = get_version()
    print(f"==> Preparando build do instalador para LiberLingua v{version}")

    # Validação do arquivo de configuração .iss
    if not ISS_SCRIPT.exists():
        print(f"[ERRO] Script Inno Setup não encontrado: {ISS_SCRIPT}", file=sys.stderr)
        return 1

    # Validação do ícone
    if not ASSETS_ICO.exists():
        print(
            f"[AVISO] Ícone {ASSETS_ICO} não encontrado. Gerando ativos visuais...",
            file=sys.stderr,
        )
        from generate_icons import generate_assets

        generate_assets()

    # Validação do executável standalone
    if not EXE_PATH.exists():
        print(
            f"[ERRO] Executável {EXE_PATH} não encontrado.\n"
            f"Compile primeiro o binário com o PyInstaller executando:\n"
            f"  hatch run pyinstaller --onefile --windowed --icon=assets/app.ico --name tradutor src/tradutor/cli.py",
            file=sys.stderr,
        )
        return 1

    # Busca pelo compilador ISCC
    iscc_path = find_iscc()
    if not iscc_path:
        print(
            "\n[ERRO] Compilador Inno Setup (ISCC.exe) não foi encontrado no sistema.\n"
            "Para instalar o Inno Setup no Windows:\n"
            "  - Via winget:  winget install JRSoftware.InnoSetup\n"
            "  - Via Chocolatey: choco install innosetup\n"
            "  - Manualmente: https://jrsoftware.org/isinfo.php\n",
            file=sys.stderr,
        )
        return 1

    print(f"==> Compilador Inno Setup encontrado: {iscc_path}")
    print(f"==> Compilando instalador: {ISS_SCRIPT} (Versão: {version})")

    cmd = [
        str(iscc_path),
        f"/DMyAppVersion={version}",
        str(ISS_SCRIPT),
    ]

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode == 0:
        setup_exe = DIST_DIR / "tradutor-ebook-setup.exe"
        print(f"\n[SUCESSO] Instalador gerado com sucesso em: {setup_exe}")
    else:
        print("\n[ERRO] Falha na compilação do instalador.", file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(build_installer())
