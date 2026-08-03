"""Tela de relatorio final (tarefa 9.5).

Mostra o real-vs-previsto (custo US$, tokens) com o usage exato da API e
o caminho do EPUB gerado. A oferta de retomada quando existe cache
compativel acontece na tela de estimativa (mesma tarefa).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from tradutor.domain import make_cost_report
from tradutor.tui.runner import RunResult
from tradutor.tui.screens.estimate import fmt_usd

REPORT_CSS = """
#report-view { width: 84; }
.report-row { height: 1; }
"""


class ReportScreen(Screen[None]):
    """Relatorio final da traducao: real-vs-previsto e arquivo de saida."""

    CSS = REPORT_CSS

    def compose(self) -> ComposeResult:
        outcome = self.app.session.outcome
        assert outcome is not None
        with Vertical(id="report-view"):
            yield Static("Traducao concluida!", classes="screen-title")
            yield from self._rows(outcome)
            with Horizontal(classes="center-row"):
                yield Button("Traduzir outro livro", id="again", variant="primary")
                yield Button("Sair", id="quit")

    def _rows(self, outcome: RunResult) -> list[Static]:
        plan = self.app.session.plan
        prices = plan.prices if plan is not None else None
        rows = [
            Static(f"Arquivo gerado: {outcome.out_path}", id="output-path"),
            Static(
                f"Tokens usados: entrada {outcome.usage.prompt_tokens} | "
                f"saida {outcome.usage.completion_tokens} | "
                f"total {outcome.usage.total_tokens}"
            ),
        ]
        if plan is not None and plan.estimate is not None and prices is not None:
            report = make_cost_report(
                estimate=plan.estimate,
                usage=outcome.usage,
                prices=prices,
            )
            rows.append(
                Static(
                    f"Previsto: {fmt_usd(report.estimated.cost_usd)} | "
                    f"Real: {fmt_usd(report.actual_cost_usd)} | "
                    f"Diferenca: {fmt_usd(report.difference_usd)}",
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
            self.app.reset_session()
            self.app.switch_screen("book")
        elif event.button.id == "quit":
            self.app.exit()
