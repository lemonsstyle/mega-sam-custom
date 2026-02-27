#!/bin/bash
# Copyright 2025 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

# 在自己的视频上运行 MegaSaM 的自动化脚本

set -e  # 遇到错误立即退出

# ============ 配置参数 ============
# 修改这些参数以适配你的视频

# 场景名称（用于保存输出）
SCENE_NAME="my_video"

# 视频数据路径（包含图像序列的目录）
DATA_DIR="data/my_scene"

# GPU 设备
GPU_ID=0

# 是否启用焦距优化（如果相机焦距未知，设置为 true）
OPT_FOCAL=false

# 是否禁用可视化（设置为 true 可以加快处理速度）
DISABLE_VIS=true

# ============ 检查必需文件 ============
echo "检查必需的模型文件..."

if [ ! -f "checkpoints/megasam_final.pth" ]; then
    echo "错误: MegaSaM 模型不存在: checkpoints/megasam_final.pth"
    exit 1
fi

if [ ! -f "Depth-Anything/checkpoints/depth_anything_vitl14.pth" ]; then
    echo "错误: Depth-Anything 模型不存在"
    echo "请下载: https://huggingface.co/spaces/LiheYoung/Depth-Anything/resolve/main/checkpoints/depth_anything_vitl14.pth"
    echo "保存到: Depth-Anything/checkpoints/depth_anything_vitl14.pth"
    exit 1
fi

if [ ! -f "cvd_opt/raft-things.pth" ]; then
    echo "警告: RAFT 模型不存在: cvd_opt/raft-things.pth"
    echo "步骤 3 (CVD 优化) 将无法运行"
    echo "请从 https://drive.google.com/drive/folders/1sWDsfuZ3Up38EUQt7-JDTT1HcGHuJgvT 下载"
    SKIP_CVD=true
else
    SKIP_CVD=false
fi

if [ ! -d "$DATA_DIR" ]; then
    echo "错误: 数据目录不存在: $DATA_DIR"
    echo "请创建目录并放入图像序列（.jpg 或 .png 格式）"
    exit 1
fi

# 检查图像文件
NUM_IMAGES=$(find "$DATA_DIR" -maxdepth 1 \( -name "*.jpg" -o -name "*.png" \) | wc -l)
if [ "$NUM_IMAGES" -eq 0 ]; then
    echo "错误: 在 $DATA_DIR 中没有找到图像文件"
    exit 1
fi

echo "找到 $NUM_IMAGES 张图像"

# ============ 步骤 1: 预计算单目深度 ============
echo ""
echo "=========================================="
echo "步骤 1/3: 预计算单目深度"
echo "=========================================="

# 运行 Depth-Anything
echo "运行 Depth-Anything..."
CUDA_VISIBLE_DEVICES=$GPU_ID python Depth-Anything/run_videos.py \
  --encoder vitl \
  --load-from Depth-Anything/checkpoints/depth_anything_vitl14.pth \
  --img-path "$DATA_DIR" \
  --outdir "Depth-Anything/video_visualization/$SCENE_NAME"

echo "Depth-Anything 完成！"

# 运行 UniDepth
echo "运行 UniDepth..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)/UniDepth"
CUDA_VISIBLE_DEVICES=$GPU_ID python UniDepth/scripts/demo_mega-sam.py \
  --scene-name "$SCENE_NAME" \
  --img-path "$DATA_DIR" \
  --outdir "UniDepth/outputs"

echo "UniDepth 完成！"

# ============ 步骤 2: 相机跟踪 ============
echo ""
echo "=========================================="
echo "步骤 2/3: 相机跟踪"
echo "=========================================="

# 构建参数
TRACKING_ARGS="--datapath=$DATA_DIR \
  --weights=checkpoints/megasam_final.pth \
  --scene_name $SCENE_NAME \
  --buffer 2048 \
  --mono_depth_path $(pwd)/Depth-Anything/video_visualization \
  --metric_depth_path $(pwd)/UniDepth/outputs"

if [ "$DISABLE_VIS" = true ]; then
    TRACKING_ARGS="$TRACKING_ARGS --disable_vis"
fi

if [ "$OPT_FOCAL" = true ]; then
    TRACKING_ARGS="$TRACKING_ARGS --opt_focal"
fi

echo "运行相机跟踪..."
CUDA_VISIBLE_DEVICES=$GPU_ID python camera_tracking_scripts/test_demo.py $TRACKING_ARGS

echo "相机跟踪完成！"
echo "输出保存在:"
echo "  - reconstructions/$SCENE_NAME/"
echo "  - outputs/${SCENE_NAME}_droid.npz"

# ============ 步骤 3: 一致性视频深度优化 ============
if [ "$SKIP_CVD" = false ]; then
    echo ""
    echo "=========================================="
    echo "步骤 3/3: 一致性视频深度优化"
    echo "=========================================="

    # 预处理光流
    echo "预处理光流..."
    CUDA_VISIBLE_DEVICES=$GPU_ID python cvd_opt/preprocess_flow.py \
      --datapath="$DATA_DIR" \
      --model=cvd_opt/raft-things.pth \
      --scene_name "$SCENE_NAME" \
      --mixed_precision

    echo "光流预处理完成！"

    # 运行 CVD 优化
    echo "运行 CVD 优化..."
    CUDA_VISIBLE_DEVICES=$GPU_ID python cvd_opt/cvd_opt.py \
      --scene_name "$SCENE_NAME" \
      --w_grad 2.0 \
      --w_normal 5.0

    echo "CVD 优化完成！"
else
    echo ""
    echo "=========================================="
    echo "跳过步骤 3: CVD 优化（RAFT 模型缺失）"
    echo "=========================================="
fi

# ============ 完成 ============
echo ""
echo "=========================================="
echo "处理完成！"
echo "=========================================="
echo ""
echo "输出文件:"
echo "  1. 相机轨迹和深度: outputs/${SCENE_NAME}_droid.npz"
echo "  2. 重建数据: reconstructions/$SCENE_NAME/"
if [ "$SKIP_CVD" = false ]; then
    echo "  3. 优化后的深度: (CVD 输出目录)"
fi
echo ""
echo "你可以使用 Python 加载结果:"
echo "  import numpy as np"
echo "  data = np.load('outputs/${SCENE_NAME}_droid.npz')"
echo "  images = data['images']"
echo "  depths = data['depths']"
echo "  cam_c2w = data['cam_c2w']"
echo ""
