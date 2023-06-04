import math
import os
import re
import subprocess
import time
from typing import Tuple, Union

start = time.perf_counter()

# ビデオ拡張子リスト
video_extension_list = [".mov", ".mp4"]

# 入力動画の解像度に合わせるフラグ変数
match_input_resolution_flag = True

# Set the log level to be displayed by ffmpeg
ffmpeg_loglevel = "error"

# 入力フォルダ
input_folder = "media"
input_folder = "./video_grid_merge/media/input"

# 出力フォルダ
output_folder = "media/output"
output_folder = "./video_grid_merge/media/output"
os.makedirs(output_folder, exist_ok=True)

# フォルダ内のファイルを取得してソート
files = os.listdir(input_folder)
files = sorted(files)


# 拡張子を取得するヘルパー関数
def get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext


def get_video_size(filename: str) -> Union[Tuple[int, int], None]:
    """Retrieves the width and height of a video file.

    Args:
        filename (str): The path to the video file.

    Returns:
        tuple or None: A tuple (width, height) representing the width and height of the video,
                       or None if the video size cannot be obtained.

    Raises:
        subprocess.CalledProcessError: If an error occurs while executing the ffprobe command.
        Exception: For other exceptions that occur during execution.

    Note:
        This function relies on the ffprobe command to parse the video metadata.
        If ffmpeg is installed, ffprobe is typically included, so there is no need to install it separately.
        Make sure ffmpeg is installed on your system.
    """
    cmd = [
        "ffprobe",
        "-v",
        f"{ffmpeg_loglevel}",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:nk=1",
        filename,
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        matches = re.findall(r"\d+", output)
        if len(matches) >= 2:
            width = int(matches[0])
            height = int(matches[1])
            return width, height
        else:
            raise Exception(f"Failed to extract video size from {filename}.")
    except subprocess.CalledProcessError as e:
        raise e
    except Exception as e:
        raise Exception(f"Error: {str(e)}")


# 拡張子を取得して動画ファイルのみを選択
input_files = [
    os.path.join(input_folder, file)
    for file in files
    if "_TV" in file and get_extension(file) in video_extension_list
]

# 出力ファイル名の入力
output_extension = (
    get_extension(input_files[0]) if input_files else video_extension_list[0]
)
output_file = input(
    "出力ファイル名を入力してください（デフォルトは 'combined_video{}'）: ".format(output_extension)
)
if not output_file:
    output_file = "combined_video{}".format(output_extension)
output_path = os.path.join(output_folder, output_file)

# Get the resolution of the input video
if match_input_resolution_flag and input_files:
    video_size = get_video_size(input_files[0])
    if video_size is not None:
        video_width, video_height = video_size
    else:
        print("入力ファイルの解像度を取得できませんでした。")
        exit()
elif not input_files:
    print("入力ファイルが見つかりません。")
    exit()
else:
    video_width = 640
    video_height = 480

# 入力動画件数を算出
N = len(input_files)
sqrt_N = int(math.sqrt(N))

# 出力動画のサイズ設定
# 入力動画分の解像度を拡張する場合は以下
output_width = video_width * sqrt_N
output_height = video_height * sqrt_N
# 入力動画の解像度に合わせる場合は以下
# output_width = video_width
# output_height = video_height

# FFmpegコマンドを作成
ffmpeg_command = (
    f"ffmpeg "
    f'{"".join([f"-i {input_file} " for input_file in input_files])}'
    f'-filter_complex "[0:v]scale={video_width}:{video_height}[v0]; '
    f"[1:v]scale={video_width}:{video_height}[v1]; "
    f"[2:v]scale={video_width}:{video_height}[v2]; "
    f"[3:v]scale={video_width}:{video_height}[v3]; "
    f"[v0][v1]hstack=inputs=2[row1]; "
    f"[v2][v3]hstack=inputs=2[row2]; "
    f'[row1][row2]vstack=inputs=2[vstack]" '
    f'-map "[vstack]" '
    f'{"".join([f"-map {i}:a " for i in range(len(input_files))])}'  # 入力ファイルの音声をマッピング
    f"-c:v libx264 -preset ultrafast "  # 映像のエンコード設定
    f"-c:a copy "  # 音声をコピー
    f"-s {output_width}x{output_height} "
    f"{output_path}"
)

# FFmpegコマンドを実行
subprocess.call(ffmpeg_command, shell=True)

elapsed_time = time.perf_counter() - start
calc_elapsed_time = "{:.8f}".format(elapsed_time)
print(f"calc_elapsed_time: {calc_elapsed_time}[sec]\n")
