# video-grid-merge
## Overview
This project allows you to use FFmpeg to arrange video files stored in a specified folder in a grid layout of NxN and generate the output.

## Note
 - The video file generation process depends on the number of input videos (square root is an integer and must be greater than or equal to 2).
 - For example, **4 videos** will be placed in a **2x2 layout**, and **9 videos** will be placed in a **3x3 layout**.
 - Input videos should be stored in the input folder.
 - The output video is created by looping and merging according to the longest video among the input videos, and stored in the output folder.
 - The videos are arranged alphabetically from top left to top right and from bottom left to bottom right.
 - To specify the placement, prefix it with a number.
 - Target input and output video file formats are MP4 and MOV.
 
## Usage
### Environment building
- If you are using **poetry**, please execute the following command。
```
% git clone
% poetry install --only main
```

- Create a virtual environment with **venv**, **pyenv**, etc. and execute the following commands.
```
% pip install -r requirements.txt
```
- Input videos should be stored in the Input folder.
- Specify the resolution of the output video.
- The following two patterns are available for specifying the resolution. (Default is 1)
	1. Expand the number of Input Video (Please change ```match_input_resolution_flag = true```)
	2. 640x480 (Please change ```match_input_resolution_flag = false```)

- command execution
```
% python video_grid_merge
```
- Upon successful completion, the video is saved in the output folder.

## Other
if you delete temporary data files in the specified folder
- poetry
```
% poetry run task vgmrm
```

- Not poetry
```
% python video_grid_merge/delete_files.py
```
