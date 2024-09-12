import builtins
import io
import os
import subprocess
import sys
import termios
from concurrent.futures import Future
from typing import Any, Generator, List, Tuple

import pytest
from _pytest.fixtures import FixtureRequest
from pytest import MonkeyPatch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_dir = os.path.dirname(os.path.abspath(__file__))

from video_grid_merge import __main__ as main

sys.stdin = io.StringIO()

FFMPEG_CMD_VERSIONS = ["v1", "v2"]


@pytest.fixture(params=FFMPEG_CMD_VERSIONS)
def ffmpeg_cmd_version(request: pytest.FixtureRequest) -> Any:
    return request.param


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


@pytest.fixture
def mock_subprocess_check_output(monkeypatch: Any) -> None:
    def mock(*args: Any, **kwargs: Any) -> bytes:
        # テスト用のコマンドに応じたモック出力
        cmd = args[0]
        if "-show_entries" in cmd and "stream=width,height" in cmd:
            if "test_valid.mp4" in cmd:
                return b"1920,1080"  # 正常な出力
            elif "test_malformed.mp4" in cmd:
                return b"1920,"  # 不完全な出力
            elif "test_empty.mp4" in cmd:
                return b""  # 空の出力
            elif "test_unexpected.mp4" in cmd:
                return b"unexpected,output"  # 予期しないフォーマット
        raise subprocess.CalledProcessError(1, cmd)  # エラーの場合

    monkeypatch.setattr(subprocess, "check_output", mock)


@pytest.fixture(autouse=True)
def clear_cache() -> Generator[None, None, None]:
    main.get_video_size.cache_clear()
    yield
    main.get_video_size.cache_clear()


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


@pytest.fixture(params=FFMPEG_CMD_VERSIONS)
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

    def mock_create_ffmpeg_command_v1(
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
        "video_grid_merge.__main__.create_ffmpeg_command_v1",
        mock_create_ffmpeg_command_v1,
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
