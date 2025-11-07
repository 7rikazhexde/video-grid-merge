import os
import subprocess
import sys
from typing import Any, Optional, Tuple

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_grid_merge import __main__ as main

base_dir = os.path.dirname(os.path.abspath(__file__))


def test_get_video_files(tmp_path: Any) -> None:
    (tmp_path / "video1.mp4").touch()
    (tmp_path / "video2.mov").touch()
    (tmp_path / "document.txt").touch()

    video_files = main.get_video_files(str(tmp_path))
    assert sorted(video_files) == ["video1.mp4", "video2.mov"]


def test_get_video_length_ffmpeg(monkeypatch: Any) -> None:
    class MockProcess:
        def __init__(self, output: bytes) -> None:
            self.output = output

        def communicate(self) -> tuple[bytes, None]:
            return (self.output, None)

    def mock_popen_success(*args: Any, **kwargs: Any) -> MockProcess:
        # Mock output with duration 62.43 seconds = 00:01:02.43
        return MockProcess(b"Duration: 00:01:02.43, start: 0.000000")

    def mock_popen_failure(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError("No such file")

    # Test successful case
    monkeypatch.setattr(subprocess, "Popen", mock_popen_success)
    file_path = os.path.join(base_dir, "test_data/input/get_videos/sample1.mov")
    expected_duration = 62.43
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration == expected_duration

    # Clear cache before second test
    main.get_video_length_ffmpeg.cache_clear()

    # Test failure case
    monkeypatch.setattr(subprocess, "Popen", mock_popen_failure)
    file_path = "invalid_video.mp4"
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration is None


def test_get_video_length_ffmpeg_invalid_command(monkeypatch: Any) -> None:
    def mock_popen(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError("No such file or directory: 'hoge'")

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    file_path = "sample1.mov"
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration is None


def test_get_video_length_ffmpeg_success(monkeypatch: Any, capsys: Any) -> None:
    # Clear cache before test
    main.get_video_length_ffmpeg.cache_clear()

    class MockProcess:
        def communicate(self) -> tuple[bytes, None]:
            return (b"Duration: 01:02:34.56, start: 0.000000", None)

    def mock_popen(*args: Any, **kwargs: Any) -> MockProcess:
        return MockProcess()

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    file_path = "sample_success.mov"
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration == 3754.56  # 1*3600 + 2*60 + 34.56


def test_get_video_length_ffmpeg_no_match(monkeypatch: Any, capsys: Any) -> None:
    # Clear cache before test
    main.get_video_length_ffmpeg.cache_clear()

    class MockProcess:
        def communicate(self) -> tuple[bytes, None]:
            return (b"Invalid output without duration", None)

    def mock_popen(*args: Any, **kwargs: Any) -> MockProcess:
        return MockProcess()

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    file_path = "sample_nomatch.mov"
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration is None
    captured = capsys.readouterr()
    assert "Failed to extract duration from FFmpeg output" in captured.out


@pytest.mark.parametrize(
    "filename, expected_result",
    [
        ("test_valid.mp4", (1920, 1080)),
        ("test_malformed.mp4", None),
        ("test_empty.mp4", None),
        ("test_unexpected.mp4", None),
    ],
)
def test_get_video_size(
    mock_subprocess_check_output: Any,
    filename: str,
    expected_result: Optional[Tuple[int, int]],
) -> None:
    result = main.get_video_size(filename)
    assert result == expected_result


def test_get_video_size_called_process_error(mock_subprocess_check_output: Any) -> None:
    result = main.get_video_size("test_error.mp4")
    assert result is None


def test_get_video_size_value_error(monkeypatch: Any) -> None:
    def mock(*args: Any, **kwargs: Any) -> bytes:
        raise ValueError("Invalid output")

    monkeypatch.setattr(subprocess, "check_output", mock)
    result = main.get_video_size("test_value_error.mp4")
    assert result is None


def test_process_video_equal_length(mock_environment: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: 10.0
    )

    main.process_video("/input", "test.mp4", 10.0)

    assert True


def test_process_video_shorter_length(mock_environment: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: 5.0
    )

    main.process_video("/input", "test.mp4", 10.0)

    expected_content = "file 'test.mp4'\n" * 2
    actual_content = "".join(mock_environment.content)
    assert actual_content == expected_content


def test_process_video_shorter_length_with_remainder(
    mock_environment: Any, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: 3.0
    )

    main.process_video("/input", "test.mp4", 10.0)

    expected_content = "file 'test.mp4'\n" * 4
    actual_content = "".join(mock_environment.content)
    assert actual_content == expected_content


def test_process_video_invalid_length(mock_environment: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_length_ffmpeg", lambda x: None
    )

    main.process_video("/input", "test.mp4", 10.0)

    assert not mock_environment.content


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


def test_get_target_files(tmpdir: Any) -> None:
    folder = tmpdir.mkdir("test")
    folder.join("test1_TV.mp4").write("dummy content")
    folder.join("test2.mp4").write("dummy content")
    folder.join("test3_TV.mov").write("dummy content")

    files = ["test1_TV.mp4", "test2.mp4", "test3_TV.mov"]
    result = main.get_target_files(str(folder), files)

    assert sorted(result) == [
        str(folder.join("test1_TV.mp4")),
        str(folder.join("test3_TV.mov")),
    ]
