import builtins
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator, List, Tuple

import pytest

from video_grid_merge import __main__ as main
from video_grid_merge import delete_files as dlf
from video_grid_merge import rename_files as rnf

CONDITION = True
base_dir = os.path.dirname(os.path.abspath(__file__))


# TestCase1
@pytest.mark.parametrize(
    ("num", "expect"),
    [
        (4, True),
        (9, True),
        (25, True),
        (2, False),
        # The following cases are excluded from the test because they will result in errors due to type inconsistencies caused by mypy.
        # num=0
        # num<0
        # num: float # Non-int type
    ],
)
def test_is_integer_square_root_greater_than_four(num: int, expect: bool) -> None:
    assert main.is_integer_square_root_greater_than_four(num) == expect


# TestCase2
file_path = os.path.join(base_dir, "test_data/input/get_videos")


@pytest.mark.parametrize(
    ("filename", "expect_width", "expect_height"),
    [
        # ("tests/test_data/input/get_videos/sample1.mov", 640, 360),
        # ("tests/test_data/input/get_videos/sample2.mov", 640, 360),
        (f"{file_path}/sample1.mov", 640, 360),
        (f"{file_path}/sample2.mov", 640, 360),
        # The following cases are excluded from the test because they will result in errors due to type inconsistencies caused by mypy.
        # num=0
        # num<0
        # num: float # Non-int type
    ],
)
def test_get_video_size_ok(
    filename: str, expect_width: int, expect_height: int
) -> None:
    # width, height = main.get_video_size(filename)
    # assert width == width
    # assert height == height
    print(f"filename: {filename}\n")
    assert main.get_video_size(filename) == (expect_width, expect_height)


# TestCase3
file_path = os.path.join(base_dir, "test_data/input")


@pytest.mark.parametrize(
    ("filename", "no_data_rtn"),
    [
        # Error executing ffprobe command
        (
            # "tests/test_data/input/get_video_size_none_data/test.log",
            f"{file_path}/get_video_size_none_data/test.log",
            # "Error executing ffprobe command: tests/test_data/get_video_size_none_data/test.log: Invalid data found when processing input\n",
            f"Error executing ffprobe command: {base_dir}/test_data/get_video_size_none_data/test.log: Invalid data found when processing input\n",
        ),
        ("", "Error executing ffprobe command: : No such file or directory\n"),
        (
            # "tests/test_data/input/get_video_size_none_data/menuettm.mp3",
            f"{file_path}/get_video_size_none_data/menuettm.mp3",
            # "Failed to extract video size from tests/test_data/get_video_size_none_data/menuettm.mp3.",
            f"Failed to extract video size from {base_dir}/test_data/get_video_size_none_data/menuettm.mp3.",
        ),
    ],
)
def test_get_video_size_none(filename: str, no_data_rtn: str) -> None:
    # with pytest.raises((subprocess.CalledProcessError, Exception)) as e:
    with pytest.raises((subprocess.CalledProcessError, Exception)):
        assert main.get_video_size(filename) is not None
        # assert str(e.value) == no_data_rtn


def test_get_file_extension() -> None:
    assert main.get_file_extension("sample.txt") == ".txt"
    assert main.get_file_extension("sample1_TV.mov") == ".mov"
    assert main.get_file_extension("sample1_TV.mp4") == ".mp4"


def test_get_target_files_c() -> None:
    files = ["sample1_TV.mov", "test.log", "sample2_TV.mov", "menuettm.mp3", ""]
    # input_folder = "tests/test_data/input"
    input_folder = os.path.join(base_dir, "test_data/input")
    expected_output = [
        os.path.join(input_folder, "sample1_TV.mov"),
        os.path.join(input_folder, "sample2_TV.mov"),
    ]
    actual_output = main.get_target_files(input_folder, files)
    for path in expected_output:
        assert path in actual_output


@pytest.fixture
def test_data_folder() -> Generator[str, None, None]:
    # 一時的なテストデータフォルダを作成する
    folder = tempfile.mkdtemp()
    # 必要なファイルを作成する
    files = ["sample1_TV.mov", "test.log", "sample2_TV.mov", "menuettm.mp3", ""]
    for file in files:
        file_path = os.path.join(folder, file)
        if file:
            with open(file_path, "w") as f:
                f.write("dummy data")
    yield folder
    # テスト終了後に一時的なテストデータフォルダを削除する
    shutil.rmtree(folder)


