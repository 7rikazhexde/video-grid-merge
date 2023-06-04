import os
import subprocess
from typing import Optional

# ビデオ拡張子リスト
video_extension_list = [".mov", ".mp4"]

# 入力フォルダのパス
folder_path = "./video_grid_merge/media/input"

# 拡張子リストを元に動画ファイルを取得
video_files = [
    file
    for file in os.listdir(folder_path)
    if os.path.splitext(file)[1] in video_extension_list
]


# 動画の長さを取得
def get_video_length_ffmpeg(file_path: str) -> Optional[float]:
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


# 動画の長さを取得
lengths = [
    get_video_length_ffmpeg(os.path.join(folder_path, file)) for file in video_files
]

# 最も長い動画の長さ
max_length = (
    max(length for length in lengths if length is not None) if any(lengths) else None
)

# 最長の動画以外を結合処理のためのファイルに追記する
for file, length in zip(video_files, lengths):
    if length == max_length:
        command = f"cp {os.path.join(folder_path, file)} {os.path.join(folder_path, os.path.splitext(file)[0])}_TV{os.path.splitext(file)[1]}"
        os.system(command)
    elif length and max_length and length < max_length:
        count = int(max_length / length)  # 結合回数を計算 (整数に変換)
        output_file = os.path.join(folder_path, f"list_{os.path.splitext(file)[0]}.txt")

        with open(output_file, "w") as f:  # 新規作成モードに変更
            for _ in range(count):
                f.write(f"file '{file}'\n")
            if max_length % length != 0:
                f.write(f"file '{file}'\n")  # 残りの長さ分を追記

# テキストファイルのリスト
text_files = [
    os.path.join(folder_path, f"list_{os.path.splitext(file)[0]}.txt")
    for file in video_files
]

# FFmpegコマンドを実行して結合処理を行う
for text_file, video_file in zip(text_files, video_files):
    if os.path.exists(text_file):
        output_file = os.path.join(
            folder_path,
            f"{os.path.splitext(video_file)[0]}_LP{os.path.splitext(video_file)[1]}",
        )
        command = f"ffmpeg -f concat -safe 0 -i {text_file} -c copy {output_file}"
        os.system(command)

# RPファイルをトリミングする
for video_file in video_files:
    if os.path.exists(
        os.path.join(
            folder_path,
            f"{os.path.splitext(video_file)[0]}_LP{os.path.splitext(video_file)[1]}",
        )
    ):
        input_file = os.path.join(
            folder_path,
            f"{os.path.splitext(video_file)[0]}_LP{os.path.splitext(video_file)[1]}",
        )
        output_file = os.path.join(
            folder_path,
            f"{os.path.splitext(video_file)[0]}_TV{os.path.splitext(video_file)[1]}",
        )
        command = f"ffmpeg -i {input_file} -ss 0 -t {max_length} -c:v copy -c:a copy {output_file}"
        os.system(command)
