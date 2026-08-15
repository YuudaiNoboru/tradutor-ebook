from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Static

from tradutor.domain import make_cost_report
from tradutor.translate.pipeline import RunResult
from tradutor.tui.screens.estimate import fmt_usd
from tradutor.tui.widgets import VersionFooter

if TYPE_CHECKING:
    from tradutor.tui.app import TradutorApp

REPORT_CSS = """
ReportScreen {
    align: center top;
}
#report-view {
    width: 84;
    max-width: 95%;
    height: auto;
    margin-top: 1;
    margin-bottom: 1;
}
.report-row {
    height: 1;
    margin-bottom: 1;
}
#output-path {
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}
#cost-report {
    margin-top: 1;
}
"""


class ReportScreen(Screen[None]):
    """Relatorio final da traducao: real-vs-previsto e arquivo de saida."""

    CSS = REPORT_CSS
    BINDINGS = [
        Binding("escape", "back", "Voltar"),
    ]

    @property
    def tradutor_app(self) -> TradutorApp:
        return cast("TradutorApp", self.app)

    def action_back(self) -> None:
        self.tradutor_app.reset_session()
        self.app.switch_screen("book")

    def compose(self) -> ComposeResult:
        outcome = self.tradutor_app.session.outcome
        assert outcome is not None
        yield Header()
        with Vertical(id="report-view"):
            yield Static("Traducao concluida!", classes="screen-title")
            yield from self._rows(outcome)
            with Horizontal(classes="center-row"):
                yield Button("Traduzir outro livro", id="again", variant="primary")
                yield Button("Sair", id="quit")
        yield VersionFooter()

    def _rows(self, outcome: RunResult) -> list[Static]:
        plan = self.tradutor_app.session.plan
        prices = plan.prices if plan is not None else None
        rows = [Static(f"Arquivo gerado: {outcome.out_path}", id="output-path")]
        if outcome.usage.token_usage_reported:
            rows.append(
                Static(
                    f"Tokens usados: entrada {outcome.usage.prompt_tokens} | "
                    f"saida {outcome.usage.completion_tokens} | "
                    f"total {outcome.usage.total_tokens}"
                )
            )
        else:
            rows.append(
                Static(
                    f"Blocos processados: {outcome.usage.blocks} | "
                    f"Caracteres: {outcome.usage.characters} | "
                    "tokens e custo não reportados pelo endpoint"
                )
            )
        if plan is not None and plan.estimate is not None and plan.estimate.cost_usd is None:
            rows.append(
                Static(
                    "Custo/uso não mensurável pelo aplicativo; o serviço remoto "
                    "pode impor limites ou bloqueios.",
                    id="cost-report",
                )
            )
        elif plan is not None and plan.estimate is not None and prices is not None:
            report = make_cost_report(estimate=plan.estimate, usage=outcome.usage, prices=prices)
            rows.append(
                Static(
                    f"Previsto: {fmt_usd(report.estimated.cost_usd or 0.0)} | "
                    f"Real: {fmt_usd(report.actual_cost_usd or 0.0)} | "
                    f"Diferenca: {fmt_usd(report.difference_usd or 0.0)}",
                    id="cost-report",
                )
            )
        else:
            rows.append(
                Static(
                    "Custo real indisponivel: configure os precos em "
                    "[cost.prices.<provider>] no config.",
                    id="cost-report",
                )
            )
        return rows

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "again":
            self.tradutor_app.reset_session()
            self.app.switch_screen("book")
        elif event.button.id == "quit":
            self.app.exit()
