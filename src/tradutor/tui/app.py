"""Aplicativo Textual (decisao D10): telas e estado da sessao.

``TradutorApp`` recebe um ``AppEnv`` injetavel (config, cadeia de
segredos, fabrica de provider e contador de tokens) — nos testes, o
ambiente e montado com fakes; em producao, defaults reais.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
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
    DEFAULT_MODEL,
    OpenAICompatProvider,
    ProviderDiscoveryError,
    create_discovered_provider,
)
from tradutor.translate.pipeline import RunResult
from tradutor.translate.planner import (
    BookPlan,
    CacheStatus,
    default_work_dir_for,
)
from tradutor.tui.screens.book import BookScreen
from tradutor.tui.screens.config import ConfigScreen
from tradutor.tui.screens.error import ErrorScreen
from tradutor.tui.screens.estimate import EstimateScreen
from tradutor.tui.screens.help import HelpScreen
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

    config: AppConfig | None = None
    config_path: Path | None = None
    chain: SecretStore | None = None
    key_backend: SecretStore | None = None
    provider_factory: Callable[[], Translator] | None = None
    token_counter: Callable[[str], int] | None = None
    latency_seconds: float = 20.0
    max_tokens: int = 4000
    work_dir_for: Callable[[Path], Path] = default_work_dir_for

    def __post_init__(self) -> None:
        if self.config_path is None:
            from tradutor.infra.config import default_config_path

            self.config_path = default_config_path()
        if self.config is None:
            from tradutor.infra.config import load_config

            self.config = load_config(self.config_path)


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

    TITLE = "LiberLingua"
    SUB_TITLE = "Tradutor de EPUBs"
    CSS = APP_CSS
    BINDINGS = [
        ("q", "quit", "Sair"),
        ("c", "config", "Configuração"),
        ("h", "help", "Ajuda"),
    ]
    SCREENS = {
        "welcome": WelcomeScreen,
        "config": ConfigScreen,
        "book": BookScreen,
        "estimate": EstimateScreen,
        "progress": ProgressScreen,
        "report": ReportScreen,
        "error": ErrorScreen,
        "help": HelpScreen,
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

    def action_config(self) -> None:
        self.push_screen("config")

    def action_help(self) -> None:
        self.push_screen("help")

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

    def key_name_for(self, provider: str) -> str:
        return f"{provider.upper()}_API_KEY"

    def has_key(self) -> bool:
        if self.env.config.family == "machine_translation":
            return True
        provider = self.env.config.provider
        return bool(self.chain().get(self.key_name_for(provider)))

    def save_key(self, key: str, provider: str | None = None) -> None:
        p = provider or self.env.config.provider
        backend = self.env.key_backend if self.env.key_backend is not None else KeyringSecretStore()
        backend.set(self.key_name_for(p), key)

    def token_counter(self) -> Callable[[str], int]:
        if self._token_counter is None:
            from tradutor.translate.batching import tiktoken_counter

            self._token_counter = (
                self.env.token_counter if self.env.token_counter is not None else tiktoken_counter()
            )
        return self._token_counter

    def build_provider(
        self,
        key_override: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        family: str | None = None,
    ) -> Translator:
        if self.env.provider_factory is not None:
            return self.env.provider_factory()
        config = self.env.config
        provider_to_use = provider_name or config.provider
        family_to_use = family or config.family
        if family_to_use == "machine_translation":
            limits = config.machine_translation
            return create_discovered_provider(
                provider_to_use,
                family="machine_translation",
                delay_seconds=limits.delay_seconds,
                timeout=limits.timeout_seconds,
                max_retries=3,
            )

        chain = self.chain()
        key_name = self.key_name_for(provider_to_use)
        if key_override:
            chain = ChainedSecretStore([PromptSecretStore(lambda _name: key_override), chain])
        provider_config = config.providers.get(provider_to_use)
        if provider_config:
            base_url = provider_config.base_url
            model = model_name or provider_config.model
        else:
            base_url = (
                "https://api.deepseek.com"
                if provider_to_use == "deepseek"
                else "https://openrouter.ai/api/v1"
                if provider_to_use == "openrouter"
                else DEFAULT_BASE_URL
            )
            model = model_name or DEFAULT_MODEL
        try:
            return create_discovered_provider(
                provider_to_use,
                family="llm",
                secret_store=chain,
                base_url=base_url,
                model=model,
                key_name=key_name,
            )
        except ProviderDiscoveryError:
            return OpenAICompatProvider(chain, base_url=base_url, model=model, key_name=key_name)

    def save_settings(
        self,
        *,
        provider: str,
        model: str,
        source: str,
        target: str,
        policy: str,
        parallelism: int,
        family: str | None = None,
    ) -> None:
        config = self.env.config
        if family is not None:
            config.family = family
        config.provider = provider

        if config.family != "machine_translation":
            if provider not in config.providers:
                if provider == "deepseek":
                    base_url = "https://api.deepseek.com"
                elif provider == "openrouter":
                    base_url = "https://openrouter.ai/api/v1"
                else:
                    base_url = DEFAULT_BASE_URL
                from tradutor.infra.config import ProviderConfig

                config.providers[provider] = ProviderConfig(base_url=base_url, model=model)
            else:
                config.providers[provider].model = model

        config.translation.source = source
        config.translation.target = target
        config.translation.policy = policy
        config.execution.parallelism = parallelism
        write_config(config, self.env.config_path)
