#!/usr/bin/env python3
"""
可视化MEGA-SAM重建结果
生成可在无图形界面服务器上查看的HTML文件
"""

import numpy as np
import base64
from io import BytesIO
from PIL import Image
import json
import os
import sys
import matplotlib.cm as cm

def numpy_to_base64(arr, format='PNG'):
    """将numpy数组转换为base64编码的图片"""
    if arr.dtype == np.float32 or arr.dtype == np.float64:
        arr = (arr * 255).clip(0, 255).astype(np.uint8)

    img = Image.fromarray(arr)
    buffer = BytesIO()
    img.save(buffer, format=format)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/{format.lower()};base64,{img_str}"

def depth_to_colormap(depth, vmin=None, vmax=None):
    """将深度图转换为彩色图（使用matplotlib turbo colormap）"""
    if vmin is None:
        vmin = np.percentile(depth, 5)
    if vmax is None:
        vmax = np.percentile(depth, 95)

    depth_normalized = (depth - vmin) / (vmax - vmin + 1e-8)
    depth_normalized = np.clip(depth_normalized, 0, 1)

    colored = cm.turbo(depth_normalized)  # (H, W, 4) float [0,1]
    return (colored[:, :, :3] * 255).astype(np.uint8)

def generate_html(scene_name, output_path='visualization.html', cvd_dir=None, recon_dir=None, max_frames=50):
    """生成HTML可视化文件"""

    # 加载数据
    _recon_base = recon_dir or '../reconstructions'
    _cvd_base = cvd_dir or '../outputs_cvd'
    recon_dir = f'{_recon_base}/{scene_name}'
    cvd_path = f'{_cvd_base}/{scene_name}_sgd_cvd_hr.npz'

    # 优先用 outputs_cvd（图像和深度来自同一文件，天然对齐）
    if os.path.exists(cvd_path):
        print(f"加载数据从: {cvd_path}")
        cvd = np.load(cvd_path)
        images = cvd['images']   # (N, H, W, 3)
        depths = cvd['depths'].astype(np.float32)  # (N, H, W)
        poses_4x4 = cvd['cam_c2w']  # (N, 4, 4)
        use_cvd = True
    else:
        print(f"加载数据从: {recon_dir}")
        images = np.load(f'{recon_dir}/images.npy').transpose(0, 2, 3, 1)  # (N, H, W, 3)
        disps = np.load(f'{recon_dir}/disps.npy')
        depths = 1.0 / (disps + 1e-8)
        poses_4x4 = None
        use_cvd = False

    # poses 用 reconstructions 里的（含四元数）
    poses = np.load(f'{recon_dir}/poses.npy')  # (N, 7)

    N, H, W, _ = images.shape
    print(f"帧数: {N}, 分辨率: {H}x{W}")

    # 准备数据
    frames_data = []

    # 采样帧（如果帧数太多，采样以减少HTML大小）
    step = max(1, N // max_frames)  # 根据max_frames参数采样

    # 如果想看所有帧，取消下面这行的注释（会生成很大的HTML文件）
    # step = 1  # 不采样，使用所有帧

    indices = list(range(0, N, step))

    print(f"处理 {len(indices)} 帧...")

    for idx in indices:
        # 图像: (H, W, 3)
        img = images[idx]

        # 深度图
        depth_colored = depth_to_colormap(depths[idx])

        # 转换为base64
        img_b64 = numpy_to_base64(img)
        depth_b64 = numpy_to_base64(depth_colored)

        # 位姿信息
        pose = poses[idx]
        position = pose[:3].tolist()
        quaternion = pose[3:].tolist()

        frames_data.append({
            'index': int(idx),
            'image': img_b64,
            'depth': depth_b64,
            'position': position,
            'quaternion': quaternion
        })

        if (len(frames_data)) % 10 == 0:
            print(f"  已处理 {len(frames_data)} 帧")

    # 相机轨迹数据
    trajectory = poses[:, :3].tolist()

    # 生成HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEGA-SAM 重建结果 - {scene_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        h1 {{
            text-align: center;
            color: #4CAF50;
            margin-bottom: 10px;
            font-size: 2em;
        }}

        .info {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}

        .controls {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }}

        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }}

        button:hover {{
            background: #45a049;
        }}

        button:disabled {{
            background: #555;
            cursor: not-allowed;
        }}

        input[type="range"] {{
            flex: 1;
            min-width: 200px;
        }}

        .frame-info {{
            color: #4CAF50;
            font-weight: bold;
        }}

        .viewer {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}

        .view-panel {{
            background: #2a2a2a;
            border-radius: 10px;
            padding: 15px;
        }}

        .view-panel h2 {{
            color: #4CAF50;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}

        .image-container {{
            position: relative;
            width: 100%;
            background: #000;
            border-radius: 5px;
            overflow: hidden;
        }}

        .image-container img {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .trajectory-panel {{
            background: #2a2a2a;
            border-radius: 10px;
            padding: 15px;
        }}

        .trajectory-panel h2 {{
            color: #4CAF50;
            margin-bottom: 10px;
        }}

        #trajectoryCanvas {{
            width: 100%;
            height: 400px;
            background: #1a1a1a;
            border-radius: 5px;
        }}

        .pose-info {{
            background: #2a2a2a;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
        }}

        .pose-info h3 {{
            color: #4CAF50;
            margin-bottom: 10px;
        }}

        .pose-data {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
        }}

        @media (max-width: 768px) {{
            .viewer {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 MEGA-SAM 重建结果</h1>
        <div class="info">
            场景: {scene_name} | 总帧数: {N} | 分辨率: {H}x{W}
        </div>

        <div class="controls">
            <div class="control-group">
                <button id="playBtn">▶ 播放</button>
                <button id="prevBtn">⏮ 上一帧</button>
                <button id="nextBtn">下一帧 ⏭</button>
            </div>

            <div class="control-group" style="flex: 1;">
                <span class="frame-info" id="frameInfo">帧 0 / {len(indices)-1}</span>
                <input type="range" id="frameSlider" min="0" max="{len(indices)-1}" value="0" step="1">
            </div>

            <div class="control-group">
                <label>速度:</label>
                <input type="range" id="speedSlider" min="1" max="10" value="5" step="1">
                <span id="speedInfo">5x</span>
            </div>
        </div>

        <div class="viewer">
            <div class="view-panel">
                <h2>📷 RGB 图像</h2>
                <div class="image-container">
                    <img id="rgbImage" src="" alt="RGB Image">
                </div>
            </div>

            <div class="view-panel">
                <h2>🌊 深度图</h2>
                <div class="image-container">
                    <img id="depthImage" src="" alt="Depth Map">
                </div>
            </div>
        </div>

        <div class="trajectory-panel">
            <h2>📍 相机轨迹 (俯视图)</h2>
            <canvas id="trajectoryCanvas"></canvas>
        </div>

        <div class="pose-info">
            <h3>📊 当前帧位姿信息</h3>
            <div class="pose-data" id="poseData"></div>
        </div>
    </div>

    <script>
        // 数据
        const framesData = {json.dumps(frames_data)};
        const trajectory = {json.dumps(trajectory)};

        // 状态
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        let playSpeed = 5;

        // 元素
        const rgbImage = document.getElementById('rgbImage');
        const depthImage = document.getElementById('depthImage');
        const frameSlider = document.getElementById('frameSlider');
        const frameInfo = document.getElementById('frameInfo');
        const playBtn = document.getElementById('playBtn');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const speedSlider = document.getElementById('speedSlider');
        const speedInfo = document.getElementById('speedInfo');
        const poseData = document.getElementById('poseData');
        const trajectoryCanvas = document.getElementById('trajectoryCanvas');

        // 更新显示
        function updateFrame(index) {{
            currentFrame = index;
            const frame = framesData[index];

            rgbImage.src = frame.image;
            depthImage.src = frame.depth;
            frameSlider.value = index;
            frameInfo.textContent = `帧 ${{index}} / ${{framesData.length - 1}} (原始索引: ${{frame.index}})`;

            // 更新位姿信息
            const pos = frame.position;
            const quat = frame.quaternion;
            poseData.innerHTML = `
                <strong>位置 (x, y, z):</strong><br>
                &nbsp;&nbsp;[${{pos[0].toFixed(4)}}, ${{pos[1].toFixed(4)}}, ${{pos[2].toFixed(4)}}]<br><br>
                <strong>四元数 (qx, qy, qz, qw):</strong><br>
                &nbsp;&nbsp;[${{quat[0].toFixed(4)}}, ${{quat[1].toFixed(4)}}, ${{quat[2].toFixed(4)}}, ${{quat[3].toFixed(4)}}]
            `;

            drawTrajectory(index);
        }}

        // 绘制轨迹
        function drawTrajectory(currentIndex) {{
            const canvas = trajectoryCanvas;
            const ctx = canvas.getContext('2d');

            // 设置canvas大小
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;

            // 计算轨迹范围
            const xs = trajectory.map(p => p[0]);
            const zs = trajectory.map(p => p[2]);
            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            const minZ = Math.min(...zs);
            const maxZ = Math.max(...zs);

            const rangeX = maxX - minX || 1;
            const rangeZ = maxZ - minZ || 1;
            const padding = 40;

            // 坐标转换
            function toCanvas(x, z) {{
                const cx = padding + (x - minX) / rangeX * (canvas.width - 2 * padding);
                const cy = padding + (z - minZ) / rangeZ * (canvas.height - 2 * padding);
                return [cx, cy];
            }}

            // 清空画布
            ctx.fillStyle = '#1a1a1a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 绘制轨迹线
            ctx.strokeStyle = '#4CAF50';
            ctx.lineWidth = 2;
            ctx.beginPath();

            for (let i = 0; i < trajectory.length; i++) {{
                const [cx, cy] = toCanvas(trajectory[i][0], trajectory[i][2]);
                if (i === 0) {{
                    ctx.moveTo(cx, cy);
                }} else {{
                    ctx.lineTo(cx, cy);
                }}
            }}
            ctx.stroke();

            // 绘制所有点
            ctx.fillStyle = '#666';
            for (let i = 0; i < trajectory.length; i++) {{
                const [cx, cy] = toCanvas(trajectory[i][0], trajectory[i][2]);
                ctx.beginPath();
                ctx.arc(cx, cy, 2, 0, 2 * Math.PI);
                ctx.fill();
            }}

            // 绘制当前位置
            const currentPos = framesData[currentIndex].position;
            const [cx, cy] = toCanvas(currentPos[0], currentPos[2]);

            ctx.fillStyle = '#FF5722';
            ctx.beginPath();
            ctx.arc(cx, cy, 6, 0, 2 * Math.PI);
            ctx.fill();

            // 绘制起点
            const [sx, sy] = toCanvas(trajectory[0][0], trajectory[0][2]);
            ctx.fillStyle = '#2196F3';
            ctx.beginPath();
            ctx.arc(sx, sy, 5, 0, 2 * Math.PI);
            ctx.fill();

            // 标签
            ctx.fillStyle = '#e0e0e0';
            ctx.font = '12px Arial';
            ctx.fillText('起点', sx + 10, sy);
            ctx.fillText('当前', cx + 10, cy);
        }}

        // 播放控制
        function play() {{
            if (isPlaying) return;
            isPlaying = true;
            playBtn.textContent = '⏸ 暂停';

            playInterval = setInterval(() => {{
                if (currentFrame < framesData.length - 1) {{
                    updateFrame(currentFrame + 1);
                }} else {{
                    pause();
                }}
            }}, 1000 / playSpeed);
        }}

        function pause() {{
            isPlaying = false;
            playBtn.textContent = '▶ 播放';
            if (playInterval) {{
                clearInterval(playInterval);
                playInterval = null;
            }}
        }}

        // 事件监听
        playBtn.addEventListener('click', () => {{
            if (isPlaying) {{
                pause();
            }} else {{
                play();
            }}
        }});

        prevBtn.addEventListener('click', () => {{
            if (currentFrame > 0) {{
                updateFrame(currentFrame - 1);
            }}
        }});

        nextBtn.addEventListener('click', () => {{
            if (currentFrame < framesData.length - 1) {{
                updateFrame(currentFrame + 1);
            }}
        }});

        frameSlider.addEventListener('input', (e) => {{
            updateFrame(parseInt(e.target.value));
        }});

        speedSlider.addEventListener('input', (e) => {{
            playSpeed = parseInt(e.target.value);
            speedInfo.textContent = playSpeed + 'x';

            if (isPlaying) {{
                pause();
                play();
            }}
        }});

        // 键盘控制
        document.addEventListener('keydown', (e) => {{
            if (e.key === ' ') {{
                e.preventDefault();
                if (isPlaying) pause(); else play();
            }} else if (e.key === 'ArrowLeft') {{
                e.preventDefault();
                if (currentFrame > 0) updateFrame(currentFrame - 1);
            }} else if (e.key === 'ArrowRight') {{
                e.preventDefault();
                if (currentFrame < framesData.length - 1) updateFrame(currentFrame + 1);
            }}
        }});

        // 初始化
        updateFrame(0);

        // 窗口大小改变时重绘轨迹
        window.addEventListener('resize', () => {{
            drawTrajectory(currentFrame);
        }});
    </script>
</body>
</html>
"""

    # 保存HTML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ 可视化文件已生成: {output_path}")
    print(f"📊 包含 {len(frames_data)} 帧数据")
    print(f"📁 文件大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='可视化MEGA-SAM重建结果')
    parser.add_argument('scene_name', help='场景名称')
    parser.add_argument('--output', default=None, help='输出HTML文件路径（默认: <scene_name>_visualization.html）')
    parser.add_argument('--cvd-dir', default=None, help='outputs_cvd目录路径（默认: ../outputs_cvd）')
    parser.add_argument('--recon-dir', default=None, help='reconstructions目录路径（默认: ../reconstructions）')
    parser.add_argument('--max-frames', type=int, default=50, help='最大帧数（默认: 50，设为0表示使用所有帧）')
    args = parser.parse_args()

    scene_name = args.scene_name
    output_path = args.output or f'{scene_name}_visualization.html'
    max_frames = args.max_frames if args.max_frames > 0 else 999999  # 0表示不限制

    generate_html(scene_name, output_path,
                  cvd_dir=args.cvd_dir,
                  recon_dir=args.recon_dir,
                  max_frames=max_frames)
