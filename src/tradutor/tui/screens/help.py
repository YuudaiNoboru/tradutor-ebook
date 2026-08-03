"""Tela modal explicativa de ajuda (tarefa 9.12)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

HELP_CSS = """
#help-dialog {
    width: 76;
    height: auto;
    border: round $primary;
    background: $panel;
    padding: 1 2;
}
.help-title {
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}
.help-text {
    margin-bottom: 1;
}
"""


class HelpScreen(ModalScreen[None]):
    """Tela modal explicativa de ajuda."""

    CSS = HELP_CSS

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("Ajuda - LiberLingua", classes="help-title")

            help_content = (
                "[b]BYOK (Chaves de API)[/b]\n"
                "Este aplicativo utiliza o modelo 'Bring Your Own Key'. Você deve configurar "
                "sua própria chave de API (como DeepSeek ou outro provider OpenAI-compatível) "
                "nas configurações. A chave é salva de forma segura no cofre de senhas do seu "
                "sistema operacional (keyring), ou em um arquivo local cifrado como fallback.\n\n"
                "[b]Fluxo de Tradução[/b]\n"
                "1. Selecione um arquivo EPUB na tela inicial.\n"
                "2. Revise a estimativa de custos e o tempo previsto.\n"
                "3. Confirme para iniciar. O app lê os capítulos de forma cirúrgica, extrai "
                "o texto e envia lotes de blocos para a API de LLM, mantendo toda a formatação original.\n"
                "4. Ao final, um novo arquivo '<nome>-<idioma>.epub' é gerado.\n\n"
                "[b]Cache e Retomada[/b]\n"
                "Se a tradução for interrompida ou cancelada, o progresso de cada bloco traduzido "
                "é salvo automaticamente em um arquivo de estado. Ao selecionar o mesmo livro com as "
                "mesmas configurações, o app detecta o progresso anterior e oferece a opção de retomar "
                "de onde parou, evitando retraduzir blocos e economizando tokens.\n\n"
                "[b]Glossário de Termos[/b]\n"
                "Antes de iniciar a tradução principal, o sistema analisa uma amostra do livro e extrai "
                "termos importantes ou nomes próprios, salvando-os em 'glossario.json' na pasta de trabalho. "
                "Você pode editar esse arquivo manualmente para ajustar traduções específicas de nomes/termos "
                "antes de iniciar a tradução."
            )
            yield Static(help_content, classes="help-text")

            with Horizontal(classes="center-row"):
                yield Button("Fechar", id="close-help", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-help":
            self.dismiss()
