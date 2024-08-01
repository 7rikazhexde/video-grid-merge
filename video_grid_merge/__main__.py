import atexit
import io
import math
import os
import subprocess
import sys
import termios
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import List, Optional, Tuple, Union

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from video_grid_merge import delete_files as dlf
from video_grid_merge import rename_files as rnf

video_extension_list = [".mov", ".mp4"]
match_input_resolution_flag = True
temporarily_data_list = ["_TV", "_LP", ".txt"]
ffmpeg_loglevel = "error"
ffmpeg_cmd_version = "v1"

original_terminal_settings = None


def init_terminal_settings() -> None:
    """
    Initialize and save the original terminal settings.

    This function attempts to save the current terminal settings. If successful,
    these settings can be used later to reset the terminal to its original state.

    Global Variables:
        original_terminal_settings (termios.tcgetattr): Stores the original terminal settings.

    Raises:
        termios.error: If there's an error getting the terminal attributes.
        io.UnsupportedOperation: If the operation is not supported (e.g., in a non-interactive environment).
    """
    global original_terminal_settings
    try:
        original_terminal_settings = termios.tcgetattr(sys.stdin)
    except (termios.error, io.UnsupportedOperation):
        original_terminal_settings = None


init_terminal_settings()


def reset_terminal() -> None:
    """
    Reset terminal settings to their original state.

    This function restores the terminal settings to the state they were in
    when the program started. It uses the global variable
    'original_terminal_settings' to achieve this.

    The function specifically:
        1. Uses termios.tcsetattr to apply the original settings.
        2. Applies the settings immediately but waits for output to drain first.

    Side Effects:
        - Modifies the current terminal settings.
        - May affect how the terminal handles input and output after this call.

    Notes:
        - This function should typically be called before the program exits,
          to ensure the terminal is left in a usable state.
        - The global variable 'original_terminal_settings' must be properly
          initialized before this function is called.
        - This function is specifically for use on Unix-like systems and
          may not work on other operating systems.

    Raises:
        termios.error: If there's an error setting the terminal attributes.
    """
    if original_terminal_settings is not None:
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
        except termios.error:
            # Silently pass if we're in a non-interactive environment
            pass


# Ensure terminal settings are reset when the program exits
atexit.register(reset_terminal)


def safe_input(prompt: str) -> str:
    """
    Safely get input from user after resetting the input buffer.

    This function clears the input buffer before prompting for user input,
    which can help prevent unwanted input from being processed. The buffer
    is only cleared in an interactive environment.

    Args:
        prompt (str): The prompt to display to the user.

    Returns:
        str: The user's input.

    Notes:
        - The input buffer is only cleared if original_terminal_settings is not None,
          indicating we're in an interactive environment.
        - If clearing the buffer fails, the function will still attempt to get user input.
    """
    if original_terminal_settings is not None:
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except termios.error:
            # If flushing fails, continue to input anyway
            pass

    return input(prompt)


def get_video_files(input_folder: str) -> List[str]:
    """
    Get a list of video files from the specified input folder.

    Args:
        input_folder (str): The path to the folder containing video files.

    Returns:
        List[str]: A list of video file names with extensions in the video_extension_list.
    """
    return [
        file
        for file in os.listdir(input_folder)
        if os.path.splitext(file)[1] in video_extension_list
    ]


@lru_cache(maxsize=None)
def get_video_length_ffmpeg(file_path: str) -> Union[float, None]:
    """
    Get the duration of a video file using ffmpeg.

    This function is cached to improve performance for repeated calls.

    Args:
        file_path (str): The path to the video file.

    Returns:
        Union[float, None]: The duration of the video in seconds, or None if the duration
        cannot be determined.
    """
    command = ["ffmpeg", "-i", file_path]
    try:
        result = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output = result.communicate()[0].decode("utf-8")
        duration_line = next(
            (line for line in output.split("\n") if "Duration" in line), None
        )
        if duration_line:
            duration_text = duration_line.split("Duration: ")[1].split(",")[0]
            h, m, s = map(float, duration_text.split(":"))
            return h * 3600 + m * 60 + s
        return None
    except Exception:
        return None


