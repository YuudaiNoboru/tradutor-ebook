"""Testes unitários do módulo updater."""

from __future__ import annotations

import os
import subprocess
import sys

import httpx
import pytest
import respx

from tradutor.infra.updater import (
    GITHUB_API_URL,
    SETUP_FILENAME,
    check_for_update,
    clear_pending_update,
    download_update,
    get_cache_dir,
    get_installer_path,
    is_frozen_windows,
    is_installed_mode,
    launch_installer_and_exit,
    open_release_url,
    parse_version,
)


def test_parse_version():
    assert parse_version("v0.4.0") == (0, 4, 0)
    assert parse_version("0.3.1") == (0, 3, 1)
    assert parse_version("v1") == (1,)
    assert parse_version("invalid") == (0,)


def test_is_frozen_windows(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert is_frozen_windows() is True

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert is_frozen_windows() is False

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    assert is_frozen_windows() is False


def test_is_installed_mode(tmp_path, monkeypatch):
    # Quando não é frozen e executable_path não é passado, retorna False
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: False)
    assert is_installed_mode() is False

    # Quando executable_path é passado explicitamente
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    exe_path = app_dir / "tradutor.exe"
    exe_path.touch()

    # Sem unins000.exe
    assert is_installed_mode(exe_path) is False

    # Com unins000.exe presente
    uninstaller = app_dir / "unins000.exe"
    uninstaller.touch()
    assert is_installed_mode(exe_path) is True

    # Quando is_frozen_windows é True e usa sys.executable
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    assert is_installed_mode() is True


def test_get_cache_dir_and_installer_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tradutor.infra.updater.platformdirs.user_cache_dir", lambda app: str(tmp_path / app)
    )
    cache_dir = get_cache_dir()
    assert cache_dir == tmp_path / "tradutor-ebook"

    installer_path = get_installer_path("custom-setup.exe")
    assert installer_path == cache_dir / "custom-setup.exe"