def test_get_target_files(test_data_folder: str) -> None:
    input_folder = test_data_folder
    files = ["sample1_TV.mov", "test.log", "sample2_TV.mov", "menuettm.mp3", ""]
    expected_output = [
        os.path.join(input_folder, file)
        for file in ["sample1_TV.mov", "sample2_TV.mov"]
    ]
    actual_output = main.get_target_files(input_folder, files)
    for path in expected_output:
        assert path in actual_output


def test_get_video_length_ffmpeg() -> None:
    # Test case 1: Valid duration line
    # file_path = "tests/test_data/input/get_videos/sample1.mov"
    file_path = os.path.join(base_dir, "test_data/input/get_videos/sample1.mov")
    expected_duration = 62.43
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration == expected_duration

    # Test case 2: Invalid duration line
    file_path = "invalid_video.mp4"
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration is None


def test_get_video_files() -> None:
    # input_folder = "tests/test_data/input/get_videos"
    input_folder = os.path.join(base_dir, "test_data/input/get_videos")
    video_extension_list = [".mov", ".mp4"]
    expected_files = ["sample1.mov", "sample2.mov", "sample3.mov", "sample4.mov"]

    files = main.get_video_files(input_folder, video_extension_list)

    assert len(files) == len(expected_files)
    for file in expected_files:
        assert file in files

    # Test with non-existent folder
    # non_existent_folder = "tests/test_data/input/no_data_folder"
    non_existent_folder = os.path.join(base_dir, "test_data/input/no_data_folder")
    if os.path.exists(non_existent_folder):
        files = main.get_video_files(non_existent_folder, video_extension_list)
        assert len(files) == 0
    else:
        pytest.skip("Non-existent folder: {}".format(non_existent_folder))

    # Test with empty extension list
    empty_extension_list: List[str] = []
    files = main.get_video_files(input_folder, empty_extension_list)
    assert len(files) == 0


