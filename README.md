# video-grid-merge

[![Test](https://github.com/rcmdnk/homebrew-file/actions/workflows/test.yml/badge.svg)](https://github.com/7rikazhexde/video-grid-merge/actions/workflows/pytest.yml)

## Overview

This project allows you to use FFmpeg to arrange video files stored in a specified folder in a grid layout of NxN and generate the output.

## Screenshot

### input video files

[sample1.mov](./video_grid_merge/media/input/sample1.mov), [sample2.mov](./video_grid_merge/media/input/sample2.mov), [sample3.mov](./video_grid_merge/media/input/sample3.mov), [sample4.mov](./video_grid_merge/media/input/sample4.mov)

<img width="800" alt="sample-screenshot" src="https://github.com/7rikazhexde/video-grid-merge/assets/33836132/caccd49b-08a4-4c34-a8f4-8f82749716be">

## Note

- The video file generation process depends on the number of input videos (square root is an integer and must be greater than or equal to 2).
- For example, **4 videos** will be placed in a **2x2 layout**, and **9 videos** will be placed in a **3x3 layout**.
- Input videos should be stored in the input folder.
- The output video is created by looping and merging according to the longest video among the input videos, and stored in the output folder.
- The videos are arranged alphabetically from top left to top right and from bottom left to bottom right.
- To specify the placement, prefix it with a number.
- Target input and output video file formats are MP4 and MOV.

## Usage

### Installing FFmpeg

In order to execute the code, FFmpeg must be installed and accessible via the $PATH environment variable.

There are a variety of ways to install FFmpeg, such as the official download links, or using your package manager of choice (e.g. sudo apt install ffmpeg on Debian/Ubuntu, brew install ffmpeg on OS X, etc.).

Regardless of how FFmpeg is installed, you can check if your environment path is set correctly by running the ffmpeg command from the terminal, in which case the version information should appear, as in the following example (truncated for brevity):

```bash
$ ffmpeg
ffmpeg version 4.2.7-0ubuntu0.1 Copyright (c) 2000-2022 the FFmpeg developers
  built with gcc 9 (Ubuntu 9.4.0-1ubuntu1~20.04.1)
```

> **Note**\
> **The actual version information displayed here may vary from one system to another; but if a message such as ffmpeg: command not found appears instead of the version information, FFmpeg is not properly installed.**

### Environment building

#### Standard Version

- If you are using **poetry**, please execute the following command

```bash
git clone --filter=blob:none --no-checkout https://github.com/7rikazhexde/video-grid-merge.git && cd video-grid-merge && git sparse-checkout init --cone && git sparse-checkout set video_grid_merge && git checkout
poetry install --only main
```

#### Development version

- It includes a static analysis tool and test data that performs the following

```bash
git clone https://github.com/7rikazhexde/video-grid-merge.git
cd video-grid-merge
poetry install
```

#### Settings

- Input videos should be stored in the Input folder.
- Specify the resolution of the output video.
- The following two patterns are available for specifying the resolution. (Default is 1)
  1. Expand the number of Input Video:\
     `match_input_resolution_flag = true`
  1. 640x480:\
     `match_input_resolution_flag = false`

### Example

- Command Execution Result Example

```bash
$ python video_grid_merge
Input Video Time List: [48.31, 62.43, 63.96, 77.83]
Enter the name of the output file (default is 'combined_video.mov'): test.mov
Video Grid Merge Start
Video Grid Merge End And Output Success
File Output Complete: ./video_grid_merge/media/output/test.mov
Processing Time(s): 24.62715184
```

## Other

### delete temporary data

if you delete temporary data files in the specified folder

- poetry

```bash
poetry run task vgmrm
```

- Not poetry

```bash
python video_grid_merge/delete_files.py
```

### Synchronous update process of version and git tag in poetry.toml

If you fork this project, you can use the following function to synchronously update the versions of poetry.toml and git tags.\
If you need it, please see [the link](<(https://github.com/7rikazhexde/trial-test/issues/1)>) for instructions on how to use it.

#### Reference

[feat: Add Version update feature by pre-commit and post-commit #1](https://github.com/7rikazhexde/trial-test/issues/1)

[GitHub Action: pytest-coverage-comment](https://github.com/MishaKav/pytest-coverage-comment#example-usage)
