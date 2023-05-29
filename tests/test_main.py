import builtins
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

import pytest

from video_grid_merge import __main__ as main
from video_grid_merge import delete_files as dlf
from video_grid_merge import rename_files as rnf

CONDITION = True


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
def test_is_integer_square_root_greater_than_four(num, expect):
    assert main.is_integer_square_root_greater_than_four(num) == expect


# TestCase2
@pytest.mark.parametrize(
    ("filename", "expect_width", "expect_height"),
    [
        ("./tests/test_data/input/get_videos/sample1.mov", 640, 360),
        ("./tests/test_data/input/get_videos/sample2.mov", 640, 360),
        # The following cases are excluded from the test because they will result in errors due to type inconsistencies caused by mypy.
        # num=0
        # num<0
        # num: float # Non-int type
    ],
)
def test_get_video_size_ok(filename, expect_width, expect_height):
    # width, height = main.get_video_size(filename)
    # assert width == width
    # assert height == height
    assert main.get_video_size(filename) == (expect_width, expect_height)


# TestCase3
@pytest.mark.parametrize(
    ("filename", "no_data_rtn"),
    [
        # Error executing ffprobe command
        (
            "./tests/test_data/input/get_video_size_none_data/test.log",
            "Error executing ffprobe command: ./tests/test_data/get_video_size_none_data/test.log: Invalid data found when processing input\n",
        ),
        ("", "Error executing ffprobe command: : No such file or directory\n"),
        (
            "./tests/test_data/input/get_video_size_none_data/menuettm.mp3",
            "Failed to extract video size from ./tests/test_data/get_video_size_none_data/menuettm.mp3.",
        ),
    ],
)
def test_get_video_size_none(filename, no_data_rtn):
    # with pytest.raises((subprocess.CalledProcessError, Exception)) as e:
    with pytest.raises((subprocess.CalledProcessError, Exception)):
        assert main.get_video_size(filename) is not None
        # assert str(e.value) == no_data_rtn


def test_get_file_extension():
    assert main.get_file_extension("sample.txt") == ".txt"
    assert main.get_file_extension("sample1_TV.mov") == ".mov"
    assert main.get_file_extension("sample1_TV.mp4") == ".mp4"


def test_get_target_files_c():
    files = ["sample1_TV.mov", "test.log", "sample2_TV.mov", "menuettm.mp3", ""]
    input_folder = "./tests/test_data/input"
    expected_output = [
        os.path.join(input_folder, "sample1_TV.mov"),
        os.path.join(input_folder, "sample2_TV.mov"),
    ]
    actual_output = main.get_target_files(input_folder, files)
    for path in expected_output:
        assert path in actual_output


@pytest.fixture
def test_data_folder():
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


def test_get_target_files(test_data_folder):
    input_folder = test_data_folder
    files = ["sample1_TV.mov", "test.log", "sample2_TV.mov", "menuettm.mp3", ""]
    expected_output = [
        os.path.join(input_folder, "sample1_TV.mov"),
        os.path.join(input_folder, "sample2_TV.mov"),
    ]
    actual_output = main.get_target_files(input_folder, files)
    for path in expected_output:
        assert path in actual_output


def test_get_video_length_ffmpeg():
    # Test case 1: Valid duration line
    file_path = "./tests/test_data/input/get_videos/sample1.mov"
    expected_duration = 62.43
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration == expected_duration

    # Test case 2: Invalid duration line
    file_path = "invalid_video.mp4"
    duration = main.get_video_length_ffmpeg(file_path)
    assert duration is None


def test_get_video_files():
    input_folder = "./tests/test_data/input/get_videos"
    video_extension_list = [".mov", ".mp4"]
    expected_files = ["sample1.mov", "sample2.mov", "sample3.mov", "sample4.mov"]

    files = main.get_video_files(input_folder, video_extension_list)

    assert len(files) == len(expected_files)
    for file in expected_files:
        assert file in files

    # Test with non-existent folder
    non_existent_folder = "./tests/test_data/input/no_data_folder"
    files = main.get_video_files(non_existent_folder, video_extension_list)
    assert len(files) == 0

    # Test with empty extension list
    empty_extension_list: List[str] = []
    files = main.get_video_files(input_folder, empty_extension_list)
    assert len(files) == 0
    # print("\n\n")


