"""Testes de integração da TUI com o updater."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.widgets import Checkbox

from tests.tui.helpers import DictSecretStore
from tests.tui.test_app_flows import wait_for
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


def test_auto_check_on_mount_opens_modal(tmp_path, monkeypatch):
    """Verifica se a checagem automática ao iniciar abre o modal de atualização."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    monkeypatch.setattr(
        "tradutor.infra.updater.check_for_update",
        lambda _v, *args, **kwargs: {
            "version": "v1.2.3",
            "is_installed": True,
            "download_url": "https://github.com/fake/tradutor-ebook-setup.exe",
            "filename": "tradutor-ebook-setup.exe",
        },
    )

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await wait_for(pilot, lambda: isinstance(app.screen, UpdateModal))
            assert isinstance(app.screen, UpdateModal)
            assert app.screen.state == "prompt"
            assert app.screen.query_one("#download-btn").display is True
            assert app.screen.query_one("#browser-btn").display is False

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_installed_mode_modal_download_and_launch(tmp_path, monkeypatch):
    """Testa fluxo de download e disparo do instalador no Modo Instalado."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    env = make_env(tmp_path, key="sk-123")

    download_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.download_update",
        lambda url, ver, filename: download_called.append((url, ver, filename)) or True,
    )

    launch_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.launch_installer_and_exit",
        lambda path=None: launch_called.append(path),
    )

    update_info = {
        "version": "v1.2.3",
        "is_installed": True,
        "download_url": "https://github.com/fake/tradutor-ebook-setup.exe",
        "filename": "tradutor-ebook-setup.exe",
    }

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            modal = UpdateModal(update_info)
            app.push_screen(modal)
            await pilot.pause()

            assert isinstance(app.screen, UpdateModal)
            assert app.screen.query_one("#download-btn").display is True
            assert app.screen.query_one("#browser-btn").display is False
            assert app.screen.query_one("#cancel-btn").display is True

            # Clica em Baixar e Atualizar
            await pilot.click("#download-btn")
            await wait_for(pilot, lambda: len(launch_called) > 0)

            assert len(download_called) == 1
            assert download_called[0][1] == "v1.2.3"
            assert len(launch_called) == 1

    asyncio.run(run(TradutorApp(env=env)))


def test_portable_mode_modal_opens_browser(tmp_path, monkeypatch):
    """Testa fluxo de redirecionamento para o navegador no Modo Portátil."""
    env = make_env(tmp_path, key="sk-123")

    browser_opened = []
    monkeypatch.setattr(
        "tradutor.infra.updater.open_release_url",
        lambda url: browser_opened.append(url) or True,
    )

    update_info = {
        "version": "v1.2.3",
        "is_installed": False,
        "release_url": "https://github.com/YuudaiNoboru/tradutor-ebook/releases/tag/v1.2.3",
    }

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            modal = UpdateModal(update_info)
            app.push_screen(modal)
            await pilot.pause()

            assert isinstance(app.screen, UpdateModal)
            assert app.screen.query_one("#download-btn").display is False
            assert app.screen.query_one("#browser-btn").display is True
            assert app.screen.query_one("#close-btn").display is True

            # Clica em Abrir no Navegador
            await pilot.click("#browser-btn")
            await pilot.pause(0.5)

            assert len(browser_opened) == 1
            assert (
                browser_opened[0]
                == "https://github.com/YuudaiNoboru/tradutor-ebook/releases/tag/v1.2.3"
            )
            assert not isinstance(app.screen, UpdateModal)

    asyncio.run(run(TradutorApp(env=env)))


def test_config_screen_update_options_and_saving(tmp_path, monkeypatch):
    """Testa a renderização e o salvamento das opções do updater na tela de configurações."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
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
    """Testa a checagem manual por atualizações, abertura do modal e download."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    env = make_env(tmp_path, key="sk-123")

    monkeypatch.setattr(
        "tradutor.infra.updater.check_for_update",
        lambda _v, *args, **kwargs: {
            "version": "v1.2.3",
            "is_installed": True,
            "download_url": "https://github.com/fake/tradutor-ebook-setup.exe",
            "filename": "tradutor-ebook-setup.exe",
        },
    )

    download_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.download_update",
        lambda url, ver, filename: download_called.append((url, ver, filename)) or True,
    )

    launch_called = []
    monkeypatch.setattr(
        "tradutor.infra.updater.launch_installer_and_exit",
        lambda path=None: launch_called.append(path),
    )

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            # Clica no botão "Verificar atualizações"
            await pilot.click("#check-now")
            await wait_for(pilot, lambda: isinstance(app.screen, UpdateModal))

            assert isinstance(app.screen, UpdateModal)
            assert app.screen.state == "prompt"

            # Clica em Baixar e Atualizar no modal
            await pilot.click("#download-btn")
            await wait_for(pilot, lambda: len(launch_called) > 0)

            assert len(download_called) == 1
            assert download_called[0][1] == "v1.2.3"
            assert len(launch_called) == 1

    asyncio.run(run(TradutorApp(env=env)))


def test_manual_check_no_update_notifies(tmp_path, monkeypatch):
    """Testa checagem manual quando não há atualizações disponíveis."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    env = make_env(tmp_path, key="sk-123")

    monkeypatch.setattr(
        "tradutor.infra.updater.check_for_update",
        lambda _v, *args, **kwargs: None,
    )

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            await pilot.click("#check-now")
            await pilot.pause(0.5)

            assert not isinstance(app.screen, UpdateModal)

    asyncio.run(run(TradutorApp(env=env)))


