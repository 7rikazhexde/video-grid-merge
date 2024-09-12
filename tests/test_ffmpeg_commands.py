import math
import os
import sys
from typing import Any, List

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_grid_merge import __main__ as main

base_dir = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(base_dir, "test_data", "input", "get_videos")
SAMPLE_VIDEOS = ["sample1.mov", "sample2.mov", "sample3.mov", "sample4.mov"]
EXPECTED_WIDTH = 640
EXPECTED_HEIGHT = 360


@pytest.fixture
def sample_video_paths() -> List[str]:
    return [os.path.join(TEST_DATA_DIR, video) for video in SAMPLE_VIDEOS]


@pytest.mark.parametrize("match_input_resolution_flag", [True, False])
def test_create_ffmpeg_command_v1(
    sample_video_paths: List[str], match_input_resolution_flag: bool
) -> None:
    output_path = "output.mp4"

    # Verify that all sample videos exist
    for path in sample_video_paths:
        assert os.path.exists(path), f"Sample video {path} does not exist"

    # Verify video dimensions
    for path in sample_video_paths:
        size = main.get_video_size(path)
        assert size is not None, f"Failed to get video size for {path}"
        width, height = size
        assert (
            width == EXPECTED_WIDTH and height == EXPECTED_HEIGHT
        ), f"Unexpected video dimensions for {path}: {width}x{height}"

    command = main.create_ffmpeg_command_v1(
        sample_video_paths, output_path, match_input_resolution_flag
    )

    # Check if the command is not empty
    assert command != ""

    # Check if all input files are in the command
    for input_file in sample_video_paths:
        assert input_file in command

    # Check if output path is in the command
    assert output_path in command

    # Check the output resolution
    N = len(sample_video_paths)
    sqrt_N = int(math.sqrt(N))
    if match_input_resolution_flag:
        expected_resolution = f"{EXPECTED_WIDTH * sqrt_N}x{EXPECTED_HEIGHT * sqrt_N}"
    else:
        expected_resolution = f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
    assert f"-s {expected_resolution}" in command

    # Check if filter complex is present
    assert "-filter_complex" in command

    # Check if the number of scale operations matches the number of input files
    scale_count = command.count(f"scale={EXPECTED_WIDTH}:{EXPECTED_HEIGHT}")
    assert scale_count == N

    # Check if the number of hstack operations is correct
    hstack_count = command.count("hstack=inputs=")
    assert hstack_count == sqrt_N

    # Check if vstack operation is present
    assert "vstack=inputs=" in command


def test_create_ffmpeg_command_v1_empty_input() -> None:
    command = main.create_ffmpeg_command_v1([], "output.mp4", True)
    assert command == ""


def test_create_ffmpeg_command_v1_invalid_video_size(tmp_path: Any) -> None:
    # Create an empty file that ffprobe can't read
    invalid_file = tmp_path / "invalid.mp4"
    invalid_file.touch()
    command = main.create_ffmpeg_command_v1([str(invalid_file)], "output.mp4", True)
    assert command == ""


@pytest.mark.parametrize("match_input_resolution_flag", [True, False])
def test_create_ffmpeg_command_v2(
    sample_video_paths: List[str], match_input_resolution_flag: bool
) -> None:
    output_path = "output.mp4"

    # Verify that all sample videos exist
    for path in sample_video_paths:
        assert os.path.exists(path), f"Sample video {path} does not exist"

    # Verify video dimensions
    for path in sample_video_paths:
        size = main.get_video_size(path)
        assert size is not None, f"Failed to get video size for {path}"
        width, height = size
        assert (
            width == EXPECTED_WIDTH and height == EXPECTED_HEIGHT
        ), f"Unexpected video dimensions for {path}: {width}x{height}"

    command = main.create_ffmpeg_command_v2(
        sample_video_paths, output_path, match_input_resolution_flag
    )

    # Check if the command is not empty
    assert command != ""

    # Check if all input files are in the command
    for input_file in sample_video_paths:
        assert input_file in command

    # Check if output path is in the command
    assert output_path in command

    # Check the output resolution
    N = len(sample_video_paths)
    sqrt_N = int(math.sqrt(N))
    if match_input_resolution_flag:
        expected_resolution = f"{EXPECTED_WIDTH * sqrt_N}x{EXPECTED_HEIGHT * sqrt_N}"
    else:
        expected_resolution = f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
    assert f"-s {expected_resolution}" in command

    # Check if filter complex is present
    assert "-filter_complex" in command

    # Check if the number of scale operations matches the number of input files
    scale_count = command.count(f"scale={EXPECTED_WIDTH}:{EXPECTED_HEIGHT}")
    assert scale_count == N

    # Check if the number of hstack operations is correct
    hstack_count = command.count("hstack=inputs=")
    assert hstack_count == sqrt_N

    # Check if vstack operation is present
    assert "vstack=inputs=" in command


def test_create_ffmpeg_command_v2_empty_input() -> None:
    command = main.create_ffmpeg_command_v2([], "output.mp4", True)
    assert command == ""


def test_create_ffmpeg_command_v2_invalid_video_size(tmp_path: Any) -> None:
    # Create an empty file that ffprobe can't read
    invalid_file = tmp_path / "invalid.mp4"
    invalid_file.touch()
    command = main.create_ffmpeg_command_v2([str(invalid_file)], "output.mp4", True)
    assert command == ""
