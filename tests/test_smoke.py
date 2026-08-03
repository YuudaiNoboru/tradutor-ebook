import re

from tradutor import __version__
from tradutor.cli import main


def test_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_main_prints_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out