@pytest.fixture(scope="module")
def test_directory(tmpdir_factory):
    # print(f"call test_directory({tmpdir_factory})\n")
    # テスト用のディレクトリを作成
    test_dir = tmpdir_factory.mktemp("test_directory")

    # テスト用のファイルを作成
    file_names = ["file 1.mp4", "file 2.mov", "file　3.mp4", "file　4.mov"]
    for file_name in file_names:
        file_path = os.path.join(test_dir, file_name)
        with open(file_path, "w") as file:
            file.write("Test content")

    # print(f'str(test_dir):{str(test_dir)}\n')
    # テスト用の一時ディレクトリを作成し、
    # test_rename_files_with_spaces実行前に
    # そのパスをtest_rename_files_with_spacesに渡す
    yield str(test_dir)

    # test_rename_files_with_spaces実行後にテスト用ディレクトリを削除
    # print("\n\ncall shutil.rmtree(test_dir)")
    shutil.rmtree(test_dir)


def test_rename_files_with_spaces(test_directory):
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
def test_data(tmpdir_factory):
    input_folder = tmpdir_factory.mktemp("input")
    video_files = ["sample3.mov", "sample1.mov", "sample4.mov", "sample2.mov"]

    # Copy video files to the test input folder
    for file in video_files:
        shutil.copyfile(
            os.path.join("tests", "test_data", "input", "get_videos", file),
            os.path.join(input_folder, file),
        )

    yield str(input_folder), video_files

    # Clean up the test input folder
    shutil.rmtree(input_folder)


def test_create_target_video(test_data):
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


temporarily_data_list = ["_TV", "_LP", ".txt"]


def test_delete_files_in_folder(tmpdir):
    folder = tmpdir.mkdir("test_folder")
    file1 = folder.join("test1.mov")
    file1.write("Test File 1")
    file2 = folder.join("test1_TV.mov")
    file2.write("Test File 2")
    file3 = folder.join("test1_LP.mov")
    file3.write("Test File 3")
    file4 = folder.join("test1_list.txt")
    file4.write("Test File 4")
    file5 = folder.join("test1,tmp")
    file5.write("Test File 5")
    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換
    dlf.delete_files_in_folder(temporarily_data_list, str(folder_path))
    assert file1.exists()
    assert not file2.exists()
    assert not file3.exists()
    assert not file4.exists()
    assert file5.exists()

    # 追加修正: 削除されなかったファイルも存在することを確認
    assert os.path.exists(str(file1))
    assert os.path.exists(str(file5))


def test_delete_files_with_confirmation_y(tmpdir, monkeypatch):
    folder = tmpdir.mkdir("test_folder")
    file1 = folder.join("test1.mov")
    file1.write("Test File 1")
    file2 = folder.join("test1_TV.mov")
    file2.write("Test File 2")
    file3 = folder.join("test1_LP.mov")
    file3.write("Test File 3")
    file4 = folder.join("test1_list.txt")
    file4.write("Test File 4")
    file5 = folder.join("test1,tmp")
    file5.write("Test File 5")

    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換

    # ユーザー入力を"y"としてモックする
    monkeypatch.setattr("builtins.input", lambda _: "y")

    dlf.delete_files_with_confirmation(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert not file2.exists()
    assert not file3.exists()
    assert not file4.exists()
    assert file5.exists()


def test_delete_files_with_confirmation_N(tmpdir, monkeypatch):
    folder = tmpdir.mkdir("test_folder")
    file1 = folder.join("test1.mov")
    file1.write("Test File 1")
    file2 = folder.join("test1_TV.mov")
    file2.write("Test File 2")
    file3 = folder.join("test1_LP.mov")
    file3.write("Test File 3")
    file4 = folder.join("test1_list.txt")
    file4.write("Test File 4")
    file5 = folder.join("test1,tmp")
    file5.write("Test File 5")

    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換

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
def output_folder():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_get_output_filename_from_user_with_input_files(output_folder, monkeypatch):
    video_extension_list = [".mov", ".mp4"]
    input_files = ["file1_TV.mov", "file2_TV.mp4"]

    # ユーザー入力をモック
    monkeypatch.setattr("builtins.input", lambda _: "output_file.mov")

    output_path = main.get_output_filename_from_user(
        video_extension_list, input_files, output_folder
    )

    expected_output_path = os.path.join(output_folder, "output_file.mov")
    assert output_path == expected_output_path


def test_get_output_filename_from_user_without_input_files(output_folder, monkeypatch):
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
    output_folder, monkeypatch, capsys
):
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


def test_create_ffmpeg_command_match_input_resolution_flag_true():
    match_input_resolution_flag = True
    input_files = [
        "./tests/test_data/input/ffmpeg_command_test/sample1_TV.mov",
        "./tests/test_data/input/ffmpeg_command_test/sample2_TV.mov",
        "./tests/test_data/input/ffmpeg_command_test/sample3_TV.mov",
        "./tests/test_data/input/ffmpeg_command_test/sample4_TV.mov",
    ]
    output_path = "./tests/test_data/output/sample1_out.mov"

    expected_ffmpeg_command = (
        "ffmpeg "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample1_TV.mov "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample2_TV.mov "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample3_TV.mov "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample4_TV.mov "
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
        "./tests/test_data/output/sample1_out.mov"
    )

    ffmpeg_command = main.create_ffmpeg_command(
        input_files, output_path, match_input_resolution_flag
    )

    assert ffmpeg_command == expected_ffmpeg_command


