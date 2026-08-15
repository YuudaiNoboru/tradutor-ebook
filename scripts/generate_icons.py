"""Script utilitário para gerar os ativos visuais oficiais do projeto.

Lê a imagem do Conceito 6B (Papel Minimalista) e produz:
- assets/logo.png (alta resolução PNG)
- assets/app.ico (ícone multi-resolução Windows: 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256)
"""

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_IMAGE = PROJECT_ROOT / "img_conceitos" / "conceito_6b_papel_minimalista_vetor.jpg"
ASSETS_DIR = PROJECT_ROOT / "assets"
LOGO_OUTPUT = ASSETS_DIR / "logo.png"
ICO_OUTPUT = ASSETS_DIR / "app.ico"

ICO_SIZES = [
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]


def generate_assets(
    source_path: Path = SOURCE_IMAGE,
    assets_dir: Path = ASSETS_DIR,
) -> None:
    """Gera o logo em PNG e o ícone Windows (.ico) a partir da imagem de origem."""
    if not source_path.exists():
        raise FileNotFoundError(f"Imagem de origem não encontrada em: {source_path}")

    assets_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as img:
        rgba_img = img.convert("RGBA")

        # 1. Salvar logo PNG em alta resolução (1024x1024)
        logo_path = assets_dir / "logo.png"
        rgba_img.save(logo_path, format="PNG", optimize=True)
        print(f"[OK] Logo gerado: {logo_path} ({rgba_img.size[0]}x{rgba_img.size[1]})")

        # 2. Salvar app.ico multi-resolução para Windows
        ico_path = assets_dir / "app.ico"
        rgba_img.save(
            ico_path,
            format="ICO",
            sizes=ICO_SIZES,
        )
        print(f"[OK] Ícone multi-resolução gerado: {ico_path} com resoluções: {ICO_SIZES}")


if __name__ == "__main__":
    generate_assets()
