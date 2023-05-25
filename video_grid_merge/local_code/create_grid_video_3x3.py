import math
import os
import subprocess
import time

import cv2

start = time.perf_counter()

# ビデオ拡張子リスト
video_extension_list = [".mov", ".mp4"]

# 入力動画の解像度に合わせるフラグ変数
match_input_resolution_flag = True

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
def get_extension(filename):
    _, ext = os.path.splitext(filename)
    return ext


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

# 入力動画の解像度を取得
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
    f"[4:v]scale={video_width}:{video_height}[v4]; "
    f"[5:v]scale={video_width}:{video_height}[v5]; "
    f"[6:v]scale={video_width}:{video_height}[v6]; "
    f"[7:v]scale={video_width}:{video_height}[v7]; "
    f"[8:v]scale={video_width}:{video_height}[v8]; "
    f"[v0][v1][v2]hstack=inputs=3[row1]; "
    f"[v3][v4][v5]hstack=inputs=3[row2]; "
    f"[v6][v7][v8]hstack=inputs=3[row3]; "
    f'[row1][row2][row3]vstack=inputs=3[vstack]" '
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
