import os
import sys
from pathlib import Path
from typing import Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_dir = os.path.dirname(os.path.abspath(__file__))

from video_grid_merge import delete_files as dlf

temporarily_data_list: List[str] = ["_TV", ".txt"]


def test_delete_files_in_folder(tmpdir: str) -> None:
    folder_path = Path(tmpdir) / "test_folder"
    folder_path.mkdir()

    file1 = folder_path / "test1.mov"
    file1.write_text("Test File 1")
    file2 = folder_path / "test1_TV.mov"
    file2.write_text("Test File 2")
    file3 = folder_path / "test1_list.txt"
    file3.write_text("Test File 4")
    file4 = folder_path / "test1,tmp"
    file4.write_text("Test File 5")

    dlf.delete_files_in_folder(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert not file2.exists()
    assert not file3.exists()
    assert file4.exists()

    # 追加修正: 削除されなかったファイルも存在することを確認
    assert os.path.exists(str(file1))
    assert os.path.exists(str(file4))


def test_delete_files_with_confirmation_y(tmpdir: str, monkeypatch: Any) -> None:
    folder = Path(tmpdir)  # フォルダパスをPathオブジェクトに変換
    folder.mkdir(parents=True, exist_ok=True)

    file1 = folder.joinpath("test1.mov")
    file1.write_text("Test File 1")
    file2 = folder.joinpath("test1_TV.mov")
    file2.write_text("Test File 2")
    file3 = folder.joinpath("test1_list.txt")
    file3.write_text("Test File 4")
    file4 = folder.joinpath("test1.tmp")
    file4.write_text("Test File 5")

    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換

    temporarily_data_list: List[str] = [
        "_TV",
        ".txt",
    ]  # temporarily_data_list の適切な型を定義する

    # ユーザー入力を"y"としてモックする
    monkeypatch.setattr("builtins.input", lambda _: "y")

    dlf.delete_files_with_confirmation(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert not file2.exists()
    assert not file3.exists()
    assert file4.exists()


def test_delete_files_with_confirmation_N(tmpdir: str, monkeypatch: Any) -> None:
    folder = Path(tmpdir)  # フォルダパスをPathオブジェクトに変換
    folder.mkdir(parents=True, exist_ok=True)

    file1 = folder.joinpath("test1.mov")
    file1.write_text("Test File 1")
    file2 = folder.joinpath("test1_TV.mov")
    file2.write_text("Test File 2")
    file4 = folder.joinpath("test1_list.txt")
    file4.write_text("Test File 3")
    file5 = folder.joinpath("test1,tmp")
    file5.write_text("Test File 4")

    folder_path = Path(str(folder))  # フォルダパスをPathオブジェクトに変換

    temporarily_data_list: List[str] = []  # temporarily_data_list の適切な型を定義する

    # ユーザー入力を"N"としてモックする
    monkeypatch.setattr("builtins.input", lambda _: "N")

    dlf.delete_files_with_confirmation(temporarily_data_list, str(folder_path))

    assert file1.exists()
    assert file2.exists()
    assert file4.exists()
    assert file5.exists()


def test_delete_files_in_folder_with_directory(tmpdir: str) -> None:
    folder = Path(tmpdir)  # フォルダパスをPathオブジェクトに変換
    folder.mkdir(parents=True, exist_ok=True)

    file1 = folder.joinpath("file_TV.txt")
    file1.write_text("Test File 1")
    (folder / "directory_TV").mkdir()

    folder_path = Path(str(folder))
    dlf.delete_files_in_folder(dlf.temporarily_data_list, str(folder_path))

    assert not (folder_path / "file_TV.txt").exists()
    assert (folder_path / "directory_TV").exists()
