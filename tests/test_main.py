import builtins
import os
import subprocess
import sys
import time
from concurrent.futures import Future
from typing import Any, Generator, List, Optional, Tuple

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_dir = os.path.dirname(os.path.abspath(__file__))

from video_grid_merge import __main__ as main


def test_reset_input_buffer_success(mocker: Any) -> None:
    mock_fcntl = mocker.patch("fcntl.fcntl")
    mock_select = mocker.patch("select.select")
    mock_stdin = mocker.patch("sys.stdin")

    # Simulate input being available once, then no more input
    mock_select.side_effect = [([mock_stdin], [], []), ([], [], [])]
    mock_stdin.read.return_value = "test input"

    main.reset_input_buffer()

    assert (
        mock_fcntl.call_count == 3
    )  # fcntl is called 3 times in the actual implementation
    assert mock_select.call_count == 2
    mock_stdin.read.assert_called_once_with(1024)


def test_reset_input_buffer_no_input(mocker: Any) -> None:
    mock_fcntl = mocker.patch("fcntl.fcntl")
    mock_select = mocker.patch("select.select")
    mock_stdin = mocker.patch("sys.stdin")

    # Simulate no input being available
    mock_select.return_value = ([], [], [])

    main.reset_input_buffer()

    assert (
        mock_fcntl.call_count == 3
    )  # fcntl is called 3 times in the actual implementation
    mock_select.assert_called_once()
    mock_stdin.read.assert_not_called()


def test_reset_input_buffer_exception(mocker: Any) -> None:
    mock_fcntl = mocker.patch("fcntl.fcntl")
    mock_fcntl.side_effect = Exception("Test exception")
    mock_sleep = mocker.patch("time.sleep")

    main.reset_input_buffer()

    mock_fcntl.assert_called_once()
    mock_sleep.assert_called_once_with(0.1)


def test_safe_input(mocker: Any) -> None:
    mock_reset = mocker.patch("video_grid_merge.__main__.reset_input_buffer")
    mock_input = mocker.patch("builtins.input", return_value="test input")

    result = main.safe_input("Enter something: ")

    assert result == "test input"
    mock_reset.assert_called_once()
    mock_input.assert_called_once_with("Enter something: ")


def test_get_video_files(tmp_path: Any) -> None:
    (tmp_path / "video1.mp4").touch()
    (tmp_path / "video2.mov").touch()
    (tmp_path / "document.txt").touch()

    video_files = main.get_video_files(str(tmp_path))
    assert sorted(video_files) == ["video1.mp4", "video2.mov"]


def test_get_video_length_ffmpeg() -> None:
    file_path = os.path.join(base_dir, "test_data/input/get_videos/sample1.mov")
    expected_duration = 62.43
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration == expected_duration

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


@pytest.fixture
def mock_environment(monkeypatch: Any) -> Any:
    def mock_join(*args: str) -> str:
        return "/".join(args)

    def mock_link(src: str, dst: str) -> None:
        pass

    def mock_run(*args: Any, **kwargs: Any) -> None:
        pass

    class MockFile:
        def __init__(self) -> None:
            self.content: List[str] = []

        def write(self, text: str) -> None:
            self.content.append(text)

        def __enter__(self) -> "MockFile":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    mock_file = MockFile()

    monkeypatch.setattr(os.path, "join", mock_join)
    monkeypatch.setattr(os, "link", mock_link)
    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)

    return mock_file


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
        # max_lengthがNoneの場合はテストをスキップ
        pytest.skip("Skipping test when max_length is None")

    assert not mock_environment.content


@pytest.fixture
def mock_get_video_length(monkeypatch: Any) -> Any:
    def mock(*args: Any) -> float:
        return 10.0

    monkeypatch.setattr("video_grid_merge.__main__.get_video_length_ffmpeg", mock)
    return mock


@pytest.fixture
def mock_process_video(monkeypatch: Any) -> Any:
    def mock(*args: Any) -> None:
        pass

    monkeypatch.setattr("video_grid_merge.__main__.process_video", mock)
    return mock


@pytest.fixture
def mock_thread_pool(monkeypatch: Any) -> Any:
    class MockExecutor:
        def __init__(self) -> None:
            self.submitted_tasks: List[Tuple[Any, Tuple[Any, ...]]] = []

        def submit(self, fn: Any, *args: Any) -> Future[None]:
            self.submitted_tasks.append((fn, args))
            future: Future[None] = Future()
            future.set_result(None)
            return future

        def __enter__(self) -> "MockExecutor":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

    executor = MockExecutor()
    monkeypatch.setattr(
        "video_grid_merge.__main__.ThreadPoolExecutor", lambda: executor
    )
    return executor


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