@pytest.fixture(scope="module")
def test_directory(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[str, None, None]:
    test_dir = tmp_path_factory.mktemp("test_directory")

    file_names = ["file 1.mp4", "file 2.mov", "file 3.mp4", "file 4.mov"]
    for file_name in file_names:
        file_path = test_dir / file_name
        with open(file_path, "w") as file:
            file.write("Test content")

    yield str(test_dir)

    shutil.rmtree(test_dir)


def test_rename_files_with_spaces(test_directory: str) -> None:
    # print(f"call test_rename_files_with_spaces({test_directory})\n")
    # テスト用ディレクトリ内のファイルをリネーム
    rnf.rename_files_with_spaces(test_directory)

    # リネーム後のファイルが存在するか確認(存在すればOK)
    renamed_files = ["file_1.mp4", "file_2.mov", "file_3.mp4", "file_4.mov"]
    for file_name in renamed_files:
        file_path = os.path.join(test_directory, file_name)
        assert os.path.exists(file_path)

    # 元のファイルが存在しないことを確認(存在しなければOK)
    original_files = ["file 1.mp4", "file 2.mov", "file　3.mp4", "file　4.mov"]
    for file_name in original_files:
        file_path = os.path.join(test_directory, file_name)
        assert not os.path.exists(file_path)


@pytest.fixture(scope="module")
def test_data(
    tmpdir_factory: pytest.TempdirFactory,
) -> Generator[Tuple[str, List[str]], None, None]:
    input_folder = tmpdir_factory.mktemp("input")
    video_files = ["sample3.mov", "sample1.mov", "sample4.mov", "sample2.mov"]

    # Copy video files to the test input folder
    for file in video_files:
        shutil.copyfile(
            os.path.join("tests", "test_data", "input", "get_videos", file),
            os.path.join(str(input_folder), file),
        )

    yield str(input_folder), video_files

    # Clean up the test input folder
    shutil.rmtree(str(input_folder))


def test_create_target_video(test_data: Tuple[str, List[str]]) -> None:
    input_folder, video_files = test_data

    # Run the function under test
    main.create_target_video(input_folder, video_files)

    # Check the existence of expected output files
    expected_output_files = [
        "sample1_TV.mov",
        "sample2_TV.mov",
        "sample3_TV.mov",
        "sample4_TV.mov",
    ]
    for output_file in expected_output_files:
        assert os.path.exists(os.path.join(input_folder, output_file))


temporarily_data_list: List[str] = ["_TV", "_LP", ".txt"]


def test_delete_files_in_folder(tmpdir: str) -> None:
    folder_path = Path(tmpdir) / "test_folder"
    folder_path.mkdir()

    file1 = folder_path / "test1.mov"
    file1.write_text("Test File 1")
    file2 = folder_path / "test1_TV.mov"
    file2.write_text("Test File 2")
    file3 = folder_path / "test1_LP.mov"
    file3.write_text("Test File 3")
    file4 = folder_path / "test1_list.txt"
    file4.write_text("Test File 4")
    file5 = folder_path / "test1,tmp"
    file5.write_text("Test File 5")

    dlf.delete_files_in_folder(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert not file2.exists()
    assert not file3.exists()
    assert not file4.exists()
    assert file5.exists()

    # 追加修正: 削除されなかったファイルも存在することを確認
    assert os.path.exists(str(file1))
    assert os.path.exists(str(file5))


def test_delete_files_with_confirmation_y(tmpdir: str, monkeypatch: Any) -> None:
    folder = Path(tmpdir)  # フォルダパスをPathオブジェクトに変換
    folder.mkdir(parents=True, exist_ok=True)

    file1 = folder.joinpath("test1.mov")
    file1.write_text("Test File 1")
    file2 = folder.joinpath("test1_TV.mov")
    file2.write_text("Test File 2")
    file3 = folder.joinpath("test1_LP.mov")
    file3.write_text("Test File 3")
    file4 = folder.joinpath("test1_list.txt")
    file4.write_text("Test File 4")
    file5 = folder.joinpath("test1.tmp")
    file5.write_text("Test File 5")

    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換

    temporarily_data_list: List[str] = [
        "_TV",
        "_LP",
        ".txt",
    ]  # temporarily_data_list の適切な型を定義する

    # ユーザー入力を"y"としてモックする
    monkeypatch.setattr("builtins.input", lambda _: "y")

    dlf.delete_files_with_confirmation(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert not file2.exists()
    assert not file3.exists()
    assert not file4.exists()
    assert file5.exists()


def test_delete_files_with_confirmation_N(tmpdir: str, monkeypatch: Any) -> None:
    folder = Path(tmpdir)  # フォルダパスをPathオブジェクトに変換
    folder.mkdir(parents=True, exist_ok=True)

    file1 = folder.joinpath("test1.mov")
    file1.write_text("Test File 1")
    file2 = folder.joinpath("test1_TV.mov")
    file2.write_text("Test File 2")
    file3 = folder.joinpath("test1_LP.mov")
    file3.write_text("Test File 3")
    file4 = folder.joinpath("test1_list.txt")
    file4.write_text("Test File 4")
    file5 = folder.joinpath("test1,tmp")
    file5.write_text("Test File 5")

    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換

    temporarily_data_list: List[str] = []  # temporarily_data_list の適切な型を定義する

    # ユーザー入力を"N"としてモックする
    monkeypatch.setattr("builtins.input", lambda _: "N")

    dlf.delete_files_with_confirmation(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert file2.exists()
    assert file3.exists()
    assert file4.exists()
    assert file5.exists()


# テスト用の一時的な出力フォルダを作成
@pytest.fixture
def output_folder() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_get_output_filename_from_user_with_input_files(
    output_folder: str, monkeypatch: Any
) -> None:
    video_extension_list = [".mov", ".mp4"]
    input_files = ["file1_TV.mov", "file2_TV.mp4"]

    # ユーザー入力をモック
    monkeypatch.setattr("builtins.input", lambda _: "output_file.mov")

    output_path = main.get_output_filename_from_user(
        video_extension_list, input_files, output_folder
    )

    expected_output_path = os.path.join(output_folder, "output_file.mov")
    assert output_path == expected_output_path


def test_get_output_filename_from_user_without_input_files(
    output_folder: str, monkeypatch: Any
) -> None:
    video_extension_list = [".mov", ".mp4"]
    input_files: List[str] = []

    # ユーザー入力をモック
    monkeypatch.setattr("builtins.input", lambda _: "")

    output_path = main.get_output_filename_from_user(
        video_extension_list, input_files, output_folder
    )

    expected_output_path = os.path.join(output_folder, "combined_video.mov")
    assert output_path == expected_output_path


def test_get_output_filename_from_user_with_invalid_extension(
    output_folder: str, monkeypatch: Any, capsys: Any
) -> None:
    video_extension_list = [".mov", ".mp4"]
    input_files = ["file1_TV.mov", "file2_TV.mp4"]

    # ユーザー入力をモック
    user_inputs = ["output_file.invalid", "output_file.mov"]
    monkeypatch.setattr("builtins.input", lambda _: user_inputs.pop(0))

    output_path = main.get_output_filename_from_user(
        video_extension_list, input_files, output_folder
    )

    expected_output_path = os.path.join(output_folder, "output_file.mov")
    assert output_path == expected_output_path

    # エラーメッセージが表示されることを確認
    captured = capsys.readouterr()
    assert "Invalid file extension" in captured.out


def test_create_ffmpeg_command_match_input_resolution_flag_true() -> None:
    match_input_resolution_flag = True
    test_folder = os.path.join(base_dir, "test_data/input/ffmpeg_command_test")
    input_files = [
        # "tests/test_data/input/ffmpeg_command_test/sample1_TV.mov",
        # "tests/test_data/input/ffmpeg_command_test/sample2_TV.mov",
        # "tests/test_data/input/ffmpeg_command_test/sample3_TV.mov",
        # "tests/test_data/input/ffmpeg_command_test/sample4_TV.mov",
        f"{test_folder}/sample1_TV.mov",
        f"{test_folder}/sample2_TV.mov",
        f"{test_folder}/sample3_TV.mov",
        f"{test_folder}/sample4_TV.mov",
    ]
    # output_path = "tests/test_data/output/sample1_out.mov"
    output_path = os.path.join(base_dir, "test_data/output/sample1_out.mov")

    expected_ffmpeg_command = (
        "ffmpeg "
        # "-i tests/test_data/input/ffmpeg_command_test/sample1_TV.mov "
        # "-i tests/test_data/input/ffmpeg_command_test/sample2_TV.mov "
        # "-i tests/test_data/input/ffmpeg_command_test/sample3_TV.mov "
        # "-i tests/test_data/input/ffmpeg_command_test/sample4_TV.mov "
        f"-i {test_folder}/sample1_TV.mov "
        f"-i {test_folder}/sample2_TV.mov "
        f"-i {test_folder}/sample3_TV.mov "
        f"-i {test_folder}/sample4_TV.mov "
        "-filter_complex "
        '"[0:v]scale=640:360[v0]; '
        "[1:v]scale=640:360[v1]; "
        "[2:v]scale=640:360[v2]; "
        "[3:v]scale=640:360[v3]; "
        "[v0][v1]hstack=inputs=2[row1]; "
        "[v2][v3]hstack=inputs=2[row2]; "
        '[row1][row2]vstack=inputs=2[vstack]" '
        '-map "[vstack]" '
        "-map 0:a -map 1:a -map 2:a -map 3:a "
        "-c:v libx264 -preset ultrafast "
        "-c:a copy "
        "-loglevel error "
        "-s 1280x720 "
        # "tests/test_data/output/sample1_out.mov"
        f"{base_dir}/test_data/output/sample1_out.mov"
    )

    ffmpeg_command = main.create_ffmpeg_command(
        input_files, output_path, match_input_resolution_flag
    )

    assert ffmpeg_command == expected_ffmpeg_command


def test_create_ffmpeg_command_match_input_resolution_flag_false() -> None:
    match_input_resolution_flag = False
    test_folder = os.path.join(base_dir, "test_data/input/ffmpeg_command_test")
    input_files = [
        # "tests/test_data/input/ffmpeg_command_test/sample1_TV.mov",
        # "tests/test_data/input/ffmpeg_command_test/sample2_TV.mov",
        # "tests/test_data/input/ffmpeg_command_test/sample3_TV.mov",
        # "tests/test_data/input/ffmpeg_command_test/sample4_TV.mov",
        f"{test_folder}/sample1_TV.mov",
        f"{test_folder}/sample2_TV.mov",
        f"{test_folder}/sample3_TV.mov",
        f"{test_folder}/sample4_TV.mov",
    ]
    # output_path = "tests/test_data/output/sample1_out.mov"
    output_path = os.path.join(base_dir, "test_data/output/sample1_out.mov")

    expected_ffmpeg_command = (
        "ffmpeg "
        # "-i tests/test_data/input/ffmpeg_command_test/sample1_TV.mov "
        # "-i tests/test_data/input/ffmpeg_command_test/sample2_TV.mov "
        # "-i tests/test_data/input/ffmpeg_command_test/sample3_TV.mov "
        # "-i tests/test_data/input/ffmpeg_command_test/sample4_TV.mov "
        f"-i {test_folder}/sample1_TV.mov "
        f"-i {test_folder}/sample2_TV.mov "
        f"-i {test_folder}/sample3_TV.mov "
        f"-i {test_folder}/sample4_TV.mov "
        "-filter_complex "
        '"[0:v]scale=640:480[v0]; '
        "[1:v]scale=640:480[v1]; "
        "[2:v]scale=640:480[v2]; "
        "[3:v]scale=640:480[v3]; "
        "[v0][v1]hstack=inputs=2[row1]; "
        "[v2][v3]hstack=inputs=2[row2]; "
        '[row1][row2]vstack=inputs=2[vstack]" '
        '-map "[vstack]" '
        "-map 0:a -map 1:a -map 2:a -map 3:a "
        "-c:v libx264 -preset ultrafast "
        "-c:a copy "
        "-loglevel error "
        "-s 1280x960 "
        # "tests/test_data/output/sample1_out.mov"
        f"{base_dir}/test_data/output/sample1_out.mov"
    )

    ffmpeg_command = main.create_ffmpeg_command(
        input_files, output_path, match_input_resolution_flag
    )

    assert ffmpeg_command == expected_ffmpeg_command


"""
@pytest.fixture
def mock_input(monkeypatch):
   def mock_input_func(prompt):
       return "output_file.mov"

   monkeypatch.setattr(builtins, "input", mock_input_func)
"""


@pytest.fixture
def mock_file_operations(monkeypatch: Any) -> None:
    def mock_rename_files_with_spaces(directory: str) -> None:
        pass

    def mock_get_video_files(
        directory: str, video_extension_list: List[str]
    ) -> List[str]:
        return ["video1.mp4", "video2.mp4"]

    def mock_is_integer_square_root_greater_than_four(value: Any) -> bool:
        return True

    def mock_create_target_video(input_folder: str, video_files: List[str]) -> None:
        pass

    def mock_makedirs(output_folder: str, exist_ok: bool) -> None:
        pass

    def mock_custom_sorted(files: List[str]) -> List[str]:
        files.sort()
        return files

    def mock_get_target_files(input_folder: List[str], files: List[str]) -> List[str]:
        return ["file1_TV.mov", "file2_TV.mov"]

    def mock_get_output_filename_from_user(
        video_extension_list: List[str], input_files: List[str], output_folder: str
    ) -> str:
        return "/path/to/output_file.mov"

    def mock_create_ffmpeg_command(
        input_files: List[str], output_path: str, match_input_resolution_flag: bool
    ) -> str:
        return "ffmpeg_command"

    def mock_subprocess_call(ffmpeg_command: str, shell: str) -> None:
        pass

    def mock_delete_files_in_folder(files: str, input_folder: List[str]) -> None:
        pass

    def mock_exit(code: int) -> None:
        raise SystemExit(code)

    monkeypatch.setattr(rnf, "rename_files_with_spaces", mock_rename_files_with_spaces)
    monkeypatch.setattr(main, "get_video_files", mock_get_video_files)
    monkeypatch.setattr(
        main,
        "is_integer_square_root_greater_than_four",
        mock_is_integer_square_root_greater_than_four,
    )
    monkeypatch.setattr(main, "create_target_video", mock_create_target_video)
    monkeypatch.setattr(os, "makedirs", mock_makedirs)  # 517行目
    monkeypatch.setattr(builtins, "sorted", mock_custom_sorted)
    monkeypatch.setattr(main, "get_target_files", mock_get_target_files)
    monkeypatch.setattr(
        main, "get_output_filename_from_user", mock_get_output_filename_from_user
    )
    monkeypatch.setattr(main, "create_ffmpeg_command", mock_create_ffmpeg_command)
    monkeypatch.setattr(subprocess, "call", mock_subprocess_call)  # 524行目
    monkeypatch.setattr(dlf, "delete_files_in_folder", mock_delete_files_in_folder)
    monkeypatch.setattr(sys, "exit", mock_exit)


# def test_main_success_case(capsys, mock_input, mock_file_operations):
def test_main_success_case(capsys: Any, mock_file_operations: Any) -> None:
    main.main()

    # 出力の検証
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out
    assert "File Output Complete: /path/to/output_file.mov" in captured.out
    assert "Processing Time(s): " in captured.out


def test_main_error_case(
    capsys: Any, mock_file_operations: Any, monkeypatch: Any
) -> None:
    def mock_get_video_files(
        directory: str, video_extension_list: List[str]
    ) -> List[str]:
        return []

    def mock_is_integer_square_root_greater_than_four(value: Any) -> bool:
        return False

    monkeypatch.setattr(main, "get_video_files", mock_get_video_files)
    monkeypatch.setattr(
        main,
        "is_integer_square_root_greater_than_four",
        mock_is_integer_square_root_greater_than_four,
    )

    input_folder = "video_grid_merge/media/input"  # input_folderの値を指定

    with pytest.raises(SystemExit) as e:
        main.main(input_folder)

    assert (
        str(e.value)
        == f"Error: Please store more than 4 video files in the input folder.\ninput_folder: {input_folder}"
    )
