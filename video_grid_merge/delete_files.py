import os

temporarily_data_list = ["_TV", "_LP", ".txt"]


def delete_files_in_folder(folder_path):
    """Deletes temporary data files in the specified folder.

    Args:
        input_folder (str): Path of the folder to be deleted
    """
    files_to_delete = [
        file_name
        for file_name in os.listdir(folder_path)
        if any(x in file_name for x in temporarily_data_list)
    ]
    for file_name in files_to_delete:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def delete_files_with_confirmation(path):
    """Ask for confirmation before deleting a file in the specified path.

    Args:
        path (str): Path to be deleted
    """
    confirmation = input(
        f"\nFiles other than input videos were created in the following paths.\nDo you want to delete the created files?[y/N]\n{path}\n"
    )
    if confirmation.lower() == "y":
        delete_files_in_folder(path)


def main():
    # Specify the path of the folder you want to delete
    path = "./video_grid_merge/media/input"
    delete_files_with_confirmation(path)


if __name__ == "__main__":
    main()
