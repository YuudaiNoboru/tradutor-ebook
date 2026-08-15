"""Tela de estimativa com confirmacao (tarefa 9.3) e retomada (9.5).

Mostra o resumo do livro, a estimativa de tokens/custo/tempo, o aviso de
que a estimativa e aproximada e a recomendacao de limite de gasto.
Quando existe cache compativel, informa o progresso armazenado e oferece
continuar ou recomecar. A tela e reutilizada (``switch_screen`` mantem a
instancia): ``refresh`` reavalia o cache apos cancelamento/erro e
``set_notice`` mostra o aviso de retomada.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Header, Input, Label, Static

from tradutor.infra.config import AppConfig
from tradutor.providers import DEFAULT_MODEL, ProviderDiscoveryError, get_provider_description
from tradutor.translate.glossary_store import load_glossary
from tradutor.translate.planner import BookPlan, CacheStatus, cache_status, plan_book
from tradutor.tui.widgets import VersionFooter

if TYPE_CHECKING:
    from tradutor.tui.app import TradutorApp
    from tradutor.tui.screens.progress import ProgressScreen

SUMMARY_CSS = """
EstimateScreen {
    align: center top;
}
#estimate-view {
    width: 84;
    max-width: 95%;
    height: auto;
    margin-top: 1;
    margin-bottom: 1;
}
.estimate-row {
    height: 1;
}
#estimate-warning {
    color: $warning;
    margin-top: 1;
}
#cache-info {
    color: $accent;
    margin-top: 1;
}
#notice {
    color: $warning;
    margin-top: 1;
}
"""


def fmt_usd(value: float) -> str:
    return f"US$ {value:.2f}"


def fmt_seconds(value: float) -> str:
    if value < 60:
        return f"{value:.0f} s"
    return f"{value / 60:.1f} min"


class EstimateScreen(Screen[None]):
    """Resumo do livro, estimativa de custo e confirmacao."""

    CSS = SUMMARY_CSS
    BINDINGS = [
        Binding("escape", "back", "Voltar"),
    ]

    @property
    def tradutor_app(self) -> TradutorApp:
        return cast("TradutorApp", self.app)

    def action_back(self) -> None:
        self.tradutor_app.session.ebook = None
        self.app.switch_screen("book")

    def compose(self) -> ComposeResult:
        session = self.tradutor_app.session
        assert session.ebook is not None
        assert session.work_dir is not None
        config = self.tradutor_app.env.config
        assert config is not None
        plan = plan_book(
            session.ebook,
            config=config,
            token_counter=self.tradutor_app.token_counter(),
        )
        cache = self._cache_status()
        self._apply_plan(plan, cache)
        yield Header()
        with Vertical(id="estimate-view"):
            yield Static("Estimativa", classes="screen-title")
            yield Static(plan.title, id="book-title")
            yield Static(self._provider_line(), id="provider-info")
            yield Static(self._book_info(plan), id="book-info")
            yield Static(self._blocks_line(plan), id="book-blocks")
            yield Static(self._estimate_line(plan), id="estimate-values")
            yield Static(self._warning_text(config), id="estimate-warning")
            yield Static(self._cache_line(cache), id="cache-info")
            yield Static("", id="notice")
            yield Checkbox(
                "Gerar Glossário e Guia de Estilo",
                value=session.enable_quality_passes,
                id="enable-quality-passes",
            )
            yield Label("Paralelismo (ajuste e confirme abaixo)")
            yield Input(
                value=str(config.execution.parallelism),
                type="integer",
                id="parallelism",
            )
            with Horizontal(classes="center-row"):
                yield Button("Traduzir agora", id="go", variant="primary")
                yield Button("Recomecar do zero", id="restart")
                yield Button("Configuracao", id="config")
                yield Button("Trocar de livro", id="back")
        yield VersionFooter()

    def on_mount(self) -> None:
        self._refresh_buttons()
        limit = self._max_parallelism()
        config = self.tradutor_app.env.config
        assert config is not None
        eff_par = min(config.execution.parallelism, limit)
        self.query_one("#parallelism", Input).value = str(eff_par)
        self.query_one("#enable-quality-passes", Checkbox).display = config.family == "llm"
        if self.tradutor_app.session.notice:
            self.query_one("#notice", Static).update(self.tradutor_app.session.notice)

    def on_screen_resume(self, event: ScreenResume) -> None:
        self.recompute()

    @on(Input.Changed)
    def _on_parallelism_changed(self, event: Input.Changed) -> None:
        if event.input.id != "parallelism" or not self.is_mounted:
            return
        try:
            value = int(event.input.value)
        except ValueError:
            return
        if value < 1:
            return
        session = self.tradutor_app.session
        assert session.ebook is not None
        config = self.tradutor_app.env.config
        assert config is not None
        plan = plan_book(
            session.ebook,
            config=config,
            token_counter=self.tradutor_app.token_counter(),
            parallelism=value,
        )
        self._apply_plan(plan, self._cache_status())
        self.query_one("#estimate-values", Static).update(self._estimate_line(plan))

    def set_notice(self, text: str) -> None:
        """Mostra um aviso e reavalia o cache (retomada apos cancelamento)."""
        self.tradutor_app.session.notice = text
        self.query_one("#notice", Static).update(text)
        self.recompute()

    def recompute(self) -> None:
        """Recalcula plano e cache (o estado pode ter mudado) e re-renderiza."""
        session = self.tradutor_app.session
        assert session.ebook is not None
        config = self.tradutor_app.env.config
        assert config is not None
        plan = plan_book(
            session.ebook,
            config=config,
            token_counter=self.tradutor_app.token_counter(),
        )
        cache = self._cache_status()
        self._apply_plan(plan, cache)
        self.query_one("#book-title", Static).update(plan.title)
        self.query_one("#book-info", Static).update(self._book_info(plan))
        self.query_one("#provider-info", Static).update(self._provider_line())
        self.query_one("#book-blocks", Static).update(self._blocks_line(plan))
        self.query_one("#estimate-values", Static).update(self._estimate_line(plan))
        self.query_one("#estimate-warning", Static).update(self._warning_text(config))
        self.query_one("#cache-info", Static).update(self._cache_line(cache))
        limit = self._max_parallelism()
        eff_par = min(config.execution.parallelism, limit)
        self.query_one("#parallelism", Input).value = str(eff_par)
        self.query_one("#enable-quality-passes", Checkbox).display = config.family == "llm"
        self._refresh_buttons()

    def _apply_plan(self, plan: BookPlan, cache: CacheStatus) -> None:
        self._plan = plan
        self._cache = cache
        self.tradutor_app.session.plan = plan
        self.tradutor_app.session.cache = cache

    def _cache_status(self) -> CacheStatus:
        session = self.tradutor_app.session
        assert session.work_dir is not None
        config = self.tradutor_app.env.config
        assert config is not None
        glossary = load_glossary(session.work_dir / "glossario.json")
        return cache_status(
            session.work_dir,
            book_hash=session.book_hash,
            config=config,
            glossary=glossary,
        )

    def _refresh_buttons(self) -> None:
        resume = self._cache.compatible and self._cache.saved_blocks > 0
        go = self.query_one("#go", Button)
        restart = self.query_one("#restart", Button)
        go.label = "Continuar traducao" if resume else "Traduzir agora"
        restart.display = resume

    def _provider_line(self) -> str:
        config = self.tradutor_app.env.config
        assert config is not None
        try:
            name = get_provider_description(config.provider, family=config.family).display_name
        except ProviderDiscoveryError:
            name = config.provider
        if config.family == "machine_translation":
            return f"Tradução: {name} | família: tradução automática"
        configured = config.providers.get(config.provider)
        model = configured.model if configured and configured.model else DEFAULT_MODEL
        return f"Tradução: {name} | família: LLM | modelo: {model}"

    @staticmethod
    def _warning_text(config: AppConfig) -> str:
        return (
            "AVISO: Google Web é um serviço experimental que usa endpoint não oficial, "
            "sem chave do usuário; há limites, bloqueios e instabilidade remotos e a "
            "gratuidade não é garantida. O serviço não reporta tokens/custo (medição por "
            "caracteres/blocos) e a estrutura XHTML será validada antes de gravar."
            if config.family == "machine_translation"
            else "AVISO: a estimativa usa precos e fator de expansao aproximados; "
            "o relatorio final compara previsto x real. Recomendamos definir "
            "um teto de gasto na conta do provedor antes de traduzir livros longos."
        )

    @staticmethod
    def _book_info(plan: BookPlan) -> str:
        return f"Idioma: {plan.language or 'desconhecido'} | Capitulos: {plan.chapter_count}"

    @staticmethod
    def _blocks_line(plan: BookPlan) -> str:
        if plan.estimate is not None and plan.estimate.cost_usd is None:
            return (
                f"Blocos traduziveis: {plan.translatable_blocks} | "
                f"Caracteres: {plan.estimate.characters} | Lotes: {plan.batch_count}"
            )
        return (
            f"Blocos traduziveis: {plan.translatable_blocks} | "
            f"Tokens de entrada: {plan.input_tokens} | Lotes: {plan.batch_count}"
        )

    @staticmethod
    def _estimate_line(plan: BookPlan) -> str:
        if plan.estimate is None:
            return (
                "Precos nao configurados: defina [cost.prices.<provedor>] no "
                "arquivo de configuracao para estimar o custo."
            )
        estimate = plan.estimate
        if estimate.cost_usd is None:
            return (
                f"Uso de tokens/custo: não reportado | Caracteres: {estimate.characters} | "
                f"Tempo estimado: {fmt_seconds(estimate.estimated_seconds)}"
            )
        return (
            f"Custo estimado: {fmt_usd(estimate.cost_usd)} | "
            f"Saida prevista: {estimate.output_tokens} tokens | "
            f"Tempo estimado: {fmt_seconds(estimate.estimated_seconds)}"
        )

    @staticmethod
    def _cache_line(cache: CacheStatus) -> str:
        if cache.compatible and cache.saved_blocks > 0:
            return (
                f"Cache: {cache.saved_blocks} blocos ja traduzidos nesta "
                "configuracao. Continuar aproveita esse progresso."
            )
        return ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "go":
            self._start(restart=False)
        elif event.button.id == "restart":
            self._start(restart=True)
        elif event.button.id == "config":
            self.app.push_screen("config", callback=lambda _: self.recompute())
        elif event.button.id == "back":
            self.tradutor_app.session.ebook = None
            self.app.switch_screen("book")

    def _max_parallelism(self) -> int:
        config = self.tradutor_app.env.config
        if not config:
            return 20
        try:
            desc = get_provider_description(config.provider, config.family)
            return min(20, desc.capabilities.max_concurrency)
        except Exception:
            return 20

    def _start(self, *, restart: bool) -> None:
        raw = self.query_one("#parallelism", Input).value.strip()
        try:
            value = int(raw)
        except ValueError:
            self.notify("Paralelismo deve ser um numero inteiro >= 1", severity="error")
            return
        limit = self._max_parallelism()
        if value < 1 or value > limit:
            self.notify(
                f"Paralelismo deve ser um numero inteiro entre 1 e {limit}",
                severity="error",
            )
            return
        config = self.tradutor_app.env.config
        assert config is not None
        config.execution.parallelism = value
        self.tradutor_app.session.reset = restart
        if config.family == "llm":
            self.tradutor_app.session.enable_quality_passes = self.query_one(
                "#enable-quality-passes", Checkbox
            ).value
        else:
            self.tradutor_app.session.enable_quality_passes = False
        progress = cast("ProgressScreen", self.app.get_screen("progress"))
        already_mounted = getattr(progress, "is_running", False)
        self.app.push_screen("progress")
        if already_mounted:
            progress.start_run()
