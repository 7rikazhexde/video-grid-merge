import os


def rename_files_with_spaces(directory: str) -> None:
    """Replace blank spaces.

    Args:
        directory (str): input data folder
    """
    for root, _, files in os.walk(directory):
        for filename in files:
            if " " in filename or "　" in filename:
                new_filename = filename.replace(" ", "_").replace("　", "_")
                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_filename)
                os.rename(old_path, new_path)
                print(f"Renamed: {old_path} to {new_path}")


if __name__ == "__main__":  # pragma: no cover
    # Specify folder path
    folder_path = "./video_grid_merge/media/input"

    # Rename files under the folder
    rename_files_with_spaces(folder_path)
