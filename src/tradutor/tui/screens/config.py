"""Tela de configuracao (tarefa 9.2).

Provider, chave sempre mascarada (com teste de conexao), idiomas,
politica de termos e paralelismo. Salvar persiste as configuracoes no
arquivo TOML e a chave no cofre do sistema.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static
from textual.worker import Worker, WorkerState

from tradutor.providers import ConnectionResult

POLICY_OPTIONS = [
    ("Traduzir termos", "traduzir"),
    ("Manter originais", "manter"),
    ("Hibrido (1a com original entre parenteses)", "hibrido"),
]

FORM_CSS = """
#config-form {
    width: 82;
    height: auto;
    max-height: 100%;
    overflow-y: auto;
}
#config-columns {
    height: auto;
}
.config-column {
    width: 38;
    margin: 0 1;
    height: auto;
}
Label { margin-top: 1; }
#test-result { margin-top: 1; }
"""


class ConfigScreen(Screen[None]):
    """Formulario de configuracao da traducao."""

    CSS = FORM_CSS
    BINDINGS = [
        Binding("c", "none", "", show=False),
        Binding("escape", "back", "Voltar"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_models: dict[str, str] = {}
        self._provider_models: dict[str, list[str]] = {}
        self._manual_input_active: dict[str, bool] = {}
        self._last_provider: str = ""

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        config = self.app.env.config
        provider_names = sorted(set(config.providers) | {"deepseek", "openrouter"})
        yield Header()
        with Vertical(id="config-form"):
            yield Static("Configuracao", classes="screen-title")
            with Horizontal(id="config-columns"):
                with Vertical(classes="config-column"):
                    yield Label("Provedor")
                    yield Select(
                        [(name, name) for name in provider_names],
                        prompt="Selecione o provedor",
                        value=config.provider if config.provider in provider_names else "deepseek",
                        id="provider",
                    )
                    yield Label("Modelo")
                    yield Select(
                        [],
                        prompt="Realize o teste de conexao para listar modelos...",
                        id="model-select",
                    )
                    yield Input(
                        placeholder="digite o nome do modelo (ex: deepseek-chat)",
                        id="model",
                    )
                    yield Label("Chave da API (mascarada)")
                    yield Input(
                        placeholder="digite a chave nova (vazia = manter a atual)",
                        password=True,
                        id="key",
                    )
                    yield Static(self._key_hint(), classes="form-hint", id="key-hint")
                with Vertical(classes="config-column"):
                    yield Label("Idioma de origem ('auto' detecta)")
                    yield Input(value=config.translation.source, id="source")
                    yield Label("Idioma de destino")
                    yield Select(
                        [
                            ("Português (pt-BR)", "pt-BR"),
                            ("Inglês (en-US)", "en-US"),
                            ("Espanhol (es-ES)", "es-ES"),
                            ("Francês (fr-FR)", "fr-FR"),
                            ("Italiano (it-IT)", "it-IT"),
                            ("Alemão (de-DE)", "de-DE"),
                            ("Outro (Digitar manual...)", "outro"),
                        ],
                        value=config.translation.target
                        if config.translation.target
                        in ["pt-BR", "en-US", "es-ES", "fr-FR", "it-IT", "de-DE"]
                        else "outro",
                        id="target-select",
                    )
                    yield Input(
                        value=config.translation.target,
                        placeholder="digite o código do idioma (ex: pt-BR)",
                        id="target",
                    )
                    yield Label("Politica de termos tecnicos")
                    yield Select(POLICY_OPTIONS, value=config.translation.policy, id="policy")
                    yield Label("Paralelismo (lotes em simultaneo)")
                    yield Input(
                        value=str(config.execution.parallelism),
                        type="integer",
                        id="parallelism",
                    )
            yield Static("", id="test-result")
            with Horizontal(classes="center-row"):
                yield Button("Testar conexao", id="test", variant="primary")
                yield Button("Salvar", id="save")
                yield Button("Voltar", id="back")
        yield Footer()

    def on_mount(self) -> None:
        config = self.app.env.config
        for name, p_config in config.providers.items():
            if p_config.model:
                self._selected_models[name] = p_config.model
                self._provider_models[name] = [p_config.model]

        target_select = self.query_one("#target-select", Select)
        self.query_one("#target", Input).display = target_select.value == "outro"

        provider_select = self.query_one("#provider", Select)
        if provider_select.value is not None:
            provider_name = str(provider_select.value)
            self._last_provider = provider_name
            self._update_model_widgets(provider_name)

    def _get_saved_model(self, provider_name: str) -> str | None:
        config = self.app.env.config
        provider_cfg = config.providers.get(provider_name)
        if provider_cfg and provider_cfg.model:
            return provider_cfg.model
        if provider_name == config.provider:
            from tradutor.tui.runner import model_for

            return model_for(config)
        return None

    def _save_current_provider_state(self, provider_name: str) -> None:
        if not provider_name:
            return
        try:
            model_select = self.query_one("#model-select", Select)
            model_input = self.query_one("#model", Input)
        except Exception:
            return

        manual_active = model_input.display
        self._manual_input_active[provider_name] = manual_active

        if manual_active:
            self._selected_models[provider_name] = model_input.value.strip()
        else:
            if model_select.value is not None and model_select.value != Select.NULL:
                self._selected_models[provider_name] = str(model_select.value)

    def _update_model_widgets(self, provider_name: str) -> None:
        model_select = self.query_one("#model-select", Select)
        model_input = self.query_one("#model", Input)

        is_manual = self._manual_input_active.get(provider_name, False)
        selected_model = self._selected_models.get(provider_name)
        available = self._provider_models.get(provider_name, [])

        if not selected_model:
            saved_model = self._get_saved_model(provider_name)
            if saved_model:
                selected_model = saved_model
                available = [saved_model]
                self._selected_models[provider_name] = selected_model
                self._provider_models[provider_name] = available

        if is_manual:
            model_select.display = False
            model_input.display = True
            model_input.value = selected_model or ""
        else:
            model_select.display = True
            model_input.display = False
            if selected_model and available:
                model_select.disabled = False
                model_select.prompt = "Selecione o modelo"
                model_select.set_options([(m, m) for m in available])
                model_select.value = selected_model
            else:
                model_select.disabled = True
                model_select.set_options([])
                model_select.clear()
                model_select.prompt = "Realize o teste de conexao para listar modelos..."

    @on(Select.Changed)
    def _on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "provider":
            if event.value is not None:
                new_provider = str(event.value)
                if self._last_provider and self._last_provider != new_provider:
                    self._save_current_provider_state(self._last_provider)
                self._last_provider = new_provider
                self._update_model_widgets(new_provider)
                self._update_key_hint(new_provider)
        elif event.select.id == "model-select":
            provider_name = str(self.query_one("#provider", Select).value)
            if event.value is not None and event.value != Select.NULL:
                self._selected_models[provider_name] = str(event.value)
        elif event.select.id == "target-select":
            inp = self.query_one("#target", Input)
            if event.value == "outro":
                inp.display = True
                inp.focus()
            else:
                inp.display = False
                if event.value is not None:
                    inp.value = str(event.value)

    @on(Input.Changed)
    def _on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "model":
            provider_name = str(self.query_one("#provider", Select).value)
            self._selected_models[provider_name] = event.value.strip()

    def _key_hint(self, provider_name: str | None = None) -> str:
        p = provider_name
        if p is None:
            try:
                p = str(self.query_one("#provider", Select).value)
            except Exception:
                p = self.app.env.config.provider
        has_key = bool(self.app.chain().get(self.app.key_name_for(p)))
        if has_key:
            return "Ja existe uma chave configurada (variavel de ambiente ou cofre)."
        return "Sem chave configurada. Obtenha uma no painel do provedor."

    def _update_key_hint(self, provider_name: str) -> None:
        try:
            hint = self.query_one("#key-hint", Static)
        except Exception:
            return
        hint.update(self._key_hint(provider_name))

    @work(thread=True, name="teste-conexao", exit_on_error=False)
    def _do_test(self, key: str | None, provider_name: str, model_name: str) -> ConnectionResult:
        return self.app.build_provider(
            key_override=key,
            provider_name=provider_name,
            model_name=model_name,
        ).test_connection()

    @on(Worker.StateChanged)
    def _on_test_done(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "teste-conexao":
            return
        label = self.query_one("#test-result", Static)
        if event.state is WorkerState.SUCCESS:
            result = event.worker.result
            message = result.message
            if result.models:
                message += f": {', '.join(result.models[:3])}"
            label.update(("OK " if result.ok else "FALHA ") + message)

            if result.ok:
                provider_name = str(self.query_one("#provider", Select).value)
                model_select = self.query_one("#model-select", Select)
                model_input = self.query_one("#model", Input)

                if result.models:
                    current_model = self._get_current_model_value()
                    model_select.display = True
                    model_input.display = False
                    model_select.disabled = False
                    model_select.prompt = "Selecione o modelo"

                    available = list(result.models)
                    self._provider_models[provider_name] = available
                    model_select.set_options([(m, m) for m in available])

                    if current_model in available:
                        model_select.value = current_model
                        self._selected_models[provider_name] = current_model
                    else:
                        model_select.value = available[0]
                        self._selected_models[provider_name] = available[0]
                    self._manual_input_active[provider_name] = False
                else:
                    model_select.display = False
                    model_input.display = True
                    self._manual_input_active[provider_name] = True
                    model_input.focus()
        elif event.state is WorkerState.ERROR:
            error = event.worker.error
            label.update(f"FALHA ao testar: {error}")

    def _get_current_model_value(self) -> str:
        model_select = self.query_one("#model-select", Select)
        model_input = self.query_one("#model", Input)
        if (
            model_select.display
            and model_select.value is not None
            and model_select.value != Select.NULL
        ):
            return str(model_select.value)
        return model_input.value.strip()

    def _typed_key(self) -> str | None:
        value = self.query_one("#key", Input).value.strip()
        return value or None

    def _parallelism(self) -> int | None:
        try:
            value = int(self.query_one("#parallelism", Input).value.strip())
        except ValueError:
            return None
        return value if value >= 1 else None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test":
            self._run_test()
        elif event.button.id == "save":
            self._save()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _run_test(self) -> None:
        label = self.query_one("#test-result", Static)
        label.update("testando conexao...")
        provider_name = str(self.query_one("#provider", Select).value)
        model_name = self._get_current_model_value()
        self._do_test(self._typed_key(), provider_name, model_name)

    def _save(self) -> None:
        parallelism = self._parallelism()
        if parallelism is None:
            self.notify("Paralelismo deve ser um numero inteiro >= 1", severity="error")
            return

        provider_select = self.query_one("#provider", Select)
        provider = provider_select.value
        if provider is None or provider == Select.BLANK:
            self.notify("O provedor é obrigatório", severity="error")
            return

        model = self._get_current_model_value()
        if not model:
            self.notify("O modelo é obrigatório", severity="error")
            return

        key = self._typed_key()
        if key:
            self.app.save_key(key)
        self.app.save_settings(
            provider=str(provider),
            model=model,
            source=self.query_one("#source", Input).value.strip() or "auto",
            target=self.query_one("#target", Input).value.strip() or "pt-BR",
            policy=str(self.query_one("#policy", Select).value),
            parallelism=parallelism,
        )
        self.notify("Configuracao salva")
        self.app.pop_screen()
