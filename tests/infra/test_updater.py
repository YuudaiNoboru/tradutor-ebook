"""Testes unitários do módulo updater."""

from __future__ import annotations

import json
import subprocess
import sys

import httpx
import respx

from tradutor.infra.updater import (
    check_delayed_update,
    check_for_update,
    download_update,
    get_pending_update_paths,
    parse_version,
    run_helper_and_exit,
)


def test_parse_version():
    assert parse_version("v0.4.0") == (0, 4, 0)
    assert parse_version("0.3.1") == (0, 3, 1)
    assert parse_version("v1") == (1,)
    assert parse_version("invalid") == (0,)


@respx.mock
def test_check_for_update_no_new_version():
    respx.get("https://api.github.com/repos/YuudaiNoboru/tradutor-ebook/releases/latest").mock(
        return_value=httpx.Response(200, json={"tag_name": "v0.3.0"})
    )
    assert check_for_update("v0.3.0") is None
    assert check_for_update("v0.4.0") is None


@respx.mock
def test_check_for_update_new_version_with_exe():
    payload = {
        "tag_name": "v0.4.0",
        "assets": [
            {
                "name": "tradutor.zip",
                "browser_download_url": "https://github.com/download/tradutor.zip",
            },
            {
                "name": "tradutor.exe",
                "browser_download_url": "https://github.com/download/tradutor.exe",
            },
        ],
    }
    respx.get("https://api.github.com/repos/YuudaiNoboru/tradutor-ebook/releases/latest").mock(
        return_value=httpx.Response(200, json=payload)
    )
    result = check_for_update("v0.3.0")
    assert result is not None
    assert result["version"] == "v0.4.0"
    assert result["download_url"] == "https://github.com/download/tradutor.exe"
    assert result["filename"] == "tradutor.exe"


@respx.mock
def test_check_for_update_new_version_no_exe():
    payload = {
        "tag_name": "v0.4.0",
        "assets": [
            {
                "name": "tradutor.zip",
                "browser_download_url": "https://github.com/download/tradutor.zip",
            }
        ],
    }
    respx.get("https://api.github.com/repos/YuudaiNoboru/tradutor-ebook/releases/latest").mock(
        return_value=httpx.Response(200, json=payload)
    )
    assert check_for_update("v0.3.0") is None


@respx.mock
def test_check_for_update_network_error():
    respx.get("https://api.github.com/repos/YuudaiNoboru/tradutor-ebook/releases/latest").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )
    assert check_for_update("v0.3.0") is None


@respx.mock
def test_check_for_update_propagates_network_error():
    import pytest

    respx.get("https://api.github.com/repos/YuudaiNoboru/tradutor-ebook/releases/latest").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )
    with pytest.raises(httpx.ConnectError):
        check_for_update("v0.3.0", propagate_errors=True)


@respx.mock
def test_download_update_success(tmp_path, monkeypatch):
    # Mock get_cache_dir to return tmp_path
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    download_url = "https://github.com/download/tradutor.exe"
    respx.get(download_url).mock(return_value=httpx.Response(200, content=b"fake exe content"))

    success = download_update(download_url, "v0.4.0", "tradutor.exe")
    assert success is True

    pending_exe, pending_json = get_pending_update_paths()
    assert pending_exe.exists()
    assert pending_json.exists()
    assert pending_exe.read_bytes() == b"fake exe content"

    manifest = json.loads(pending_json.read_text(encoding="utf-8"))
    assert manifest["version"] == "v0.4.0"
    assert manifest["filename"] == "tradutor.exe"


@respx.mock
def test_download_update_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    download_url = "https://github.com/download/tradutor.exe"
    respx.get(download_url).mock(return_value=httpx.Response(500))

    success = download_update(download_url, "v0.4.0", "tradutor.exe")
    assert success is False

    pending_exe, pending_json = get_pending_update_paths()
    assert not pending_exe.exists()
    assert not pending_json.exists()


def test_check_delayed_update(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)

    # Empty cache
    assert check_delayed_update("v0.3.0") is None

    pending_exe, pending_json = get_pending_update_paths()

    # Only exe exists
    pending_exe.write_bytes(b"some content")
    assert check_delayed_update("v0.3.0") is None

    # Both exist, but version is same
    manifest = {"version": "v0.3.0", "filename": "tradutor.exe"}
    pending_json.write_text(json.dumps(manifest), encoding="utf-8")
    assert check_delayed_update("v0.3.0") is None

    # Both exist, version is newer
    manifest = {"version": "v0.4.0", "filename": "tradutor.exe"}
    pending_json.write_text(json.dumps(manifest), encoding="utf-8")
    result = check_delayed_update("v0.3.0")
    assert result is not None
    assert result["version"] == "v0.4.0"
    assert result["filename"] == "tradutor.exe"
    assert result["exe_path"] == str(pending_exe)
    assert result["json_path"] == str(pending_json)


def test_run_helper_and_exit(tmp_path, monkeypatch):
    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: True)

    pending_exe = tmp_path / "pending_update.exe"
    pending_json = tmp_path / "pending_update.json"
    current_exe = tmp_path / "tradutor.exe"

    pending_exe.touch()
    pending_json.touch()
    current_exe.touch()

    # Mock subprocess.Popen and sys.exit
    popen_called = []

    def mock_popen(args, **kwargs):
        popen_called.append(args)

        # Return a dummy object
        class DummyProcess:
            pass

        return DummyProcess()

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    exit_called = []
    monkeypatch.setattr(sys, "exit", lambda code: exit_called.append(code))

    run_helper_and_exit(pending_exe, pending_json, current_exe)

    assert len(popen_called) == 1
    assert len(exit_called) == 1
    assert exit_called[0] == 0

    # Verify batch script was created
    bat_path = pending_exe.parent / "update_helper.bat"
    assert bat_path.exists()
    bat_content = bat_path.read_text(encoding="utf-8")
    assert "copy /Y" in bat_content
    assert "pending_update.exe" in bat_content
    assert "tradutor.exe" in bat_content


def test_run_helper_and_exit_raises_in_dev_mode(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr("tradutor.infra.updater.get_cache_dir", lambda: tmp_path)
    monkeypatch.setattr("tradutor.infra.updater.is_frozen_windows", lambda: False)

    pending_exe = tmp_path / "pending_update.exe"
    pending_json = tmp_path / "pending_update.json"

    with pytest.raises(RuntimeError, match="Auto-update is only supported"):
        run_helper_and_exit(pending_exe, pending_json)
