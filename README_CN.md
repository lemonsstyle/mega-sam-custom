# MEGA-SAM 自定义视频测试指南

中文文档| [English](./README.md) 

原文为 CVPR 2025（Best Paper Honorable Mention），题目 [MegaSaM：Accurate, Fast and Robust Structure and Motion from Casual Dynamic Videos](https://github.com/mega-sam/mega-sam)
本指南介绍如何使用改进版v2脚本处理自己的视频数据。

---

## 前置准备

### 1. AutoDL环境配置(非AutoDL请忽略）

如果在国内服务器上运行，建议先配置网络加速和镜像源：

```bash
# 网络加速（如果有）
source /etc/network_turbo

# 使用HuggingFace镜像加速模型下载
export HF_ENDPOINT=https://hf-mirror.com
```

### 2. 检查必需的模型文件

确保以下模型文件已下载：
- `checkpoints/megasam_final.pth` - MegaSaM主模型
- `Depth-Anything/checkpoints/depth_anything_vitl14.pth` - [Depth-Anything模型](https://drive.google.com/file/d/14Yve37sf3qJ7yZFeieL8N6YwpQ5tpFHu/view?usp=drive_link)
- `cvd_opt/raft-things.pth` - RAFT光流模型（可选，用于CVD优化）
- `base/xformers-0.0.22.post7-py310_cu11.8.0_pyt2.0.1.tar.bz2` - [xformers 安装包](https://drive.google.com/file/d/1WPmOFUJ2ScFlm21h23uVhkgGqfGMYrVF/view?usp=drive_link)

---

## 完整处理流程

### 步骤1: 提取视频帧

从视频文件中提取图像序列：

```bash
./prepare_video_v2.sh /root/autodl-tmp/1.mp4 --output-dir /root/autodl-tmp/test/
```

**参数说明：**
- 第一个参数：输入视频文件路径
- `--output-dir`：输出目录（提取的图像保存位置）
- `--fps`：提取帧率（可选，默认30）
- `--quality`：JPEG质量（可选，默认2，越小越好）

**输出：**
- 提取的图像序列保存在 `/root/autodl-tmp/test/`
- 文件名格式：`00001.jpg`, `00002.jpg`, ...

---

### 步骤2: 运行深度重建

处理图像序列，重建深度和相机轨迹：

```bash
./run_custom_video_v2.sh \
    --scene-name test \
    --data-dir /root/autodl-tmp/test \
    --output-dir /root/autodl-tmp/test/outputs \
    --recon-dir /root/autodl-tmp/test/reconstructions \
    --cvd-output-dir /root/autodl-tmp/test/outputs_cvd
```

**参数说明：**
- `--scene-name`：场景名称（用于输出文件命名）
- `--data-dir`：输入图像序列目录
- `--output-dir`：输出目录（保存相机轨迹）
- `--recon-dir`：重建数据目录
- `--cvd-output-dir`：CVD优化输出目录

**可选参数：**
- `--opt-focal`：启用焦距优化（相机焦距未知时使用）
- `--skip-depth`：跳过深度预计算（如果已运行过）
- `--skip-tracking`：跳过相机跟踪
- `--skip-cvd`：跳过CVD优化

**输出文件：**
```
/root/autodl-tmp/test/
├── outputs/
│   └── test_droid.npz              # 相机轨迹和初始深度
├── reconstructions/
│   └── test/
│       ├── images.npy              # RGB图像
│       ├── disps.npy               # 视差图
│       ├── poses.npy               # 相机位姿
│       ├── intrinsics.npy          # 相机内参
│       └── motion_prob.npy         # 运动概率
└── outputs_cvd/
    └── test_sgd_cvd_hr.npz         # CVD优化后的深度
```

**处理时间：**
- 深度预计算：约1-2分钟/100帧
- 相机跟踪：约2-5分钟/100帧
- CVD优化：约3-5分钟/100帧

---

### 步骤3: 可视化结果（HTML版）

生成可下载的HTML可视化文件：

```bash
python ./visual/visualize_results.py test \
    --cvd-dir /root/autodl-tmp/test/outputs_cvd \
    --recon-dir /root/autodl-tmp/test/reconstructions \
    --output /root/autodl-tmp/test/visualization.html \
    --max-frames 100
```

**参数说明：**
- 第一个参数：场景名称
- `--cvd-dir`：CVD输出目录路径
- `--recon-dir`：重建数据目录路径
- `--output`：输出HTML文件路径
- `--max-frames`：最大帧数（默认50，设为0使用所有帧）

**输出：**
- 生成独立的HTML文件（约25-50MB）
- 包含RGB图像、深度图、相机轨迹

---

### 步骤4: 可视化结果（3D点云版）

启动Web服务器，在线查看3D点云：

```bash
python ./visual/pointcloud_viewer.py test \
    --port 6006 \
    --cvd-dir /root/autodl-tmp/test/outputs_cvd \
    --max-points 100000 \
    --sample-frames 10
```

**参数说明：**
- 第一个参数：场景名称
- `--port`：服务器端口（默认6006）
- `--cvd-dir`：CVD输出目录路径
- `--max-points`：最大点数（默认100000）
- `--sample-frames`：采样帧数（默认10）

**访问方式(非AutoDL请忽略）：**

选中实例的自定义服务，点开 6006 对应地址即可。

**性能建议：**
- 快速预览：`--max-points 50000 --sample-frames 5`
- 标准质量：`--max-points 100000 --sample-frames 10`
- 高质量：`--max-points 200000 --sample-frames 20`

---

## 常见问题

### Q1: 如何只重新运行某个步骤？

使用 `--skip-*` 参数跳过已完成的步骤：

```bash
# 只运行CVD优化（跳过深度预计算和相机跟踪）
./run_custom_video_v2.sh \
    --scene-name test \
    --data-dir /root/autodl-tmp/test \
    --output-dir /root/autodl-tmp/test/outputs \
    --recon-dir /root/autodl-tmp/test/reconstructions \
    --cvd-output-dir /root/autodl-tmp/test/outputs_cvd \
    --skip-depth \
    --skip-tracking
```

### Q2: 如何提取视频的特定片段？

使用 `--start-time` 和 `--duration` 参数：

```bash
# 从第30秒开始，提取60秒
./prepare_video_v2.sh video.mp4 \
    --output-dir /path/to/output \
    --start-time 30 \
    --duration 60
```

### Q3: 如何调整提取的帧率？

使用 `--fps` 参数：

```bash
# 每秒提取15帧（降低帧率可减少处理时间）
./prepare_video_v2.sh video.mp4 \
    --output-dir /path/to/output \
    --fps 15
```

### Q4: HTML文件太大怎么办？

减少 `--max-frames` 参数：

```bash
# 只包含50帧（约25MB）
python ./visual/visualize_results.py test \
    --cvd-dir /path/to/outputs_cvd \
    --recon-dir /path/to/reconstructions \
    --output visualization.html \
    --max-frames 50
```

### Q5: 点云显示的帧数太少？

增加 `--sample-frames` 参数：

```bash
# 采样20帧生成点云
python ./visual/pointcloud_viewer.py test \
    --port 6006 \
    --cvd-dir /path/to/outputs_cvd \
    --sample-frames 20
```

### Q6: 如何处理多个视频？

使用循环批量处理：

```bash
for video in video1.mp4 video2.mp4 video3.mp4; do
    name=$(basename "$video" .mp4)

    # 提取帧
    ./prepare_video_v2.sh "$video" --output-dir "data/$name"

    # 运行重建
    ./run_custom_video_v2.sh \
        --scene-name "$name" \
        --data-dir "data/$name" \
        --output-dir "results/$name/outputs" \
        --recon-dir "results/$name/reconstructions" \
        --cvd-output-dir "results/$name/outputs_cvd"
done
```

---

## 输出文件说明

### 1. 相机轨迹文件 (`*_droid.npz`)

```python
import numpy as np
data = np.load('outputs/test_droid.npz')

# 包含的数据：
# - images: (N, H, W, 3) RGB图像
# - depths: (N, H, W) 深度图
# - intrinsic: (3, 3) 相机内参矩阵
# - cam_c2w: (N, 4, 4) 相机到世界坐标变换矩阵
```

### 2. 重建数据文件夹 (`reconstructions/`)

```python
import numpy as np

images = np.load('reconstructions/test/images.npy')      # (N, 3, H, W)
disps = np.load('reconstructions/test/disps.npy')        # (N, H, W)
poses = np.load('reconstructions/test/poses.npy')        # (N, 7) [x,y,z,qx,qy,qz,qw]
intrinsics = np.load('reconstructions/test/intrinsics.npy')  # (N, 4) [fx,fy,cx,cy]
```

### 3. CVD优化深度 (`*_sgd_cvd_hr.npz`)

```python
import numpy as np
data = np.load('outputs_cvd/test_sgd_cvd_hr.npz')

# 包含的数据：
# - images: (N, H, W, 3) RGB图像
# - depths: (N, H, W) 优化后的深度图
# - intrinsic: (3, 3) 相机内参矩阵
# - cam_c2w: (N, 4, 4) 相机位姿
```

---

## 性能优化建议

### 1. 减少图像数量
- 降低提取帧率：`--fps 15` 或 `--fps 10`
- 提取视频片段：使用 `--start-time` 和 `--duration`

### 2. 跳过不必要的步骤
- 如果不需要CVD优化：`--skip-cvd`
- 如果已运行过深度预计算：`--skip-depth`

### 3. 调整可视化参数
- HTML版：减少 `--max-frames`
- 点云版：减少 `--sample-frames` 和 `--max-points`

---


更多详细信息请参考：
- `visual/README.md` - 可视化工具说明
- `visual/POINTCLOUD_README.md` - 点云工具详细说明
