"""Testes de integração da TUI com o updater."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.widgets import Checkbox

from tests.tui.helpers import DictSecretStore
from tradutor.infra.config import AppConfig
from tradutor.tui.app import AppEnv, TradutorApp
from tradutor.tui.screens.config import ConfigScreen
from tradutor.tui.screens.update import UpdateModal


def make_env(tmp_path: Path, *, key: str | None = None, **overrides) -> AppEnv:
    chain = DictSecretStore()
    if key:
        chain.set("DEEPSEEK_API_KEY", key)
    env = AppEnv(
        config=AppConfig(),
        config_path=tmp_path / "config.toml",
        chain=chain,
        key_backend=chain,
        token_counter=len,
        latency_seconds=1.0,
        work_dir_for=lambda _path: tmp_path / "trabalho",
    )
    for name, value in overrides.items():
        setattr(env, name, value)
    return env


def test_delayed_update_applies_on_mount(tmp_path, monkeypatch):
    """Verifica se uma atualização pendente local é disparada ao iniciar o app."""
    # Mock updater behaviors
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    monkeypatch.setattr(
        "tradutor.infra.updater.check_delayed_update",
        lambda _v: {
            "version": "v9.9.9",
            "filename": "tradutor.exe",
            "exe_path": str(tmp_path / "exe"),
            "json_path": str(tmp_path / "json"),
        },
    )

    helper_called = []

    def mock_run_helper(exe_path, json_path, current_exe=None):
        helper_called.append((exe_path, json_path))

    monkeypatch.setattr("tradutor.infra.updater.run_helper_and_exit", mock_run_helper)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            # Wait for the timer to fire (we set it for 2.0s, so we wait slightly longer)
            await pilot.pause(2.5)
            assert len(helper_called) == 1
            assert helper_called[0][0] == Path(tmp_path / "exe")

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_config_screen_update_options_and_saving(tmp_path):
    """Testa a renderização e o salvamento das opções do updater na tela de configurações."""
    env = make_env(tmp_path, key="sk-123")

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            assert isinstance(app.screen, ConfigScreen)

            # Verifica se o Checkbox existe e está ativado (default)
            checkbox = app.screen.query_one("#auto-check", Checkbox)
            assert checkbox.value is True

            # Desmarca a opção e clica em Salvar
            checkbox.value = False
            await pilot.click("#save")
            await pilot.pause()

            # Recarrega a configuração para verificar se persistiu
            from tradutor.infra.config import load_config

            reloaded = load_config(env.config_path)
            assert reloaded.update.auto_check is False

    asyncio.run(run(TradutorApp(env=env)))


def test_manual_check_opens_modal_and_downloads(tmp_path, monkeypatch):
    """Testa a checagem manual por atualizações, abertura do modal e fluxo de download/reinício."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    env = make_env(tmp_path, key="sk-123")

    # Mocks do updater
    monkeypatch.setattr(
        "tradutor.infra.updater.check_for_update",
        lambda _v, *args, **kwargs: {
            "version": "v1.2.3",
            "download_url": "https://github.com/fake/tradutor.exe",
            "filename": "tradutor.exe",
        },
    )

    download_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.download_update",
        lambda url, ver, filename: download_called.append((url, ver, filename)) or True,
    )

    helper_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.run_helper_and_exit",
        lambda exe, js, curr=None: helper_called.append((exe, js)),
    )

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            # Clica no botão "Verificar atualizações"
            await pilot.click("#check-now")
            await pilot.pause(0.5)

            # O modal de atualização deve estar ativo
            assert isinstance(app.screen, UpdateModal)
            assert app.screen.state == "prompt"

            # Clica em Baixar no modal
            await pilot.click("#download-btn")
            # Espera o download (em worker thread) concluir
            await pilot.pause(1.0)

            # Estado deve ser downloaded
            assert app.screen.state == "downloaded"
            assert len(download_called) == 1
            assert download_called[0][1] == "v1.2.3"

            # Clica em Reiniciar
            await pilot.click("#restart-btn")
            await pilot.pause(0.5)

            # Verifica se o helper de reinício foi chamado
            assert len(helper_called) == 1

    asyncio.run(run(TradutorApp(env=env)))


def test_updater_prevented_when_not_frozen(tmp_path, monkeypatch):
    """Testa que ações do updater são bloqueadas e notificadas se não for executável compilado Windows."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: False)
    env = make_env(tmp_path, key="sk-123")

    helper_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.run_helper_and_exit",
        lambda exe, js, curr=None: helper_called.append((exe, js)),
    )

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            # Clica no botão "Verificar atualizações"
            await pilot.click("#check-now")
            await pilot.pause(0.5)

            # Não deve abrir o modal de atualização
            assert not isinstance(app.screen, UpdateModal)

            # Agora vamos testar o botão no modal de atualização caso ele fosse aberto
            modal = UpdateModal(
                {
                    "version": "v1.2.3",
                    "download_url": "https://github.com/fake/tradutor.exe",
                    "filename": "tradutor.exe",
                }
            )
            app.push_screen(modal)
            await pilot.pause()

            # Força o estado downloaded para exibir o botão de reiniciar
            modal.state = "downloaded"
            await pilot.pause()

            # Clica em Reiniciar
            await pilot.click("#restart-btn")
            await pilot.pause(0.5)

            # Verifica que o helper não foi chamado e o modal foi fechado
            assert len(helper_called) == 0
            assert app.screen != modal

    asyncio.run(run(TradutorApp(env=env)))
