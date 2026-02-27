# MEGA-SAM Custom Video Testing Guide

[中文文档](./IMPROVED_SCRIPTS_GUIDE.md) | English

Original paper: CVPR 2025 (Best Paper Honorable Mention), [MegaSaM: Accurate, Fast and Robust Structure and Motion from Casual Dynamic Videos](https://github.com/mega-sam/mega-sam)
This guide explains how to use the improved v2 scripts to process your own video data.

---

## Prerequisites

### 1. AutoDL Environment Setup (Skip if not using AutoDL)

If running on a server in China, it is recommended to configure network acceleration and mirror sources first:

```bash
# Network acceleration (if available)
source /etc/network_turbo

# Use HuggingFace mirror to speed up model downloads
export HF_ENDPOINT=https://hf-mirror.com
```

### 2. Check Required Model Files

Make sure the following model files have been downloaded:
- `checkpoints/megasam_final.pth` - MegaSaM main model
- `Depth-Anything/checkpoints/depth_anything_vitl14.pth` - Depth-Anything model
- `cvd_opt/raft-things.pth` - RAFT optical flow model (optional, used for CVD optimization)
- `base/xformers-0.0.22.post7-py310_cu11.8.0_pyt2.0.1.tar.bz2` - xformers installation package

---

## Complete Processing Pipeline

### Step 1: Extract Video Frames

Extract an image sequence from a video file:

```bash
./prepare_video_v2.sh /root/autodl-tmp/1.mp4 --output-dir /root/autodl-tmp/test/
```

**Parameters:**
- First argument: input video file path
- `--output-dir`: output directory (where extracted images are saved)
- `--fps`: extraction frame rate (optional, default 30)
- `--quality`: JPEG quality (optional, default 2, lower is better)

**Output:**
- Extracted image sequence saved to `/root/autodl-tmp/test/`
- Filename format: `00001.jpg`, `00002.jpg`, ...

---

### Step 2: Run Depth Reconstruction

Process the image sequence to reconstruct depth and camera trajectories:

```bash
./run_custom_video_v2.sh \
    --scene-name test \
    --data-dir /root/autodl-tmp/test \
    --output-dir /root/autodl-tmp/test/outputs \
    --recon-dir /root/autodl-tmp/test/reconstructions \
    --cvd-output-dir /root/autodl-tmp/test/outputs_cvd
```

**Parameters:**
- `--scene-name`: scene name (used for output file naming)
- `--data-dir`: input image sequence directory
- `--output-dir`: output directory (saves camera trajectories)
- `--recon-dir`: reconstruction data directory
- `--cvd-output-dir`: CVD optimization output directory

**Optional Parameters:**
- `--opt-focal`: enable focal length optimization (use when camera focal length is unknown)
- `--skip-depth`: skip depth pre-computation (if already run before)
- `--skip-tracking`: skip camera tracking
- `--skip-cvd`: skip CVD optimization

**Output Files:**
```
/root/autodl-tmp/test/
├── outputs/
│   └── test_droid.npz              # Camera trajectory and initial depth
├── reconstructions/
│   └── test/
│       ├── images.npy              # RGB images
│       ├── disps.npy               # Disparity maps
│       ├── poses.npy               # Camera poses
│       ├── intrinsics.npy          # Camera intrinsics
│       └── motion_prob.npy         # Motion probability
└── outputs_cvd/
    └── test_sgd_cvd_hr.npz         # CVD-optimized depth
```

**Processing Time:**
- Depth pre-computation: ~1-2 min / 100 frames
- Camera tracking: ~2-5 min / 100 frames
- CVD optimization: ~3-5 min / 100 frames

---

### Step 3: Visualize Results (HTML Version)

Generate a downloadable HTML visualization file:

```bash
python ./visual/visualize_results.py test \
    --cvd-dir /root/autodl-tmp/test/outputs_cvd \
    --recon-dir /root/autodl-tmp/test/reconstructions \
    --output /root/autodl-tmp/test/visualization.html \
    --max-frames 100
```

**Parameters:**
- First argument: scene name
- `--cvd-dir`: CVD output directory path
- `--recon-dir`: reconstruction data directory path
- `--output`: output HTML file path
- `--max-frames`: maximum number of frames (default 50, set to 0 to use all frames)

**Output:**
- Generates a standalone HTML file (~25-50MB)
- Contains RGB images, depth maps, and camera trajectories



**Features:**
- Play/pause video sequence
- Frame-by-frame RGB and depth map viewing
- Top-down view of camera trajectory
- Per-frame pose information display
- Keyboard shortcuts (Space, Left/Right arrows)

---

### Step 4: Visualize Results (3D Point Cloud Version)

Start a web server to view the 3D point cloud online:

```bash
python ./visual/pointcloud_viewer.py test \
    --port 6006 \
    --cvd-dir /root/autodl-tmp/test/outputs_cvd \
    --max-points 100000 \
    --sample-frames 10
```

**Parameters:**
- First argument: scene name
- `--port`: server port (default 6006)
- `--cvd-dir`: CVD output directory path
- `--max-points`: maximum number of points (default 100000)
- `--sample-frames`: number of sampled frames (default 10)

**Access Method (Skip if not using AutoDL):**

Select the instance's custom service and open the address corresponding to port 6006.



**Features:**
- 3D point cloud display (with RGB colors)
- Camera trajectory visualization
- Mouse interaction controls (rotate, pan, zoom)
- Real-time point size adjustment
- Show/hide camera trajectory

**Performance Recommendations:**
- Quick preview: `--max-points 50000 --sample-frames 5`
- Standard quality: `--max-points 100000 --sample-frames 10`
- High quality: `--max-points 200000 --sample-frames 20`

---

## FAQ

### Q1: How to re-run only a specific step?

Use `--skip-*` parameters to skip completed steps:

```bash
# Run only CVD optimization (skip depth pre-computation and camera tracking)
./run_custom_video_v2.sh \
    --scene-name test \
    --data-dir /root/autodl-tmp/test \
    --output-dir /root/autodl-tmp/test/outputs \
    --recon-dir /root/autodl-tmp/test/reconstructions \
    --cvd-output-dir /root/autodl-tmp/test/outputs_cvd \
    --skip-depth \
    --skip-tracking
```

### Q2: How to extract a specific segment of a video?

Use the `--start-time` and `--duration` parameters:

```bash
# Start from the 30th second, extract 60 seconds
./prepare_video_v2.sh video.mp4 \
    --output-dir /path/to/output \
    --start-time 30 \
    --duration 60
```

### Q3: How to adjust the extraction frame rate?

Use the `--fps` parameter:

```bash
# Extract 15 frames per second (lower frame rate reduces processing time)
./prepare_video_v2.sh video.mp4 \
    --output-dir /path/to/output \
    --fps 15
```

### Q4: What if the HTML file is too large?

Reduce the `--max-frames` parameter:

```bash
# Include only 50 frames (~25MB)
python ./visual/visualize_results.py test \
    --cvd-dir /path/to/outputs_cvd \
    --recon-dir /path/to/reconstructions \
    --output visualization.html \
    --max-frames 50
```

### Q5: Too few frames displayed in the point cloud?

Increase the `--sample-frames` parameter:

```bash
# Sample 20 frames to generate the point cloud
python ./visual/pointcloud_viewer.py test \
    --port 6006 \
    --cvd-dir /path/to/outputs_cvd \
    --sample-frames 20
```

### Q6: How to process multiple videos?

Use a loop for batch processing:

```bash
for video in video1.mp4 video2.mp4 video3.mp4; do
    name=$(basename "$video" .mp4)

    # Extract frames
    ./prepare_video_v2.sh "$video" --output-dir "data/$name"

    # Run reconstruction
    ./run_custom_video_v2.sh \
        --scene-name "$name" \
        --data-dir "data/$name" \
        --output-dir "results/$name/outputs" \
        --recon-dir "results/$name/reconstructions" \
        --cvd-output-dir "results/$name/outputs_cvd"
done
```

---

## Output File Descriptions

### 1. Camera Trajectory File (`*_droid.npz`)

```python
import numpy as np
data = np.load('outputs/test_droid.npz')

# Contains:
# - images: (N, H, W, 3) RGB images
# - depths: (N, H, W) depth maps
# - intrinsic: (3, 3) camera intrinsic matrix
# - cam_c2w: (N, 4, 4) camera-to-world transformation matrices
```

### 2. Reconstruction Data Folder (`reconstructions/`)

```python
import numpy as np

images = np.load('reconstructions/test/images.npy')      # (N, 3, H, W)
disps = np.load('reconstructions/test/disps.npy')        # (N, H, W)
poses = np.load('reconstructions/test/poses.npy')        # (N, 7) [x,y,z,qx,qy,qz,qw]
intrinsics = np.load('reconstructions/test/intrinsics.npy')  # (N, 4) [fx,fy,cx,cy]
```

### 3. CVD-Optimized Depth (`*_sgd_cvd_hr.npz`)

```python
import numpy as np
data = np.load('outputs_cvd/test_sgd_cvd_hr.npz')

# Contains:
# - images: (N, H, W, 3) RGB images
# - depths: (N, H, W) optimized depth maps
# - intrinsic: (3, 3) camera intrinsic matrix
# - cam_c2w: (N, 4, 4) camera poses
```

---

## Performance Optimization Tips

### 1. Reduce the Number of Images
- Lower the extraction frame rate: `--fps 15` or `--fps 10`
- Extract a video segment: use `--start-time` and `--duration`

### 2. Skip Unnecessary Steps
- If CVD optimization is not needed: `--skip-cvd`
- If depth pre-computation has already been run: `--skip-depth`

### 3. Adjust Visualization Parameters
- HTML version: reduce `--max-frames`
- Point cloud version: reduce `--sample-frames` and `--max-points`

---


For more details, please refer to:
- `visual/README.md` - Visualization tools documentation
- `visual/POINTCLOUD_README.md` - Point cloud tool detailed documentation
