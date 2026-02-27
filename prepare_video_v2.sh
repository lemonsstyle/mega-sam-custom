#!/bin/bash
# 改进版：支持自定义输出路径的视频帧提取脚本

set -e

# ============ 使用说明 ============
show_usage() {
    cat << EOF
使用方法: $0 <视频文件> [选项]

必需参数:
  视频文件                   输入视频文件路径

可选参数:
  --output-dir PATH          输出目录（默认: data/<视频文件名>）
  --fps FPS                  提取帧率（默认: 30）
  --quality QUALITY          JPEG质量 1-31，越小越好（默认: 2）
  --start-time TIME          开始时间，格式 HH:MM:SS 或秒数（默认: 开头）
  --duration TIME            持续时间，格式 HH:MM:SS 或秒数（默认: 全部）

示例:
  # 基本用法（输出到 data/my_video/）
  $0 my_video.mp4

  # 指定输出目录和帧率
  $0 video.mp4 --output-dir /path/to/output --fps 15

  # 提取视频片段（从10秒开始，持续30秒）
  $0 video.mp4 --start-time 10 --duration 30 --output-dir data/clip1

  # 高质量提取
  $0 video.mp4 --quality 1 --fps 60

EOF
    exit 1
}

# ============ 默认参数 ============
VIDEO_PATH=""
OUTPUT_DIR=""
FPS=30
QUALITY=2
START_TIME=""
DURATION=""

# ============ 解析命令行参数 ============
if [ $# -eq 0 ]; then
    show_usage
fi

# 先检查是否是帮助请求
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
fi

VIDEO_PATH="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --fps)
            FPS="$2"
            shift 2
            ;;
        --quality)
            QUALITY="$2"
            shift 2
            ;;
        --start-time)
            START_TIME="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
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

# ============ 验证参数 ============
if [ -z "$VIDEO_PATH" ]; then
    echo "错误: 必须指定视频文件"
    show_usage
fi

if [ ! -f "$VIDEO_PATH" ]; then
    echo "错误: 视频文件不存在: $VIDEO_PATH"
    exit 1
fi

# 如果没有指定输出目录，使用视频文件名
if [ -z "$OUTPUT_DIR" ]; then
    VIDEO_BASENAME=$(basename "$VIDEO_PATH")
    VIDEO_NAME="${VIDEO_BASENAME%.*}"
    OUTPUT_DIR="data/$VIDEO_NAME"
fi

# 检查 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: 未找到 ffmpeg"
    echo "请安装: sudo apt-get install ffmpeg"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "已创建输出目录: $OUTPUT_DIR"

# ============ 显示配置 ============
echo "=========================================="
echo "从视频提取帧"
echo "=========================================="
echo "输入视频: $VIDEO_PATH"
echo "输出目录: $OUTPUT_DIR"
echo "帧率: $FPS fps"
echo "质量: $QUALITY"
if [ -n "$START_TIME" ]; then
    echo "开始时间: $START_TIME"
fi
if [ -n "$DURATION" ]; then
    echo "持续时间: $DURATION"
fi
echo ""

# ============ 获取视频信息 ============
echo "视频信息:"
ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate,duration \
    -of default=noprint_wrappers=1 "$VIDEO_PATH"
echo ""

# ============ 构建 ffmpeg 命令 ============
FFMPEG_CMD="ffmpeg -i \"$VIDEO_PATH\""

if [ -n "$START_TIME" ]; then
    FFMPEG_CMD="$FFMPEG_CMD -ss $START_TIME"
fi

if [ -n "$DURATION" ]; then
    FFMPEG_CMD="$FFMPEG_CMD -t $DURATION"
fi

FFMPEG_CMD="$FFMPEG_CMD -r $FPS -qscale:v $QUALITY \"$OUTPUT_DIR/%05d.jpg\" -y"

# ============ 提取帧 ============
echo "正在提取帧..."
echo "命令: $FFMPEG_CMD"
echo ""

eval $FFMPEG_CMD

# ============ 统计结果 ============
NUM_FRAMES=$(find "$OUTPUT_DIR" -maxdepth 1 -name "*.jpg" | wc -l)

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
echo "提取了 $NUM_FRAMES 帧"
echo "保存在: $OUTPUT_DIR"
echo ""
echo "下一步: 运行 MegaSaM"
# 移除OUTPUT_DIR末尾的斜杠
OUTPUT_DIR_CLEAN="${OUTPUT_DIR%/}"
echo "  ./run_custom_video_v2.sh \\"
echo "    --scene-name $(basename $OUTPUT_DIR_CLEAN) \\"
echo "    --data-dir $OUTPUT_DIR_CLEAN \\"
echo "    --output-dir $OUTPUT_DIR_CLEAN/outputs \\"
echo "    --recon-dir $OUTPUT_DIR_CLEAN/reconstructions"
echo ""
