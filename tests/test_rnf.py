import os
import shutil
import sys
from typing import Generator

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_dir = os.path.dirname(os.path.abspath(__file__))

from video_grid_merge import rename_files as rnf


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
