#!/bin/bash
# 改进版：所有路径可配置的 MegaSaM 运行脚本

set -e

# ============ 使用说明 ============
show_usage() {
    cat << EOF
使用方法: $0 [选项]

必需参数:
  --scene-name NAME          场景名称（用于输出文件命名）
  --data-dir PATH            输入图像序列目录

可选参数:
  --output-dir PATH          输出目录（默认: outputs）
  --recon-dir PATH           重建数据目录（默认: reconstructions）
  --cvd-output-dir PATH      CVD优化输出目录（默认: 自动设置为output-dir同级的outputs_cvd）
  --depth-anything-dir PATH  Depth-Anything输出目录（默认: Depth-Anything/video_visualization）
  --unidepth-dir PATH        UniDepth输出目录（默认: UniDepth/outputs）
  --gpu-id ID                GPU设备ID（默认: 0）
  --opt-focal                启用焦距优化
  --disable-vis              禁用可视化
  --skip-depth               跳过深度预计算（如果已运行过）
  --skip-tracking            跳过相机跟踪（如果已运行过）
  --skip-cvd                 跳过CVD优化

示例:
  # 基本用法
  $0 --scene-name my_video --data-dir data/my_scene

  # 自定义输出路径
  $0 --scene-name video1 --data-dir /path/to/images \\
     --output-dir /path/to/outputs --recon-dir /path/to/recons

  # 跳过已完成的步骤
  $0 --scene-name my_video --data-dir data/my_scene --skip-depth

EOF
    exit 1
}

# ============ 默认参数 ============
SCENE_NAME=""
DATA_DIR=""
OUTPUT_DIR="outputs"
RECON_DIR="reconstructions"
DEPTH_ANYTHING_DIR="Depth-Anything/video_visualization"
UNIDEPTH_DIR="UniDepth/outputs"
CVD_OUTPUT_DIR=""  # CVD优化输出目录，默认为空，后面会自动设置
GPU_ID=0
OPT_FOCAL=true
DISABLE_VIS=true
SKIP_DEPTH=false
SKIP_TRACKING=false
SKIP_CVD=false

# ============ 解析命令行参数 ============
while [[ $# -gt 0 ]]; do
    case $1 in
        --scene-name)
            SCENE_NAME="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --recon-dir)
            RECON_DIR="$2"
            shift 2
            ;;
        --depth-anything-dir)
            DEPTH_ANYTHING_DIR="$2"
            shift 2
            ;;
        --unidepth-dir)
            UNIDEPTH_DIR="$2"
            shift 2
            ;;
        --cvd-output-dir)
            CVD_OUTPUT_DIR="$2"
            shift 2
            ;;
        --gpu-id)
            GPU_ID="$2"
            shift 2
            ;;
        --opt-focal)
            OPT_FOCAL=true
            shift
            ;;
        --no-opt-focal)
            OPT_FOCAL=false
            shift
            ;;
        --disable-vis)
            DISABLE_VIS=true
            shift
            ;;
        --skip-depth)
            SKIP_DEPTH=true
            shift
            ;;
        --skip-tracking)
            SKIP_TRACKING=true
            shift
            ;;
        --skip-cvd)
            SKIP_CVD=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "未知参数: $1"
            show_usage
            ;;
    esac
done

# ============ 验证必需参数 ============
if [ -z "$SCENE_NAME" ]; then
    echo "错误: 必须指定 --scene-name"
    show_usage
fi

if [ -z "$DATA_DIR" ]; then
    echo "错误: 必须指定 --data-dir"
    show_usage
fi

# 如果没有指定CVD输出目录，自动设置为output-dir同级的outputs_cvd
if [ -z "$CVD_OUTPUT_DIR" ]; then
    # 获取OUTPUT_DIR的父目录
    OUTPUT_PARENT=$(dirname "$OUTPUT_DIR")
    if [ "$OUTPUT_PARENT" = "." ]; then
        CVD_OUTPUT_DIR="outputs_cvd"
    else
        CVD_OUTPUT_DIR="$OUTPUT_PARENT/outputs_cvd"
    fi
fi

# ============ 显示配置 ============
echo "=========================================="
echo "MegaSaM 处理配置"
echo "=========================================="
echo "场景名称: $SCENE_NAME"
echo "输入目录: $DATA_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "重建目录: $RECON_DIR"
echo "CVD输出目录: $CVD_OUTPUT_DIR"
echo "GPU ID: $GPU_ID"
echo "焦距优化: $OPT_FOCAL"
echo "禁用可视化: $DISABLE_VIS"
echo ""

# ============ 检查必需文件 ============
echo "检查必需的模型文件..."

if [ ! -f "checkpoints/megasam_final.pth" ]; then
    echo "错误: MegaSaM 模型不存在: checkpoints/megasam_final.pth"
    exit 1
fi

if [ "$SKIP_DEPTH" = false ]; then
    if [ ! -f "Depth-Anything/checkpoints/depth_anything_vitl14.pth" ]; then
        echo "错误: Depth-Anything 模型不存在"
        exit 1
    fi
fi

if [ "$SKIP_CVD" = false ] && [ ! -f "cvd_opt/raft-things.pth" ]; then
    echo "警告: RAFT 模型不存在，将跳过 CVD 优化"
    SKIP_CVD=true
fi

if [ ! -d "$DATA_DIR" ]; then
    echo "错误: 数据目录不存在: $DATA_DIR"
    exit 1
