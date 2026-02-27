#!/bin/bash
# 从视频文件提取帧的辅助脚本

set -e

# 使用方法
if [ "$#" -lt 2 ]; then
    echo "使用方法: $0 <视频文件路径> <输出目录名称> [帧率]"
    echo ""
    echo "示例:"
    echo "  $0 my_video.mp4 my_video 30"
    echo "  $0 /path/to/video.mp4 scene1"
    echo ""
    echo "参数:"
    echo "  视频文件路径: 输入视频文件（.mp4, .avi, .mov 等）"
    echo "  输出目录名称: 输出目录名称（将创建在 data/ 下）"
    echo "  帧率: 可选，每秒提取的帧数（默认: 30）"
    exit 1
fi

VIDEO_PATH="$1"
OUTPUT_NAME="$2"
FPS="${3:-30}"  # 默认 30 fps

OUTPUT_DIR="data/$OUTPUT_NAME"

# 检查视频文件是否存在
if [ ! -f "$VIDEO_PATH" ]; then
    echo "错误: 视频文件不存在: $VIDEO_PATH"
    exit 1
fi

# 检查 ffmpeg 是否安装
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: 未找到 ffmpeg"
    echo "请安装 ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "从视频提取帧"
echo "=========================================="
echo "输入视频: $VIDEO_PATH"
echo "输出目录: $OUTPUT_DIR"
echo "帧率: $FPS fps"
echo ""

# 获取视频信息
echo "视频信息:"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,duration -of default=noprint_wrappers=1 "$VIDEO_PATH"
echo ""

# 提取帧
echo "正在提取帧..."
ffmpeg -i "$VIDEO_PATH" -r "$FPS" -qscale:v 2 "$OUTPUT_DIR/%05d.jpg" -y

# 统计提取的帧数
NUM_FRAMES=$(ls "$OUTPUT_DIR"/*.jpg 2>/dev/null | wc -l)

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
echo "提取了 $NUM_FRAMES 帧"
echo "保存在: $OUTPUT_DIR"
echo ""
echo "下一步: 运行 MegaSaM"
echo "  1. 编辑 run_custom_video.sh，设置:"
echo "     SCENE_NAME=\"$OUTPUT_NAME\""
echo "     DATA_DIR=\"$OUTPUT_DIR\""
echo "  2. 运行: ./run_custom_video.sh"
echo ""