def process_video(input_folder: str, file: str, max_length: float) -> None:
    """
    Process a single video file, either by linking or concatenating it to match the max_length.

    Args:
        input_folder (str): The path to the folder containing the input video.
        file (str): The name of the video file to process.
        max_length (float): The target length for the processed video.
    """
    length = get_video_length_ffmpeg(os.path.join(input_folder, file))
    if length == max_length:
        os.link(
            os.path.join(input_folder, file),
            os.path.join(
                input_folder,
                f"{os.path.splitext(file)[0]}_TV{os.path.splitext(file)[1]}",
            ),
        )
    elif length and max_length and length < max_length:
        count = int(max_length / length)
        output_file = os.path.join(
            input_folder, f"list_{os.path.splitext(file)[0]}.txt"
        )

        with open(output_file, "w") as f:
            f.write(f"file '{file}'\n" * count)
            if max_length % length != 0:
                f.write(f"file '{file}'\n")

        tv_file = os.path.join(
            input_folder, f"{os.path.splitext(file)[0]}_TV{os.path.splitext(file)[1]}"
        )
        subprocess.run(
            f"ffmpeg -f concat -safe 0 -i {output_file} -c copy -t {max_length} {tv_file} -loglevel {ffmpeg_loglevel}",
            shell=True,
        )


def create_target_video(input_folder: str, video_files: List[str]) -> None:
    """
    Create target videos by processing all input video files.

    This function determines the maximum length among all input videos and processes
    each video to match this length.

    Args:
        input_folder (str): The path to the folder containing the input videos.
        video_files (List[str]): A list of video file names to process.
    """
    lengths = [
        get_video_length_ffmpeg(os.path.join(input_folder, file))
        for file in video_files
    ]
    print(f"Input Video Time List: {lengths}")

    max_length = max((length for length in lengths if length is not None), default=None)
    if max_length is None:
        return

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_video, input_folder, file, max_length)
            for file in video_files
        ]
        for future in as_completed(futures):
            future.result()


def get_target_files(folder: str, files: List[str]) -> List[str]:
    """
    Get a list of processed video files (with '_TV' in the filename) from the specified folder.

    Args:
        folder (str): The path to the folder containing the processed video files.
        files (List[str]): A list of file names to filter.

    Returns:
        List[str]: A list of full paths to the processed video files.
    """
    return [
        os.path.join(folder, file)
        for file in files
        if "_TV" in file and file.endswith(tuple(video_extension_list))
    ]


def get_output_filename_from_user(output_folder: str) -> str:
    """
    Prompt the user for an output filename and handle potential file conflicts.

    Args:
        output_folder (str): The path to the output folder.

    Returns:
        str: The full path to the output file.
    """
    while True:
        output_file = safe_input(
            f"Enter the name of the output file (default is 'combined_video{video_extension_list[0]}'): "
        )
        if not output_file:
            output_file = f"combined_video{video_extension_list[0]}"
        if not output_file.endswith(tuple(video_extension_list)):
            output_file += video_extension_list[0]
        output_path = os.path.join(output_folder, output_file)
        if os.path.exists(output_path):
            overwrite = safe_input(
                f"File {output_file} already exists. Overwrite? (y/n): "
            )
            if overwrite.lower() != "y":
                continue
        return output_path


