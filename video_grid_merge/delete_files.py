import os
from typing import List

temporarily_data_list = ["_TV", ".txt"]


def delete_files_in_folder(tmp_data_list: List[str], input_folder: str) -> None:
    """Deletes temporary data files in the specified folder.

    Args:
        tmp_data_list (List[str]): List defining temporarily stored data information
        input_folder (str): Path of the folder to be deleted
    """
    files_to_delete = [
        file_name
        for file_name in os.listdir(input_folder)
        if any(x in file_name for x in tmp_data_list)
    ]
    for file_name in files_to_delete:
        file_path = os.path.join(input_folder, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def delete_files_with_confirmation(tmp_data_list: List[str], path: str) -> None:
    """Ask for confirmation before deleting a file in the specified path.

    Args:
        tmp_data_list (List[str]): List defining temporarily stored data information
        path (str): Path to be deleted
    """
    confirmation = input(
        f"\nFiles other than input videos were created in the following paths.\n{path}\nDo you want to delete the created files?[y/N] "
    )
    if confirmation.lower() == "y":
        delete_files_in_folder(tmp_data_list, path)


if __name__ == "__main__":  # pragma: no cover
    path = "./video_grid_merge/media/input"
    delete_files_with_confirmation(temporarily_data_list, path)
