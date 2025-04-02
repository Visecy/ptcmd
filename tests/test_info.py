from typing import Any, List
from unittest import mock

import pytest

from ptcmd import Cmd
from ptcmd.info import CommandInfo, build_cmd_info


@pytest.fixture
def app() -> Cmd:
    return Cmd()


def test_init() -> None:
    info = CommandInfo(name="test", cmd_func=lambda argv: None)
    assert info.name == "test"
    assert info.cmd_func([]) is None
    assert info.help_func is None
    assert info.argparser is None
    assert info.completer is None
    assert info.category is None
    assert info.hidden is False
    assert info.disabled is False
    assert info.__cmd_info__(mock.Mock()) is info


def test_build_cmd_info(app: Cmd) -> None:
    def do_test(self: Any, argv: List[str]) -> None:
        """Test"""

    info = build_cmd_info(do_test, app)
    assert info.name == "test"
    assert info.cmd_func([]) is None
    assert info.help_func is None
