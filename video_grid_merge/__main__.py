import math
import os
import subprocess
import sys
import time
from typing import List, Union

import cv2

input_folder = "./video_grid_merge/media/input"
output_folder = "./video_grid_merge/media/output"

# video_extension_list
video_extension_list = [".mov", ".mp4"]

# Flag variable to match input video resolution
match_input_resolution_flag = True

# Temporarily data type
temporarily_data_list = ["_TV", "_LP", ".txt"]

# Set the log level to be displayed by ffmpeg
ffmpeg_loglevel = "error"


def rename_files_with_spaces(directory: str):
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


def get_video_files(input_folder: str, video_extension_list: List) -> List[str]:
    """Returns a list of video file names that correspond to the list of extensions stored in the input folder.

    Args:
        input_folder (str): String representing the path to the folder containing the video file
        video_extension_list (List): List of strings representing the video file extensions to be obtained

    Returns:
        List: List of strings containing paths to video files
    """
    video_files = [
        file
        for file in os.listdir(input_folder)
        if os.path.splitext(file)[1] in video_extension_list
    ]
    # print(video_files)
    return video_files


def get_video_length_ffmpeg(file_path: str) -> Union[float, None]:
    """Obtains the metadata of the video specified by the argument in the FFmpeg command, extracts the video length (seconds) from it, and returns it.

    Args:
        file_path (str): String representing the path of the video file whose length is to be obtained

    Returns:
        Union[float, None]:
        Video length (float) if length was successfully obtained.
        None if the length could not be obtained.
    """
    command = ["ffmpeg", "-i", file_path]
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.communicate()[0].decode("utf-8")
    duration_line = [line for line in output.split("\n") if "Duration" in line]
    if duration_line:
        duration_text = duration_line[0].split("Duration: ")[1].split(",")[0]
        duration_parts = duration_text.split(":")
        duration = (
            int(duration_parts[0]) * 3600
            + int(duration_parts[1]) * 60
            + float(duration_parts[2])
        )
        return duration
    return None


def create_target_video(video_files: List[str]):
    """Aligns the length of the video output with respect to the video specified in the argument using the FFmpeg command.

    Args:
        video_files (List[str]): List of strings containing paths to video files
    """
    # Get video length
    lengths = [
        get_video_length_ffmpeg(os.path.join(input_folder, file))
        for file in video_files
    ]
    print(f"Input Video Time List: {lengths}")

    # Get the length of the longest video
    max_length = max(lengths)

    # Append all but the longest video to the file for the merging process
    for file, length in zip(video_files, lengths):
        if length == max_length:
            command = f"cp {os.path.join(input_folder, file)} {os.path.join(input_folder, os.path.splitext(file)[0])}_TV{os.path.splitext(file)[1]}"
            os.system(command)
        elif length < max_length:
            # Calculate the number of joins (converted to integer)
            count = int(max_length / length)
            output_file = os.path.join(
                input_folder, f"list_{os.path.splitext(file)[0]}.txt"
            )

            # Change to new creation mode
            with open(output_file, "w") as f:
                for _ in range(count):
                    f.write(f"file '{file}'\n")
                if max_length % length != 0:
                    # Add the remaining length
                    f.write(f"file '{file}'\n")

    # List of text files
    text_files = [
        os.path.join(input_folder, f"list_{os.path.splitext(file)[0]}.txt")
        for file in video_files
    ]

    # Execute FFmpeg command for merging process
    for text_file, video_file in zip(text_files, video_files):
        if os.path.exists(text_file):
            output_file = os.path.join(
                input_folder,
                f"{os.path.splitext(video_file)[0]}_LP{os.path.splitext(video_file)[1]}",
            )
            command = f"ffmpeg -f concat -safe 0 -i {text_file} -c copy {output_file} -loglevel {ffmpeg_loglevel}"
            os.system(command)

    # Execute FFmpeg command for trimming _LP files
    for video_file in video_files:
        if os.path.exists(
            os.path.join(
                input_folder,
                f"{os.path.splitext(video_file)[0]}_LP{os.path.splitext(video_file)[1]}",
            )
        ):
            input_file = os.path.join(
                input_folder,
                f"{os.path.splitext(video_file)[0]}_LP{os.path.splitext(video_file)[1]}",
            )
            output_file = os.path.join(
                input_folder,
                f"{os.path.splitext(video_file)[0]}_TV{os.path.splitext(video_file)[1]}",
            )
            command = f"ffmpeg -i {input_file} -ss 0 -t {max_length} -c:v copy -c:a copy {output_file} -loglevel {ffmpeg_loglevel}"
            os.system(command)


def get_file_extension(filename: str) -> str:
    """Returns a string with the file extension specified in the argument.

    Args:
        filename (str): File name to get extension

    Returns:
        str: extension string
    """
    _, ext = os.path.splitext(filename)
    return ext


def get_target_files(files: List[str]) -> List[str]:
    """Returns a list of video files from a folder that contains _TV and matches the extension list.

    Args:
        files (List[str]): List of files to be processed

    Returns:
        List[str]: List of paths to files that satisfy the condition
    """
    input_files = [
        os.path.join(input_folder, file)
        for file in files
        if "_TV" in file and get_file_extension(file) in video_extension_list
    ]
    return input_files


