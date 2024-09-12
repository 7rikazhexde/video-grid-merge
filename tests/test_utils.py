import os
import sys
import termios
from typing import Any, Callable, List, Optional

import pytest
from pytest import MonkeyPatch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_grid_merge import __main__ as main


def test_reset_terminal(mock_terminal: Any, monkeypatch: MonkeyPatch) -> None:
    mock_tcsetattr, _, _ = mock_terminal

    mock_original_settings = object()
    monkeypatch.setattr(main, "original_terminal_settings", mock_original_settings)

    main.reset_terminal()

    mock_tcsetattr.assert_called_once_with(
        sys.stdin, termios.TCSADRAIN, mock_original_settings
    )


def test_atexit_register(monkeypatch: MonkeyPatch) -> None:
    called_functions: List[Callable[[], None]] = []

    def mock_register(func: Callable[[], None]) -> None:
        called_functions.append(func)

    monkeypatch.setattr("atexit.register", mock_register)

    import importlib

    importlib.reload(main)

    assert len(called_functions) == 1
    assert called_functions[0] == main.reset_terminal


def test_reset_terminal_no_original_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "original_terminal_settings", None)
    main.reset_terminal()  # Verify that no errors occur


def test_reset_terminal_with_error(monkeypatch: MonkeyPatch) -> None:
    def mock_tcsetattr(*args: Any) -> None:
        raise termios.error("Mock error")

    monkeypatch.setattr(termios, "tcsetattr", mock_tcsetattr)
    monkeypatch.setattr(main, "original_terminal_settings", object())
    main.reset_terminal()  # Verify that no errors occur


def test_original_terminal_settings_error(monkeypatch: MonkeyPatch) -> None:
    def mock_tcgetattr(*args: Any) -> None:
        raise termios.error("Mock termios error")

    monkeypatch.setattr(termios, "tcgetattr", mock_tcgetattr)

    import importlib

    importlib.reload(main)

    assert main.original_terminal_settings is None


@pytest.mark.parametrize(
    "length,max_length", [(None, 10.0), (10.0, None), (None, None)]
)
def test_process_video_none_values(
    mock_environment: Any,
    monkeypatch: Any,
    length: Optional[float],
    max_length: Optional[float],
) -> None:
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: length
    )

    if max_length is not None:
        main.process_video("/input", "test.mp4", max_length)
    else:
        pytest.skip("Skipping test when max_length is None")

    assert not mock_environment.content
