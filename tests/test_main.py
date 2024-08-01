import builtins
import io
import math
import os
import subprocess
import sys
import termios
import time
from concurrent.futures import Future
from typing import Any, Callable, Generator, List, Optional, Tuple

import pytest
from _pytest.fixtures import FixtureRequest
from pytest import MonkeyPatch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_dir = os.path.dirname(os.path.abspath(__file__))

from video_grid_merge import __main__ as main

sys.stdin = io.StringIO()


@pytest.fixture
def mock_terminal(monkeypatch: MonkeyPatch) -> Tuple[Any, Any, Any]:
    class MockObject:
        def __init__(self) -> None:
            self.call_args: Any = None
            self.return_value: Any = None

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            self.call_args = (args, kwargs)
            return self.return_value

        def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None:
            assert self.call_args == (args, kwargs)

    mock_tcsetattr = MockObject()
    mock_tcgetattr = MockObject()
    mock_stdin = MockObject()

    monkeypatch.setattr(termios, "tcsetattr", mock_tcsetattr)
    monkeypatch.setattr(termios, "tcgetattr", mock_tcgetattr)
    monkeypatch.setattr(sys, "stdin", mock_stdin)

    mock_tcgetattr.return_value = MockObject()

    return mock_tcsetattr, mock_tcgetattr, mock_stdin


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


def test_reset_terminal(
    mock_terminal: Tuple[Any, Any, Any], monkeypatch: MonkeyPatch
) -> None:
    mock_tcsetattr, _, _ = mock_terminal

    # グローバル変数 original_terminal_settings をモック
    mock_original_settings = object()
    monkeypatch.setattr(main, "original_terminal_settings", mock_original_settings)

    main.reset_terminal()

    # termios.tcsetattr が正しく呼び出されたことを確認
    mock_tcsetattr.assert_called_once_with(
        sys.stdin, termios.TCSADRAIN, mock_original_settings
    )


def test_atexit_register(monkeypatch: MonkeyPatch) -> None:
    called_functions: List[Callable[[], None]] = []

    def mock_register(func: Callable[[], None]) -> None:
        called_functions.append(func)

    monkeypatch.setattr("atexit.register", mock_register)

    # Reimport the module and trigger a call to atexit.register
    import importlib

    importlib.reload(main)

    # Confirm that atexit.register was called with reset_terminal
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


@pytest.mark.parametrize("version", ["v1", "v2", "invalid"])
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


def test_original_terminal_settings_error(monkeypatch: MonkeyPatch) -> None:
    def mock_tcgetattr(*args: Any) -> None:
        raise termios.error("Mock termios error")

    monkeypatch.setattr(termios, "tcgetattr", mock_tcgetattr)

    # Reimport the module to trigger the exception in the global scope
    import importlib

    importlib.reload(main)

    assert main.original_terminal_settings is None


def test_reset_terminal_with_none_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "original_terminal_settings", None)
    main.reset_terminal()  # This should not raise an exception


def test_safe_input_with_none_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(main, "original_terminal_settings", None)
    monkeypatch.setattr(builtins, "input", lambda _: "test input")
    result = main.safe_input("Prompt: ")
    assert result == "test input"


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


# Constants
TEST_DATA_DIR = os.path.join(base_dir, "test_data", "input", "get_videos")
SAMPLE_VIDEOS = ["sample1.mov", "sample2.mov", "sample3.mov", "sample4.mov"]
EXPECTED_WIDTH = 640
EXPECTED_HEIGHT = 360


@pytest.fixture
def sample_video_paths() -> List[str]:
    return [os.path.join(TEST_DATA_DIR, video) for video in SAMPLE_VIDEOS]


@pytest.mark.parametrize("match_input_resolution_flag", [True, False])
def test_create_ffmpeg_command(
    sample_video_paths: List[str], match_input_resolution_flag: bool
) -> None:
    output_path = "output.mp4"

    # Verify that all sample videos exist
    for path in sample_video_paths:
        assert os.path.exists(path), f"Sample video {path} does not exist"

    # Verify video dimensions
    for path in sample_video_paths:
        size = main.get_video_size(path)
        assert size is not None, f"Failed to get video size for {path}"
        width, height = size
        assert (
            width == EXPECTED_WIDTH and height == EXPECTED_HEIGHT
        ), f"Unexpected video dimensions for {path}: {width}x{height}"

    command = main.create_ffmpeg_command(
        sample_video_paths, output_path, match_input_resolution_flag
    )

    # Check if the command is not empty
    assert command != ""

    # Check if all input files are in the command
    for input_file in sample_video_paths:
        assert input_file in command

    # Check if output path is in the command
    assert output_path in command

    # Check the output resolution
    N = len(sample_video_paths)
    sqrt_N = int(math.sqrt(N))
    if match_input_resolution_flag:
        expected_resolution = f"{EXPECTED_WIDTH * sqrt_N}x{EXPECTED_HEIGHT * sqrt_N}"
    else:
        expected_resolution = f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
    assert f"-s {expected_resolution}" in command

    # Check if filter complex is present
    assert "-filter_complex" in command

    # Check if the number of scale operations matches the number of input files
    scale_count = command.count(f"scale={EXPECTED_WIDTH}:{EXPECTED_HEIGHT}")
    assert scale_count == N

    # Check if the number of hstack operations is correct
    hstack_count = command.count("hstack=inputs=")
    assert hstack_count == sqrt_N

    # Check if vstack operation is present
    assert "vstack=inputs=" in command