def get_output_filename_from_user(input_files: list[str]) -> str:
    """Output file name input.

    Args:
        input_files (list[str]): contains _TV and matches the extension list

    Returns:
        str: output file path
    """
    # Get extension from input file (_TV)
    output_extension = (
        get_file_extension(input_files[0]) if input_files else video_extension_list[0]
    )
    while True:
        # Enter output file name
        output_file = input(
            "Enter the name of the output file (default is 'combined_video{}'): ".format(
                output_extension
            )
        )
        if not output_file:
            output_file = "combined_video{}".format(output_extension)
        if get_file_extension(output_file) in video_extension_list:
            break
        else:
            print("Invalid file extension. Please enter a valid extension.")
    output_path = os.path.join(output_folder, output_file)
    return output_path


def create_ffmpeg_command(input_files: list[str], output_path: str) -> str:
    """Retrun FFmpeg command generation to create a grid-like video.

    Args:
        input_files (list[str]): contains _TV and matches the extension list
        output_path (str): output file path

    Returns:
        str: FFmpeg command
    """
    # Get the resolution of the input video
    if match_input_resolution_flag:
        if input_files:
            first_file = input_files[0]
            cap = cv2.VideoCapture(first_file)
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
    else:
        video_width = 640
        video_height = 480

    # Calculate the number of input videos
    N = len(input_files)
    sqrt_N = int(math.sqrt(N))

    # Set output video size
    # To extend the resolution for the input video, use the following
    output_width = video_width * sqrt_N
    output_height = video_height * sqrt_N
    # To match the resolution of the input video, use the following
    # output_width = video_width
    # output_height = video_height

    # Create FFmpeg command
    ffmpeg_command = (
        f"ffmpeg "
        f'{"".join([f"-i {input_file} " for input_file in input_files])}'
        f'-filter_complex "[0:v]scale={video_width}:{video_height}[v0]; '
    )

    for i in range(1, N):
        ffmpeg_command += f"[{i}:v]scale={video_width}:{video_height}[v{i}]; "

    for i in range(sqrt_N):
        for j in range(sqrt_N):
            index = i * sqrt_N + j
            ffmpeg_command += f"[v{index}]"

        ffmpeg_command += f"hstack=inputs={sqrt_N}[row{i+1}]; "

    for i in range(sqrt_N):
        ffmpeg_command += f"[row{i+1}]"

    ffmpeg_command += f'vstack=inputs={sqrt_N}[vstack]" '

    ffmpeg_command += (
        f'-map "[vstack]" '
        f'{"".join([f"-map {i}:a " for i in range(len(input_files))])}'
        f"-c:v libx264 -preset ultrafast "
        f"-c:a copy "
        f"-loglevel {ffmpeg_loglevel} "
        f"-s {output_width}x{output_height} "
        f"{output_path}"
    )
    return ffmpeg_command


def delete_files_in_folder(input_folder: str):
    """Deletes temporary data files in the specified folder.

    Args:
        input_folder (str): Path of the folder to be deleted
    """
    files_to_delete = [
        file_name
        for file_name in os.listdir(input_folder)
        if any(x in file_name for x in temporarily_data_list)
    ]
    for file_name in files_to_delete:
        file_path = os.path.join(input_folder, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def delete_files_with_confirmation(path: str):
    """Ask for confirmation before deleting a file in the specified path.

    Args:
        path (str): Path to be deleted
    """
    confirmation = input(
        f"Files other than input videos were created in the following paths. Do you want to delete the created files?[y/N]\n{path}\n"
    )
    if confirmation.lower() == "y":
        delete_files_in_folder(path)


def is_integer_square_root_greater_than_four(n):
    root = math.sqrt(n)
    return root == int(root) and root >= 2


def main():
    # Start measurement of program elapsed time
    start = time.perf_counter()
    # Rename files under the folder
    rename_files_with_spaces(input_folder)
    # Input video information acquisition
    video_files = get_video_files(input_folder, video_extension_list)
    print(len(video_files))
    if not is_integer_square_root_greater_than_four(int(len(video_files))):
        warning_message = f"Error: Please store more than 4 video files in the input folder.\ninput_folder: {input_folder}"
        sys.exit(warning_message)
    # Loop processing of input video & creation of combined video
    create_target_video(video_files)
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    # Retrieve and sort files in a folder
    files = os.listdir(input_folder)
    files = sorted(files)
    # Get the _TV.mov file as input video
    input_files = get_target_files(files)
    # Specify output file name (user input)
    output_path = get_output_filename_from_user(input_files)
    # Create FFmpeg command
    ffmpeg_command = create_ffmpeg_command(input_files, output_path)
    # Execute FFmpeg command
    print("Video Grid Merge Start")
    subprocess.call(ffmpeg_command, shell=True)
    # Delete files other than input videos
    # delete_files_with_confirmation(input_folder)
    delete_files_in_folder(input_folder)
    print("Video Grid Merge End And Output Success")
    print(f"File Output Complete: {output_path}")
    # Program elapsed time measurement complete & displayed
    elapsed_time = time.perf_counter() - start
    calc_elapsed_time = "{:.8f}".format(elapsed_time)
    print(f"Processing Time(s): {calc_elapsed_time}\n")


if __name__ == "__main__":
    main()