video_extension_list = [".mov", ".mp4"]


@pytest.fixture
def mock_safe_input(monkeypatch: Any) -> List[str]:
    inputs: List[str] = []

    def mock_input(prompt: str) -> str:
        return inputs.pop(0) if inputs else ""

    monkeypatch.setattr("video_grid_merge.__main__.safe_input", mock_input)
    return inputs


@pytest.fixture
def mock_os_path_exists(monkeypatch: Any) -> List[bool]:
    exists_results: List[bool] = []

    def mock_exists(path: str) -> bool:
        return exists_results.pop(0) if exists_results else False

    monkeypatch.setattr("os.path.exists", mock_exists)
    return exists_results


def test_default_filename(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.append("")
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"combined_video{video_extension_list[0]}")


def test_custom_filename_without_extension(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.append("my_video")
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"my_video{video_extension_list[0]}")


def test_custom_filename_with_valid_extension(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.append(f"my_video{video_extension_list[1]}")
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"my_video{video_extension_list[1]}")


def test_overwrite_existing_file(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.extend(["existing_video", "y"])
    mock_os_path_exists.append(True)
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"existing_video{video_extension_list[0]}")


def test_do_not_overwrite_existing_file(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.extend(["existing_video", "n", "new_video"])
    mock_os_path_exists.extend([True, False])
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"new_video{video_extension_list[0]}")


def test_multiple_attempts_with_existing_files(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.extend(["video1", "n", "video2", "n", "video3"])
    mock_os_path_exists.extend([True, True, False])
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"video3{video_extension_list[0]}")


def test_empty_input_after_rejecting_overwrite(
    mock_safe_input: List[str], mock_os_path_exists: List[bool]
) -> None:
    mock_safe_input.extend(["existing_video", "n", ""])
    mock_os_path_exists.extend([True, False])
    result = main.get_output_filename_from_user("/output")
    assert result == os.path.join("/output", f"combined_video{video_extension_list[0]}")


ffmpeg_loglevel = "error"


@pytest.fixture
def mock_subprocess_check_output(monkeypatch: Any) -> None:
    def mock(*args: Any, **kwargs: Any) -> bytes:
        if args[0][1] == "-v":
            return b"1920x1080\n"
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr("subprocess.check_output", mock)


def test_get_video_size_success(mock_subprocess_check_output: Any) -> None:
    result = main.get_video_size("test_video.mp4")
    assert result == (1920, 1080)


def test_get_video_size_failure(
    mock_subprocess_check_output: Any, monkeypatch: Any
) -> None:
    def mock_error(*args: Any, **kwargs: Any) -> None:
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr("subprocess.check_output", mock_error)

    result = main.get_video_size("non_existent_video.mp4")
    assert result is None


def test_get_video_size_cache(mock_subprocess_check_output: Any) -> None:
    result1 = main.get_video_size("test_video.mp4")
    assert result1 == (1920, 1080)

    result2 = main.get_video_size("test_video.mp4")
    assert result2 == (1920, 1080)

    assert main.get_video_size.cache_info().hits == 1
    assert main.get_video_size.cache_info().misses == 1


def test_get_video_size_different_files(mock_subprocess_check_output: Any) -> None:
    result1 = main.get_video_size("video1.mp4")
    assert result1 == (1920, 1080)

    result2 = main.get_video_size("video2.mp4")
    assert result2 == (1920, 1080)

    assert main.get_video_size.cache_info().misses == 2


def test_get_video_size_command_construction(
    mock_subprocess_check_output: Any, monkeypatch: Any
) -> None:
    called_commands: List[List[str]] = []

    def mock_check_output(cmd: List[str], *args: Any, **kwargs: Any) -> bytes:
        called_commands.append(cmd)
        return b"1920x1080\n"

    monkeypatch.setattr("subprocess.check_output", mock_check_output)

    main.get_video_size("test_video.mp4")

    expected_cmd = [
        "ffprobe",
        "-v",
        f"{ffmpeg_loglevel}",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=s=x:p=0",
        "test_video.mp4",
    ]
    assert called_commands[0] == expected_cmd


@pytest.fixture(autouse=True)
def clear_cache() -> Generator[None, None, None]:
    main.get_video_size.cache_clear()
    yield
    main.get_video_size.cache_clear()


@pytest.fixture
def mock_get_video_size(monkeypatch: Any) -> None:
    def mock(*args: Any, **kwargs: Any) -> Tuple[int, int]:
        return (1920, 1080)

    monkeypatch.setattr("video_grid_merge.__main__.get_video_size", mock)