fi

# 检查图像文件
NUM_IMAGES=$(find "$DATA_DIR" -maxdepth 1 \( -name "*.jpg" -o -name "*.png" \) | wc -l)
if [ "$NUM_IMAGES" -eq 0 ]; then
    echo "错误: 在 $DATA_DIR 中没有找到图像文件"
    exit 1
fi

echo "找到 $NUM_IMAGES 张图像"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"
mkdir -p "$RECON_DIR"
mkdir -p "$DEPTH_ANYTHING_DIR"
mkdir -p "$UNIDEPTH_DIR"
mkdir -p "$CVD_OUTPUT_DIR"

echo "已创建输出目录:"
echo "  - $OUTPUT_DIR"
echo "  - $RECON_DIR"
echo "  - $CVD_OUTPUT_DIR"
echo "  - $DEPTH_ANYTHING_DIR"
echo "  - $UNIDEPTH_DIR"
echo ""

# ============ 步骤 1: 预计算单目深度 ============
if [ "$SKIP_DEPTH" = false ]; then
    echo ""
    echo "=========================================="
    echo "步骤 1/3: 预计算单目深度"
    echo "=========================================="

    # Depth-Anything
    echo "运行 Depth-Anything..."
    CUDA_VISIBLE_DEVICES=$GPU_ID python Depth-Anything/run_videos.py \
      --encoder vitl \
      --load-from Depth-Anything/checkpoints/depth_anything_vitl14.pth \
      --img-path "$DATA_DIR" \
      --outdir "$DEPTH_ANYTHING_DIR/$SCENE_NAME"

    echo "Depth-Anything 完成！"

    # UniDepth
    echo "运行 UniDepth..."
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/UniDepth"
    CUDA_VISIBLE_DEVICES=$GPU_ID python UniDepth/scripts/demo_mega-sam.py \
      --scene-name "$SCENE_NAME" \
      --img-path "$DATA_DIR" \
      --outdir "$UNIDEPTH_DIR"

    echo "UniDepth 完成！"
else
    echo ""
    echo "=========================================="
    echo "跳过步骤 1: 深度预计算"
    echo "=========================================="
fi

# ============ 步骤 2: 相机跟踪 ============
if [ "$SKIP_TRACKING" = false ]; then
    echo ""
    echo "=========================================="
    echo "步骤 2/3: 相机跟踪"
    echo "=========================================="

    TRACKING_ARGS="--datapath=$DATA_DIR \
      --weights=checkpoints/megasam_final.pth \
      --scene_name $SCENE_NAME \
      --buffer 2048 \
      --mono_depth_path $(pwd)/$DEPTH_ANYTHING_DIR \
      --metric_depth_path $(pwd)/$UNIDEPTH_DIR \
      --output_dir $OUTPUT_DIR \
      --recon_dir $RECON_DIR"

    if [ "$DISABLE_VIS" = true ]; then
        TRACKING_ARGS="$TRACKING_ARGS --disable_vis"
    fi

    if [ "$OPT_FOCAL" = false ]; then
        TRACKING_ARGS="$TRACKING_ARGS --no_opt_focal"
    fi

    echo "运行相机跟踪..."
    CUDA_VISIBLE_DEVICES=$GPU_ID python camera_tracking_scripts/test_demo_v2.py $TRACKING_ARGS

    echo "相机跟踪完成！"
    echo "输出保存在:"
    echo "  - $RECON_DIR/$SCENE_NAME/"
    echo "  - $OUTPUT_DIR/${SCENE_NAME}_droid.npz"
else
    echo ""
    echo "=========================================="
    echo "跳过步骤 2: 相机跟踪"
    echo "=========================================="
fi

# ============ 步骤 3: CVD 优化 ============
if [ "$SKIP_CVD" = false ]; then
    echo ""
    echo "=========================================="
    echo "步骤 3/3: 一致性视频深度优化"
    echo "=========================================="

    # 预处理光流
    echo "预处理光流..."
    CUDA_VISIBLE_DEVICES=$GPU_ID python cvd_opt/preprocess_flow_v2.py \
      --datapath="$DATA_DIR" \
      --model=cvd_opt/raft-things.pth \
      --scene_name "$SCENE_NAME" \
      --mixed_precision

    echo "光流预处理完成！"

    # CVD 优化
    echo "运行 CVD 优化..."
    CUDA_VISIBLE_DEVICES=$GPU_ID python cvd_opt/cvd_opt_v2.py \
      --scene_name "$SCENE_NAME" \
      --recon_dir "$RECON_DIR" \
      --output_dir "$CVD_OUTPUT_DIR" \
      --w_grad 2.0 \
      --w_normal 5.0

    echo "CVD 优化完成！"
else
    echo ""
    echo "=========================================="
    echo "跳过步骤 3: CVD 优化"
    echo "=========================================="
fi

# ============ 完成 ============
echo ""
echo "=========================================="
echo "处理完成！"
echo "=========================================="
echo ""
echo "输出文件:"
echo "  1. 相机轨迹: $OUTPUT_DIR/${SCENE_NAME}_droid.npz"
echo "  2. 重建数据: $RECON_DIR/$SCENE_NAME/"
if [ "$SKIP_CVD" = false ]; then
    echo "  3. 优化深度: $CVD_OUTPUT_DIR/${SCENE_NAME}_sgd_cvd_hr.npz"
fi
echo ""
