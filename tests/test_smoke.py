from tradutor import __version__
from tradutor.cli import main


def test_version():
    assert __version__ == "0.1.0"


def test_main_prints_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out