def test_clear_pending_update(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    files = [
        tmp_path / SETUP_FILENAME,
        tmp_path / f"{SETUP_FILENAME}.tmp",
        tmp_path / "pending_update.exe",
        tmp_path / "pending_update.json",
        tmp_path / "pending_update.exe.tmp",
        tmp_path / "update_helper.ps1",
        tmp_path / "update_helper.bat",
    ]
    for f in files:
        f.touch()

    clear_pending_update()

    for f in files:
        assert not f.exists()


@respx.mock
def test_check_for_update_no_new_version():
    respx.get(GITHUB_API_URL).mock(return_value=httpx.Response(200, json={"tag_name": "v0.3.0"}))
    assert check_for_update("v0.3.0") is None
    assert check_for_update("v0.4.0") is None


@respx.mock
def test_check_for_update_empty_tag():
    respx.get(GITHUB_API_URL).mock(return_value=httpx.Response(200, json={"tag_name": ""}))
    assert check_for_update("v0.3.0") is None


@respx.mock
def test_check_for_update_installed_mode_finds_setup(tmp_path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    exe_path = app_dir / "tradutor.exe"
    exe_path.touch()
    (app_dir / "unins000.exe").touch()

    payload = {
        "tag_name": "v0.4.0",
        "html_url": "https://github.com/YuudaiNoboru/tradutor-ebook/releases/tag/v0.4.0",
        "assets": [
            {
                "name": "tradutor.exe",
                "browser_download_url": "https://github.com/download/tradutor.exe",
            },
            {
                "name": "tradutor-ebook-setup.exe",
                "browser_download_url": "https://github.com/download/tradutor-ebook-setup.exe",
            },
        ],
    }
    respx.get(GITHUB_API_URL).mock(return_value=httpx.Response(200, json=payload))

    result = check_for_update("v0.3.0", executable_path=exe_path)
    assert result is not None
    assert result["version"] == "v0.4.0"
    assert result["is_installed"] is True
    assert result["download_url"] == "https://github.com/download/tradutor-ebook-setup.exe"
    assert result["filename"] == "tradutor-ebook-setup.exe"


@respx.mock
def test_check_for_update_installed_mode_fallback_setup_exe(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    exe_path = app_dir / "tradutor.exe"
    exe_path.touch()
    (app_dir / "unins000.exe").touch()

    payload = {
        "tag_name": "v0.4.0",
        "assets": [
            {
                "name": "setup-custom.exe",
                "browser_download_url": "https://github.com/download/setup-custom.exe",
            },
        ],
    }
    respx.get(GITHUB_API_URL).mock(return_value=httpx.Response(200, json=payload))

    result = check_for_update("v0.3.0", executable_path=exe_path)
    assert result is not None
    assert result["is_installed"] is True
    assert result["download_url"] == "https://github.com/download/setup-custom.exe"
    assert result["filename"] == "setup-custom.exe"


@respx.mock
def test_check_for_update_portable_mode(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    exe_path = app_dir / "tradutor.exe"
    exe_path.touch()

    payload = {
        "tag_name": "v0.4.0",
        "html_url": "https://github.com/YuudaiNoboru/tradutor-ebook/releases/tag/v0.4.0",
        "assets": [
            {
                "name": "tradutor.exe",
                "browser_download_url": "https://github.com/download/tradutor.exe",
            },
        ],
    }
    respx.get(GITHUB_API_URL).mock(return_value=httpx.Response(200, json=payload))

    result = check_for_update("v0.3.0", executable_path=exe_path)
    assert result is not None
    assert result["version"] == "v0.4.0"
    assert result["is_installed"] is False
    assert (
        result["release_url"]
        == "https://github.com/YuudaiNoboru/tradutor-ebook/releases/tag/v0.4.0"
    )


@respx.mock
def test_check_for_update_network_error():
    respx.get(GITHUB_API_URL).mock(side_effect=httpx.ConnectError("Connection failed"))
    assert check_for_update("v0.3.0") is None


@respx.mock
def test_check_for_update_propagates_network_error():
    respx.get(GITHUB_API_URL).mock(side_effect=httpx.ConnectError("Connection failed"))
    with pytest.raises(httpx.ConnectError):
        check_for_update("v0.3.0", propagate_errors=True)


@respx.mock
def test_download_update_success(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    # Conteúdo com cabeçalho MZ e tamanho > 1024 bytes
    fake_pe_content = b"MZ" + b"\x00" * 2048
    download_url = "https://github.com/download/tradutor-ebook-setup.exe"
    respx.get(download_url).mock(return_value=httpx.Response(200, content=fake_pe_content))

    # Cria arquivo existente anterior para testar sobrescrita
    (tmp_path / SETUP_FILENAME).write_bytes(b"old")

    success = download_update(download_url, "v0.4.0", SETUP_FILENAME)
    assert success is True

    dest_file = tmp_path / SETUP_FILENAME
    assert dest_file.exists()
    assert dest_file.read_bytes() == fake_pe_content
    assert not (tmp_path / f"{SETUP_FILENAME}.tmp").exists()


def test_download_update_empty_url():
    assert download_update("") is False


@respx.mock
def test_download_update_invalid_header(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    # Tamanho > 1024 bytes mas sem cabeçalho MZ
    fake_content = b"XX" + b"\x00" * 2048
    download_url = "https://github.com/download/setup.exe"
    respx.get(download_url).mock(return_value=httpx.Response(200, content=fake_content))

    success = download_update(download_url, "v0.4.0", "setup.exe")
    assert success is False
    assert not (tmp_path / "setup.exe").exists()
    assert not (tmp_path / "setup.exe.tmp").exists()


@respx.mock
def test_download_update_too_small(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    # Cabeçalho MZ mas tamanho < 1024 bytes
    fake_content = b"MZ\x00\x00"
    download_url = "https://github.com/download/setup.exe"
    respx.get(download_url).mock(return_value=httpx.Response(200, content=fake_content))

    success = download_update(download_url, "v0.4.0", "setup.exe")
    assert success is False
    assert not (tmp_path / "setup.exe").exists()


@respx.mock
def test_download_update_http_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    download_url = "https://github.com/download/setup.exe"
    respx.get(download_url).mock(return_value=httpx.Response(500))

    success = download_update(download_url, "v0.4.0", "setup.exe")
    assert success is False
    assert not (tmp_path / "setup.exe").exists()


def test_launch_installer_and_exit_success(tmp_path):
    installer_file = tmp_path / "setup.exe"
    installer_file.write_bytes(b"MZ\x00\x00")

    popen_called = []
    exit_called = []

    def mock_popen(args, **kwargs):
        popen_called.append((args, kwargs))

    def mock_exit(code):
        exit_called.append(code)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(os, "_exit", mock_exit)

    try:
        launch_installer_and_exit(installer_file)
        assert len(popen_called) == 1
        args, kwargs = popen_called[0]
        assert args[0] == str(installer_file)
        assert kwargs.get("close_fds") is True
        assert exit_called == [0]
    finally:
        monkeypatch.undo()


def test_launch_installer_and_exit_file_not_found(tmp_path, monkeypatch):
    non_existent = tmp_path / "non_existent_setup.exe"
    monkeypatch.setattr("tradutor.infra.updater.get_installer_path", lambda: non_existent)

    with pytest.raises(FileNotFoundError, match="Instalador não encontrado"):
        launch_installer_and_exit()


def test_open_release_url(monkeypatch):
    opened = []
    monkeypatch.setattr(
        "tradutor.infra.updater.webbrowser.open", lambda url: opened.append(url) or True
    )

    assert open_release_url("https://github.com/release") is True
    assert opened == ["https://github.com/release"]

    def mock_open_err(url):
        raise OSError("Browser error")

    monkeypatch.setattr("tradutor.infra.updater.webbrowser.open", mock_open_err)
    assert open_release_url("https://github.com/release") is False