def test_create_ffmpeg_command_empty_input() -> None:
    result = main.create_ffmpeg_command([], "output.mp4", True)
    assert result == ""


def test_create_ffmpeg_command_single_input(mock_get_video_size: Any) -> None:
    result = main.create_ffmpeg_command(["input1.mp4"], "output.mp4", True)
    expected = (
        f'ffmpeg -y -i input1.mp4 -filter_complex "[0:v]scale=1920:1080[v0]; [v0]hstack=inputs=1[row0]; '
        f'[row0]vstack=inputs=1[vstack]" -map "[vstack]" -map 0:a -c:v libx264 -preset ultrafast -c:a copy '
        f"-loglevel {ffmpeg_loglevel} -s 1920x1080 output.mp4"
    )
    assert result == expected


def test_create_ffmpeg_command_multiple_inputs(mock_get_video_size: Any) -> None:
    result = main.create_ffmpeg_command(
        ["input1.mp4", "input2.mp4", "input3.mp4", "input4.mp4"], "output.mp4", True
    )
    expected = (
        f"ffmpeg -y -i input1.mp4 -i input2.mp4 -i input3.mp4 -i input4.mp4 "
        f'-filter_complex "[0:v]scale=1920:1080[v0]; [1:v]scale=1920:1080[v1]; [2:v]scale=1920:1080[v2]; [3:v]scale=1920:1080[v3]; '
        f"[v0][v1]hstack=inputs=2[row0]; [v2][v3]hstack=inputs=2[row1]; "
        f'[row0][row1]vstack=inputs=2[vstack]" '
        f'-map "[vstack]" -map 0:a -map 1:a -map 2:a -map 3:a -c:v libx264 -preset ultrafast -c:a copy '
        f"-loglevel {ffmpeg_loglevel} -s 3840x2160 output.mp4"
    )
    assert result == expected


def test_create_ffmpeg_command_output_size_calculation(
    mock_get_video_size: Any,
) -> None:
    result = main.create_ffmpeg_command(
        ["input1.mp4", "input2.mp4", "input3.mp4", "input4.mp4"], "output.mp4", True
    )
    assert "-s 3840x2160" in result


@pytest.fixture
def mock_file_operations(monkeypatch: Any) -> None:
    def mock_rename_files_with_spaces(directory: str) -> None:
        pass

    def mock_get_video_files(directory: str) -> List[str]:
        return ["video1.mp4", "video2.mp4", "video3.mp4", "video4.mp4"]

    def mock_create_target_video(input_folder: str, video_files: List[str]) -> None:
        pass

    def mock_makedirs(output_folder: str, exist_ok: bool) -> None:
        pass

    def mock_custom_sorted(files: List[str]) -> List[str]:
        files.sort()
        return files

    def mock_get_target_files(input_folder: str, files: List[str]) -> List[str]:
        return ["file1_TV.mov", "file2_TV.mov"]

    def mock_get_output_filename_from_user(input_folder: str) -> str:
        return "/path/to/output_file.mov"

    def mock_create_ffmpeg_command(
        input_files: List[str], output_path: str, match_input_resolution_flag: bool
    ) -> str:
        return "ffmpeg_command"

    def mock_subprocess_run(ffmpeg_command: str, shell: bool) -> None:
        pass

    def mock_delete_files_in_folder(files: List[str], input_folder: str) -> None:
        pass

    def mock_exit(code: int) -> None:
        raise SystemExit(code)

    def mock_listdir(directory: str) -> List[str]:
        return ["file1_TV.mov", "file2_TV.mov"]

    monkeypatch.setattr(
        "video_grid_merge.__main__.rnf.rename_files_with_spaces",
        mock_rename_files_with_spaces,
    )
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_video_files", mock_get_video_files
    )
    monkeypatch.setattr(
        "video_grid_merge.__main__.create_target_video", mock_create_target_video
    )
    monkeypatch.setattr(os, "makedirs", mock_makedirs)
    monkeypatch.setattr(builtins, "sorted", mock_custom_sorted)
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_target_files", mock_get_target_files
    )
    monkeypatch.setattr(
        "video_grid_merge.__main__.get_output_filename_from_user",
        mock_get_output_filename_from_user,
    )
    monkeypatch.setattr(
        "video_grid_merge.__main__.create_ffmpeg_command", mock_create_ffmpeg_command
    )
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    monkeypatch.setattr(
        "video_grid_merge.__main__.dlf.delete_files_in_folder",
        mock_delete_files_in_folder,
    )
    monkeypatch.setattr(sys, "exit", mock_exit)
    monkeypatch.setattr(os, "listdir", mock_listdir)


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