def test_updater_prevented_when_not_frozen(tmp_path, monkeypatch):
    """Testa que opções do updater são ocultadas quando não for executável compilado Windows."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: False)
    env = make_env(tmp_path, key="sk-123")

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            assert app.screen.query_one("#updates-label").display is False
            assert app.screen.query_one("#auto-check").display is False
            assert app.screen.query_one("#check-now").display is False

    asyncio.run(run(TradutorApp(env=env)))


def test_update_download_failure_shows_error_state(tmp_path, monkeypatch):
    """Testa transição para estado de erro quando o download falha e fechamento pelo close-btn."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    monkeypatch.setattr(
        "tradutor.infra.updater.check_for_update",
        lambda _v, *args, **kwargs: {
            "version": "v1.2.3",
            "is_installed": True,
            "download_url": "https://github.com/fake/tradutor-ebook-setup.exe",
            "filename": "tradutor-ebook-setup.exe",
        },
    )
    monkeypatch.setattr(
        "tradutor.infra.updater.download_update",
        lambda url, ver, filename: False,
    )
    env = make_env(tmp_path, key="sk-123")

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            # Clica no botão "Verificar atualizações"
            await pilot.click("#check-now")
            await wait_for(pilot, lambda: isinstance(app.screen, UpdateModal))

            assert isinstance(app.screen, UpdateModal)
            modal = app.screen

            # Dispara download com erro
            await pilot.click("#download-btn")
            await wait_for(pilot, lambda: modal.state == "error")

            assert modal.state == "error"
            # Clica em fechar
            await pilot.click("#close-btn")
            await pilot.pause()
            assert not isinstance(app.screen, UpdateModal)

    asyncio.run(run(TradutorApp(env=env)))


def test_update_modal_cancel_button(tmp_path, monkeypatch):
    """Testa fechamento do modal ao clicar no botão Cancelar."""
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    monkeypatch.setattr(
        "tradutor.infra.updater.check_for_update",
        lambda _v, *args, **kwargs: {
            "version": "v1.2.3",
            "is_installed": True,
            "download_url": "https://github.com/fake/tradutor-ebook-setup.exe",
            "filename": "tradutor-ebook-setup.exe",
        },
    )
    env = make_env(tmp_path, key="sk-123")

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            app.push_screen("config")
            await pilot.pause()

            # Clica no botão "Verificar atualizações"
            await pilot.click("#check-now")
            await wait_for(pilot, lambda: isinstance(app.screen, UpdateModal))

            assert isinstance(app.screen, UpdateModal)

            # Clica em Cancelar
            await pilot.click("#cancel-btn")
            await pilot.pause(0.5)
            assert not isinstance(app.screen, UpdateModal)

    asyncio.run(run(TradutorApp(env=env)))


def test_update_modal_launch_exception_shows_error(tmp_path, monkeypatch):
    """Testa transição para estado de erro caso o disparo do instalador lance exceção."""
    env = make_env(tmp_path, key="sk-123")

    monkeypatch.setattr("tradutor.infra.updater.download_update", lambda *args, **kwargs: True)

    def mock_launch_fail(path=None):
        raise OSError("Failed to launch installer")

    monkeypatch.setattr("tradutor.infra.updater.launch_installer_and_exit", mock_launch_fail)

    update_info = {
        "version": "v1.2.3",
        "is_installed": True,
        "download_url": "https://github.com/fake/tradutor-ebook-setup.exe",
        "filename": "tradutor-ebook-setup.exe",
    }

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            modal = UpdateModal(update_info)
            app.push_screen(modal)
            await pilot.pause()

            await pilot.click("#download-btn")
            await wait_for(pilot, lambda: modal.state == "error")

            assert modal.state == "error"
            await pilot.click("#close-btn")
            await pilot.pause()
            assert not isinstance(app.screen, UpdateModal)

    asyncio.run(run(TradutorApp(env=env)))


def test_portable_mode_modal_fallback_url_and_close(tmp_path, monkeypatch):
    """Testa fechamento do modal no modo portátil e fallback da URL de release."""
    env = make_env(tmp_path, key="sk-123")

    browser_opened = []
    monkeypatch.setattr(
        "tradutor.infra.updater.open_release_url",
        lambda url: browser_opened.append(url) or True,
    )

    update_info = {
        "version": "v1.2.3",
        "is_installed": False,
    }

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            modal = UpdateModal(update_info)
            app.push_screen(modal)
            await pilot.pause()

            # Fecha pelo botão fechar
            await pilot.click("#close-btn")
            await pilot.pause()
            assert not isinstance(app.screen, UpdateModal)

            # Abre novamente e clica em abrir no navegador para testar URL default de fallback
            modal2 = UpdateModal(update_info)
            app.push_screen(modal2)
            await pilot.pause()

            await pilot.click("#browser-btn")
            await pilot.pause(0.5)

            assert len(browser_opened) == 1
            assert "releases" in browser_opened[0]

    asyncio.run(run(TradutorApp(env=env)))