def test_create_ffmpeg_command_match_input_resolution_flag_false():
    match_input_resolution_flag = False
    input_files = [
        "./tests/test_data/input/ffmpeg_command_test/sample1_TV.mov",
        "./tests/test_data/input/ffmpeg_command_test/sample2_TV.mov",
        "./tests/test_data/input/ffmpeg_command_test/sample3_TV.mov",
        "./tests/test_data/input/ffmpeg_command_test/sample4_TV.mov",
    ]
    output_path = "./tests/test_data/output/sample1_out.mov"

    expected_ffmpeg_command = (
        "ffmpeg "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample1_TV.mov "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample2_TV.mov "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample3_TV.mov "
        "-i ./tests/test_data/input/ffmpeg_command_test/sample4_TV.mov "
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
        "./tests/test_data/output/sample1_out.mov"
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
def mock_file_operations(monkeypatch):
    def mock_rename_files_with_spaces(directory):
        pass

    def mock_get_video_files(directory, video_extension_list):
        return ["video1.mp4", "video2.mp4"]

    def mock_is_integer_square_root_greater_than_four(value):
        return True

    def mock_create_target_video(input_folder, video_files):
        pass

    def mock_makedirs(output_folder, exist_ok):
        pass

    def mock_custom_sorted(files):
        files.sort()
        return files

    def mock_get_target_files(input_folder, files):
        return ["file1_TV.mov", "file2_TV.mov"]

    def mock_get_output_filename_from_user(
        video_extension_list, input_files, output_folder
    ):
        return "/path/to/output_file.mov"

    def mock_create_ffmpeg_command(
        input_files, output_path, match_input_resolution_flag
    ):
        return "ffmpeg_command"

    def mock_subprocess_call(ffmpeg_command, shell):
        pass

    def mock_delete_files_in_folder(files, input_folder):
        pass

    def mock_exit(code):
        raise SystemExit(code)

    monkeypatch.setattr(rnf, "rename_files_with_spaces", mock_rename_files_with_spaces)
    monkeypatch.setattr(main, "get_video_files", mock_get_video_files)
    monkeypatch.setattr(
        main,
        "is_integer_square_root_greater_than_four",
        mock_is_integer_square_root_greater_than_four,
    )
    monkeypatch.setattr(main, "create_target_video", mock_create_target_video)
    monkeypatch.setattr(main.os, "makedirs", mock_makedirs)
    monkeypatch.setattr(builtins, "sorted", mock_custom_sorted)
    monkeypatch.setattr(main, "get_target_files", mock_get_target_files)
    monkeypatch.setattr(
        main, "get_output_filename_from_user", mock_get_output_filename_from_user
    )
    monkeypatch.setattr(main, "create_ffmpeg_command", mock_create_ffmpeg_command)
    monkeypatch.setattr(main.subprocess, "call", mock_subprocess_call)
    monkeypatch.setattr(dlf, "delete_files_in_folder", mock_delete_files_in_folder)
    monkeypatch.setattr(sys, "exit", mock_exit)


# def test_main_success_case(capsys, mock_input, mock_file_operations):
def test_main_success_case(capsys, mock_file_operations):
    main.main()

    # 出力の検証
    captured = capsys.readouterr()
    assert "Video Grid Merge Start" in captured.out
    assert "Video Grid Merge End And Output Success" in captured.out
    assert "File Output Complete: /path/to/output_file.mov" in captured.out
    assert "Processing Time(s): " in captured.out


def test_main_error_case(
    # capsys, mock_input, mock_file_operations, monkeypatch
    capsys,
    mock_file_operations,
    monkeypatch,
):
    def mock_get_video_files(directory, video_extension_list):
        return []

    def mock_is_integer_square_root_greater_than_four(value):
        return False

    monkeypatch.setattr(main, "get_video_files", mock_get_video_files)
    monkeypatch.setattr(
        main,
        "is_integer_square_root_greater_than_four",
        mock_is_integer_square_root_greater_than_four,
    )

    input_folder = "./video_grid_merge/media/input"  # input_folderの値を指定

    with pytest.raises(SystemExit) as e:
        main.main(input_folder)

    assert (
        str(e.value)
        == f"Error: Please store more than 4 video files in the input folder.\ninput_folder: {input_folder}"
    )