@lru_cache(maxsize=None)
def get_video_size(filename: str) -> Optional[Tuple[int, int]]:
    """
    Get the width and height of a video file using ffprobe.

    This function is cached to improve performance for repeated calls.

    Args:
        filename (str): The path to the video file.

    Returns:
        Optional[Tuple[int, int]]: A tuple containing the width and height of the video,
        or None if the size cannot be determined.
    """
    cmd = [
        "ffprobe",
        "-v",
        f"{ffmpeg_loglevel}",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=s=x:p=0",
        filename,
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        width, height = map(int, output.split("x"))
        return (width, height)
    except subprocess.CalledProcessError as e:
        print(f"Error: {str(e)}")
        return None


def create_ffmpeg_command(
    input_files: list[str], output_path: str, match_input_resolution_flag: bool
) -> str:
    """
    Create the ffmpeg command to merge multiple videos into a grid layout.

    Args:
        input_files (list[str]): A list of input video file paths.
        output_path (str): The path for the output video file.
        match_input_resolution_flag (bool): Whether to match the input video resolution.

    Returns:
        str: The ffmpeg command string.
    """
    if not input_files:
        return ""

    video_size = get_video_size(input_files[0])
    if video_size is None:
        return ""

    video_width, video_height = video_size

    N = len(input_files)
    sqrt_N = int(math.sqrt(N))

    if match_input_resolution_flag:
        output_width = video_width * sqrt_N
        output_height = video_height * sqrt_N
    else:
        output_width = video_width
        output_height = video_height

    filter_complex = "".join(
        [f"[{i}:v]scale={video_width}:{video_height}[v{i}]; " for i in range(N)]
    )
    filter_complex += "".join(
        [
            f'{"".join([f"[v{i*sqrt_N+j}]" for j in range(sqrt_N)])}hstack=inputs={sqrt_N}[row{i}]; '
            for i in range(sqrt_N)
        ]
    )
    filter_complex += (
        f'{"".join([f"[row{i}]" for i in range(sqrt_N)])}vstack=inputs={sqrt_N}[vstack]'
    )

    return (
        f"ffmpeg -y {' '.join([f'-i {input_file}' for input_file in input_files])} "
        f'-filter_complex "{filter_complex}" '
        f'-map "[vstack]" {" ".join([f"-map {i}:a" for i in range(len(input_files))])} '
        f"-c:v libx264 -preset ultrafast -c:a copy -loglevel {ffmpeg_loglevel} "
        f"-s {output_width}x{output_height} {output_path}"
    )


def create_ffmpeg_command_v2(
    input_files: list[str], output_path: str, match_input_resolution_flag: bool
) -> str:
    """
    Create an optimized ffmpeg command to merge multiple videos into a grid layout.

    Args:
        input_files (list[str]): A list of input video file paths.
        output_path (str): The path for the output video file.
        match_input_resolution_flag (bool): Whether to match the input video resolution.

    Returns:
        str: The optimized ffmpeg command string.
    """
    if not input_files:
        return ""

    video_size = get_video_size(input_files[0])
    if video_size is None:
        return ""

    video_width, video_height = video_size

    N = len(input_files)
    sqrt_N = int(math.sqrt(N))

    if match_input_resolution_flag:
        output_width = video_width * sqrt_N
        output_height = video_height * sqrt_N
    else:
        output_width = video_width
        output_height = video_height
    filter_complex = "".join(
        [
            f"[{i}:v]scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]; "
            for i in range(N)
        ]
    )
    filter_complex += "".join(
        [
            f'{"".join([f"[v{i*sqrt_N+j}]" for j in range(sqrt_N)])}hstack=inputs={sqrt_N}[row{i}]; '
            for i in range(sqrt_N)
        ]
    )
    filter_complex += (
        f'{"".join([f"[row{i}]" for i in range(sqrt_N)])}vstack=inputs={sqrt_N}[vstack]'
    )

    return (
        f"ffmpeg -y {' '.join([f'-i {input_file}' for input_file in input_files])} "
        f'-filter_complex "{filter_complex}" '
        f'-map "[vstack]" {" ".join([f"-map {i}:a" for i in range(len(input_files))])} '
        f"-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k "
        f"-threads 0 -loglevel {ffmpeg_loglevel} "
        f"-s {output_width}x{output_height} {output_path}"
    )


def main(
    input_folder: Optional[str] = None, output_folder: Optional[str] = None
) -> None:
    """
    Main function to process and merge multiple videos into a grid layout.

    This function handles the entire workflow, including:
    - Getting input video files
    - Creating target videos
    - Generating the ffmpeg command
    - Running the ffmpeg command to create the final merged video

    Args:
        input_folder (Optional[str]): The path to the input folder. If None, a default path is used.
        output_folder (Optional[str]): The path to the output folder. If None, a default path is used.
    """
    input_folder = input_folder or "./video_grid_merge/media/input"
    output_folder = output_folder or "./video_grid_merge/media/output"

    start = time.perf_counter()
    rnf.rename_files_with_spaces(input_folder)
    video_files = get_video_files(input_folder)

    if len(video_files) < 4 or int(math.sqrt(len(video_files))) ** 2 != len(
        video_files
    ):
        sys.exit(
            f"Error: Please store a perfect square number (>= 4) of video files in the input folder.\ninput_folder: {input_folder}"
        )

    os.makedirs(output_folder, exist_ok=True)
    output_path = get_output_filename_from_user(output_folder)

    create_target_video(input_folder, video_files)
    input_files = get_target_files(input_folder, sorted(os.listdir(input_folder)))

    if ffmpeg_cmd_version == "v1":
        ffmpeg_command = create_ffmpeg_command(
            input_files, output_path, match_input_resolution_flag
        )
    elif ffmpeg_cmd_version == "v2":
        ffmpeg_command = create_ffmpeg_command_v2(
            input_files, output_path, match_input_resolution_flag
        )
    else:
        raise ValueError(f"Invalid ffmpeg_cmd_version: {ffmpeg_cmd_version}")

    print("Video Grid Merge Start")
    subprocess.run(ffmpeg_command, shell=True)
    dlf.delete_files_in_folder(temporarily_data_list, input_folder)
    print("Video Grid Merge End And Output Success")
    print(f"File Output Complete: {output_path}")

    elapsed_time = time.perf_counter() - start
    print(f"Processing Time(s): {elapsed_time:.8f}\n")


if __name__ == "__main__":  # pragma: no cover
    main()
