import io
import os
import sys
import termios
from typing import Any, List, Tuple

import pytest
from pytest import MonkeyPatch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_grid_merge import __main__ as main

video_extension_list = [".mov", ".mp4"]


@pytest.mark.parametrize(
    "user_input,expected",
    [
        ("test_input", "test_input"),
        ("", ""),
        ("long input with spaces", "long input with spaces"),
    ],
)
def test_safe_input(
    user_input: str,
    expected: str,
    mock_terminal: Tuple[Any, Any, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    _, _, mock_stdin = mock_terminal

    # 標準入力をモック
    mock_stdin.readline = lambda: user_input + "\n"

    # 標準出力をキャプチャ
    captured_output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured_output)

    def mock_tcflush(*args: Any) -> None:
        pass

    monkeypatch.setattr(termios, "tcflush", mock_tcflush)

    # input 関数をモック
    def mock_input(prompt: str) -> str:
        print(prompt, end="", flush=True)  # プロンプトを出力
        return user_input

    monkeypatch.setattr("builtins.input", mock_input)

    result = main.safe_input("Enter input: ")

    # 結果を検証
    assert result == expected
    assert captured_output.getvalue() == "Enter input: "


def test_safe_input_no_original_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "original_terminal_settings", None)
    monkeypatch.setattr("builtins.input", lambda _: "test")
    result = main.safe_input("Prompt: ")
    assert result == "test"


def test_safe_input_with_error(monkeypatch: MonkeyPatch) -> None:
    def mock_tcflush(*args: Any) -> None:
        raise termios.error("Mock error")

    monkeypatch.setattr(termios, "tcflush", mock_tcflush)
    monkeypatch.setattr(main, "original_terminal_settings", object())
    monkeypatch.setattr("builtins.input", lambda _: "test")
    result = main.safe_input("Prompt: ")
    assert result == "test"


@pytest.mark.parametrize(
    "input_sequence,os_path_exists_sequence,expected_output",
    [
        ([""], [False], "/output/combined_video.mov"),
        (["my_video"], [False], "/output/my_video.mov"),
        (["my_video.mp4"], [False], "/output/my_video.mp4"),
        (["existing_video", "y"], [True], "/output/existing_video.mov"),
        (["existing_video", "n", "new_video"], [True, False], "/output/new_video.mov"),
        (
            ["video1", "n", "video2", "n", "video3"],
            [True, True, False],
            "/output/video3.mov",
        ),
        (["existing_video", "n", ""], [True, False], "/output/combined_video.mov"),
    ],
)
def test_get_output_filename_from_user(
    input_sequence: List[str],
    os_path_exists_sequence: List[bool],
    expected_output: str,
    mock_safe_input: List[str],
    mock_os_path_exists: List[bool],
) -> None:
    mock_safe_input.extend(input_sequence)
    mock_os_path_exists.extend(os_path_exists_sequence)
    result = main.get_output_filename_from_user("/output")
    assert result == expected_output