def test_create_ffmpeg_command_empty_input() -> None:
    command = main.create_ffmpeg_command([], "output.mp4", True)
    assert command == ""


def test_create_ffmpeg_command_invalid_video_size(tmp_path: Any) -> None:
    # Create an empty file that ffprobe can't read
    invalid_file = tmp_path / "invalid.mp4"
    invalid_file.touch()
    command = main.create_ffmpeg_command([str(invalid_file)], "output.mp4", True)
    assert command == ""


@pytest.mark.parametrize("match_input_resolution_flag", [True, False])
def test_create_ffmpeg_command_v2(
    sample_video_paths: List[str], match_input_resolution_flag: bool
) -> None:
    output_path = "output.mp4"

    # Verify that all sample videos exist
    for path in sample_video_paths:
        assert os.path.exists(path), f"Sample video {path} does not exist"

    # Verify video dimensions
    for path in sample_video_paths:
        size = main.get_video_size(path)
        assert size is not None, f"Failed to get video size for {path}"
        width, height = size
        assert (
            width == EXPECTED_WIDTH and height == EXPECTED_HEIGHT
        ), f"Unexpected video dimensions for {path}: {width}x{height}"

    command = main.create_ffmpeg_command_v2(
        sample_video_paths, output_path, match_input_resolution_flag
    )

    # Check if the command is not empty
    assert command != ""

    # Check if all input files are in the command
    for input_file in sample_video_paths:
        assert input_file in command

    # Check if output path is in the command
    assert output_path in command

    # Check the output resolution
    N = len(sample_video_paths)
    sqrt_N = int(math.sqrt(N))
    if match_input_resolution_flag:
        expected_resolution = f"{EXPECTED_WIDTH * sqrt_N}x{EXPECTED_HEIGHT * sqrt_N}"
    else:
        expected_resolution = f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
    assert f"-s {expected_resolution}" in command

    # Check if filter complex is present
    assert "-filter_complex" in command

    # Check if the number of scale operations matches the number of input files
    scale_count = command.count(f"scale={EXPECTED_WIDTH}:{EXPECTED_HEIGHT}")
    assert scale_count == N

    # Check if the number of hstack operations is correct
    hstack_count = command.count("hstack=inputs=")
    assert hstack_count == sqrt_N

    # Check if vstack operation is present
    assert "vstack=inputs=" in command


def test_create_ffmpeg_command_v2_empty_input() -> None:
    command = main.create_ffmpeg_command_v2([], "output.mp4", True)
    assert command == ""


def test_create_ffmpeg_command_v2_invalid_video_size(tmp_path: Any) -> None:
    # Create an empty file that ffprobe can't read
    invalid_file = tmp_path / "invalid.mp4"
    invalid_file.touch()
    command = main.create_ffmpeg_command_v2([str(invalid_file)], "output.mp4", True)
    assert command == ""


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_main_with_different_versions(
    version: str,
    mock_file_operations: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "ffmpeg_cmd_version", version)
    main.main()
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out
    assert f"Executing command: ffmpeg_command_{version}" in captured.out


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


@pytest.fixture(params=["v1", "v2"])
def mock_file_operations(
    request: FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> FixtureRequest:
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
        return "ffmpeg_command_v1"

    def mock_create_ffmpeg_command_v2(
        input_files: List[str], output_path: str, match_input_resolution_flag: bool
    ) -> str:
        return "ffmpeg_command_v2"

    def mock_subprocess_run(ffmpeg_command: str, shell: bool) -> None:
        print(f"Executing command: {ffmpeg_command}")

    def mock_delete_files_in_folder(files: List[str], input_folder: str) -> None:
        pass

    def mock_exit(code: int) -> None:
        raise SystemExit(code)

    def mock_listdir(directory: str) -> List[str]:
        return ["file1_TV.mov", "file2_TV.mov"]

    monkeypatch.setattr(main, "ffmpeg_cmd_version", request.param)

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
    monkeypatch.setattr(
        "video_grid_merge.__main__.create_ffmpeg_command_v2",
        mock_create_ffmpeg_command_v2,
    )
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    monkeypatch.setattr(
        "video_grid_merge.__main__.dlf.delete_files_in_folder",
        mock_delete_files_in_folder,
    )
    monkeypatch.setattr(sys, "exit", mock_exit)
    monkeypatch.setattr(os, "listdir", mock_listdir)

    # Set ffmpeg_cmd_version based on the current parameter
    monkeypatch.setattr("video_grid_merge.__main__.ffmpeg_cmd_version", request.param)

    return request


def test_main(
    mock_file_operations: FixtureRequest, capsys: pytest.CaptureFixture[str]
) -> None:
    from video_grid_merge.__main__ import main

    main()
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out

    # ffmpeg_cmd_version に基づいた追加のアサーション
    if mock_file_operations.param == "v1":
        assert "Executing command: ffmpeg_command_v1" in captured.out
    else:
        assert "Executing command: ffmpeg_command_v2" in captured.out


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
