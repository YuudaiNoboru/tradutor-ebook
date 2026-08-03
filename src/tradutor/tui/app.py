"""Aplicativo Textual (decisao D10): telas e estado da sessao.

``TradutorApp`` recebe um ``AppEnv`` injetavel (config, cadeia de
segredos, fabrica de provider e contador de tokens) — nos testes, o
ambiente e montado com fakes; em producao, defaults reais.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from tradutor.domain import Translator
from tradutor.domain.secrets import SecretStore
from tradutor.epub.container import Ebook
from tradutor.infra.config import AppConfig, write_config
from tradutor.infra.secrets import (
    ChainedSecretStore,
    KeyringSecretStore,
    PromptSecretStore,
    build_secret_chain,
)
from tradutor.providers import (
    DEFAULT_BASE_URL,
    DEFAULT_KEY_NAME,
    DEFAULT_MODEL,
    OpenAICompatProvider,
)
from tradutor.tui.runner import BookPlan, CacheStatus, RunResult, default_work_dir_for
from tradutor.tui.screens.book import BookScreen
from tradutor.tui.screens.config import ConfigScreen
from tradutor.tui.screens.error import ErrorScreen
from tradutor.tui.screens.estimate import EstimateScreen
from tradutor.tui.screens.progress import ProgressScreen
from tradutor.tui.screens.report import ReportScreen
from tradutor.tui.screens.welcome import WelcomeScreen

APP_CSS = """
Screen { align: center middle; }
.screen-title { text-style: bold; text-align: center; margin-bottom: 1; }
.center-row { align: center middle; margin-top: 1; }
.center-row Button { margin: 0 1; }
.app-title { text-style: bold; text-align: center; color: $accent; }
.welcome-text { text-align: center; margin-top: 1; }
.welcome-hint { text-align: center; margin-top: 1; color: $warning; }
.form-hint { color: $text-muted; }
.error-title { text-style: bold; color: $error; }
#error-dialog { width: 72; border: round $error; padding: 1 2; }
"""


@dataclass
class AppEnv:
    """Dependencias injetaveis da TUI (producao ou testes)."""

    config: AppConfig = field(default_factory=AppConfig)
    config_path: Path | None = None
    chain: SecretStore | None = None
    key_backend: SecretStore | None = None
    provider_factory: Callable[[], Translator] | None = None
    token_counter: Callable[[str], int] | None = None
    latency_seconds: float = 20.0
    max_tokens: int = 4000
    work_dir_for: Callable[[Path], Path] = default_work_dir_for


@dataclass
class Session:
    """Estado transitorio da sessao: livro, plano, cache e resultado."""

    ebook: Ebook | None = None
    book_hash: str = ""
    work_dir: Path | None = None
    plan: BookPlan | None = None
    cache: CacheStatus | None = None
    reset: bool = False
    outcome: RunResult | None = None
    notice: str = ""


class TradutorApp(App[None]):
    """TUI do tradutor: boas-vindas -> config -> livro -> estimativa -> progresso -> relatorio."""

    TITLE = "tradutor-ebook"
    SUB_TITLE = "Tradutor de EPUBs (BYOK)"
    CSS = APP_CSS
    BINDINGS = [("q", "quit", "Sair")]
    SCREENS = {
        "welcome": WelcomeScreen,
        "config": ConfigScreen,
        "book": BookScreen,
        "estimate": EstimateScreen,
        "progress": ProgressScreen,
        "report": ReportScreen,
        "error": ErrorScreen,
    }

    def __init__(self, env: AppEnv | None = None) -> None:
        super().__init__()
        self.env = env if env is not None else AppEnv()
        self.session = Session()
        self._chain: SecretStore | None = None
        self._token_counter: Callable[[str], int] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen("welcome" if not self.has_key() else "book")

    def reset_session(self) -> None:
        self.session = Session()

    def chain(self) -> SecretStore:
        if self._chain is None:
            self._chain = (
                self.env.chain
                if self.env.chain is not None
                else build_secret_chain(env=os.environ, keyring_store=KeyringSecretStore())
            )
        return self._chain

    def has_key(self) -> bool:
        return bool(self.chain().get(DEFAULT_KEY_NAME))

    def save_key(self, key: str) -> None:
        backend = self.env.key_backend if self.env.key_backend is not None else KeyringSecretStore()
        backend.set(DEFAULT_KEY_NAME, key)

    def token_counter(self) -> Callable[[str], int]:
        if self._token_counter is None:
            from tradutor.translate.batching import tiktoken_counter

            self._token_counter = (
                self.env.token_counter if self.env.token_counter is not None else tiktoken_counter()
            )
        return self._token_counter

    def build_provider(self, key_override: str | None = None) -> Translator:
        if self.env.provider_factory is not None:
            return self.env.provider_factory()
        chain = self.chain()
        if key_override:
            chain = ChainedSecretStore([PromptSecretStore(lambda: key_override), chain])
        provider_config = self.env.config.providers.get(self.env.config.provider)
        return OpenAICompatProvider(
            chain,
            base_url=provider_config.base_url if provider_config else DEFAULT_BASE_URL,
            model=provider_config.model if provider_config else DEFAULT_MODEL,
        )

    def save_settings(
        self,
        *,
        provider: str,
        source: str,
        target: str,
        policy: str,
        parallelism: int,
    ) -> None:
        config = self.env.config
        config.provider = provider
        config.translation.source = source
        config.translation.target = target
        config.translation.policy = policy
        config.execution.parallelism = parallelism
        write_config(config, self.env.config_path)
