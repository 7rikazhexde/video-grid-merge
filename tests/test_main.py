import builtins
import io
import os
import sys
import time
from concurrent.futures import Future
from typing import Any, List, Optional

import pytest
from _pytest.fixtures import FixtureRequest
from pytest import MonkeyPatch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_dir = os.path.dirname(os.path.abspath(__file__))

from video_grid_merge import __main__ as main

from .conftest import FFMPEG_CMD_VERSIONS

sys.stdin = io.StringIO()


@pytest.mark.parametrize("version", [*FFMPEG_CMD_VERSIONS, "invalid"])
def test_main_all_versions(
    version: str,
    mock_file_operations: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "ffmpeg_cmd_version", version)
    if version == "invalid":
        with pytest.raises(ValueError, match="Invalid ffmpeg_cmd_version: invalid"):
            main.main()
    else:
        main.main()
        captured = capsys.readouterr()
        assert "Video Grid Merge Start" in captured.out
        assert "Video Grid Merge End And Output Success" in captured.out
        assert f"Executing command: ffmpeg_command_{version}" in captured.out


def test_main_with_non_square_number_of_videos(
    mock_file_operations: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mock_get_video_files(folder: str) -> List[str]:
        return [
            "video1.mp4",
            "video2.mp4",
            "video3.mp4",
        ]  # 3 videos (not square number)

    monkeypatch.setattr(main, "get_video_files", mock_get_video_files)

    with pytest.raises(SystemExit):
        main.main()


def test_safe_input_with_none_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "original_terminal_settings", None)
    monkeypatch.setattr(builtins, "input", lambda _: "test input")
    result = main.safe_input("Prompt: ")
    assert result == "test input"


def test_create_target_video_empty_list(
    mock_get_video_length: Any, mock_process_video: Any, mock_thread_pool: Any
) -> None:
    main.create_target_video("/input", [])
    assert len(mock_thread_pool.submitted_tasks) == 0


def test_create_target_video_all_none_lengths(
    mock_get_video_length: Any,
    mock_process_video: Any,
    mock_thread_pool: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: None
    )
    main.create_target_video("/input", ["video1.mp4", "video2.mp4"])
    assert len(mock_thread_pool.submitted_tasks) == 0


def test_create_target_video_some_valid_lengths(
    mock_get_video_length: Any,
    mock_process_video: Any,
    mock_thread_pool: Any,
    monkeypatch: Any,
) -> None:
    lengths = [10.0, None, 15.0]
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: lengths.pop(0)
    )

    main.create_target_video("/input", ["video1.mp4", "video2.mp4", "video3.mp4"])

    assert len(mock_thread_pool.submitted_tasks) == 3
    for task in mock_thread_pool.submitted_tasks:
        assert task[0] == main.process_video
        assert task[1][0] == "/input"
        assert task[1][2] == 15.0


def test_create_target_video_exception_in_thread(
    mock_get_video_length: Any,
    mock_process_video: Any,
    mock_thread_pool: Any,
    monkeypatch: Any,
) -> None:
    def mock_submit(*args: Any) -> Future[None]:
        future: Future[None] = Future()
        future.set_exception(Exception("Test exception"))
        return future

    monkeypatch.setattr(mock_thread_pool, "submit", mock_submit)

    with pytest.raises(Exception, match="Test exception"):
        main.create_target_video("/input", ["video1.mp4"])


@pytest.mark.parametrize(
    "lengths,expected_max",
    [
        ([10.0, 15.0, 5.0], 15.0),
        ([None, 10.0, None], 10.0),
        ([10.0], 10.0),
    ],
)
def test_create_target_video_various_lengths(
    mock_get_video_length: Any,
    mock_process_video: Any,
    mock_thread_pool: Any,
    monkeypatch: Any,
    lengths: List[Optional[float]],
    expected_max: float,
) -> None:
    length_iter = iter(lengths)
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: next(length_iter)
    )

    main.create_target_video("/input", [f"video{i}.mp4" for i in range(len(lengths))])

    assert len(mock_thread_pool.submitted_tasks) == len(lengths)
    for task in mock_thread_pool.submitted_tasks:
        assert task[0] == main.process_video
        assert task[1][0] == "/input"
        assert task[1][2] == expected_max


video_extension_list = [".mov", ".mp4"]


def test_main_with_different_versions(
    ffmpeg_cmd_version: str,
    mock_file_operations: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "ffmpeg_cmd_version", ffmpeg_cmd_version)
    main.main()
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out
    assert f"Executing command: ffmpeg_command_{ffmpeg_cmd_version}" in captured.out


def test_main_with_invalid_version(
    mock_file_operations: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "ffmpeg_cmd_version", "invalid")
    with pytest.raises(ValueError, match="Invalid ffmpeg_cmd_version: invalid"):
        main.main()


def test_main_with_insufficient_videos(
    mock_file_operations: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mock_get_video_files(folder: str) -> List[str]:
        return ["video1.mp4", "video2.mp4"]  # 不十分なビデオ数

    monkeypatch.setattr(main, "get_video_files", mock_get_video_files)

    with pytest.raises(SystemExit):
        main.main()


@pytest.mark.parametrize(
    "input_folder,output_folder",
    [
        ("/custom/input", None),
        (None, "/custom/output"),
        ("/custom/input", "/custom/output"),
    ],
)
def test_main_with_custom_folders(
    input_folder: Optional[str],
    output_folder: Optional[str],
    mock_file_operations: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main.main(input_folder=input_folder, output_folder=output_folder)
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out


def test_main(
    ffmpeg_cmd_version: str,
    mock_file_operations: FixtureRequest,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    from video_grid_merge.__main__ import main

    # Set the ffmpeg_cmd_version for this test
    monkeypatch.setattr(
        "video_grid_merge.__main__.ffmpeg_cmd_version", ffmpeg_cmd_version
    )

    main()
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out

    # Assert based on the ffmpeg_cmd_version
    assert f"Executing command: ffmpeg_command_{ffmpeg_cmd_version}" in captured.out


def test_main_success_case(capsys: Any, mock_file_operations: Any) -> None:
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(time, "perf_counter", lambda: 1.0)

        main.main()

        captured = capsys.readouterr()
        assert "Video Grid Merge Start" in captured.out
        assert "Video Grid Merge End And Output Success" in captured.out
        assert "File Output Complete: /path/to/output_file.mov" in captured.out
        assert "Processing Time(s): " in captured.out


def test_main_error_case(capsys: Any, monkeypatch: Any) -> None:
    def mock_get_video_files(directory: str) -> List[str]:
        return []

    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_files", mock_get_video_files
    )

    input_folder = "video_grid_merge/media/input"

    with pytest.raises(SystemExit) as e:
        main.main(input_folder=input_folder)

    assert (
        str(e.value)
        == f"Error: Please store a perfect square number (>= 4) of video files in the input folder.\ninput_folder: {input_folder}"
    )


def test_main_with_specified_folders(capsys: Any, mock_file_operations: Any) -> None:
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(time, "perf_counter", lambda: 1.0)

        main.main(input_folder="custom_input", output_folder="custom_output")

        captured = capsys.readouterr()
        assert "Video Grid Merge Start" in captured.out
        assert "Video Grid Merge End And Output Success" in captured.out
        assert "File Output Complete: /path/to/output_file.mov" in captured.out
        assert "Processing Time(s): " in captured.out
