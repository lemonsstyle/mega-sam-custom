#!/usr/bin/env python3
"""
3D点云可视化服务器
使用Three.js创建可交互的点云场景
"""

import numpy as np
import json
import sys
import os
from flask import Flask, render_template_string, jsonify, send_from_directory

app = Flask(__name__)
VISUAL_DIR = '/root/mega-sam-main/visual'

# 全局变量存储点云数据
pointcloud_data = None
camera_poses = None
scene_name = None

def load_pointcloud(scene_name, max_points=100000, sample_frames=10, cvd_dir=None):
    """从重建结果生成点云"""
    _cvd_base = cvd_dir or '../outputs_cvd'
    cvd_path = f'{_cvd_base}/{scene_name}_sgd_cvd_hr.npz'

    if not os.path.exists(cvd_path):
        print(f"错误: 找不到 {cvd_path}")
        return None, None

    print(f"加载数据: {cvd_path}")
    cvd = np.load(cvd_path)

    images = cvd['images']  # (N, H, W, 3)
    depths = cvd['depths'].astype(np.float32)  # (N, H, W)
    intrinsic = cvd['intrinsic']  # (3, 3)
    cam_c2w = cvd['cam_c2w']  # (N, 4, 4)

    N, H, W, _ = images.shape
    print(f"总帧数: {N}, 分辨率: {H}x{W}")

    # 采样帧
    step = max(1, N // sample_frames)
    frame_indices = list(range(0, N, step))
    print(f"采样 {len(frame_indices)} 帧生成点云")

    # 相机内参
    fx, fy = intrinsic[0, 0], intrinsic[1, 1]
    cx, cy = intrinsic[0, 2], intrinsic[1, 2]

    all_points = []
    all_colors = []

    for frame_idx in frame_indices:
        img = images[frame_idx]
        depth = depths[frame_idx]
        c2w = cam_c2w[frame_idx]

        # 下采样像素（减少点数）
        stride = max(1, int(np.sqrt(H * W / (max_points / len(frame_indices)))))

        for v in range(0, H, stride):
            for u in range(0, W, stride):
                d = depth[v, u]

                # 过滤无效深度
                if d <= 0 or d > 10 or np.isnan(d) or np.isinf(d):
                    continue

                # 像素坐标 -> 相机坐标
                x = (u - cx) * d / fx
                y = (v - cy) * d / fy
                z = d

                # 相机坐标 -> 世界坐标
                point_cam = np.array([x, y, z, 1.0])
                point_world = c2w @ point_cam

                all_points.append(point_world[:3])
                all_colors.append(img[v, u] / 255.0)

        if len(all_points) % 10000 == 0:
            print(f"  已处理 {len(all_points)} 个点")

    points = np.array(all_points, dtype=np.float32)
    colors = np.array(all_colors, dtype=np.float32)

    print(f"生成点云: {len(points)} 个点")

    # 相机轨迹
    camera_positions = cam_c2w[:, :3, 3].tolist()

    return {
        'positions': points.tolist(),
        'colors': colors.tolist()
    }, camera_positions

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D点云查看器 - {{ scene_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            overflow: hidden;
        }

        #container {
            width: 100vw;
            height: 100vh;
            position: relative;
        }

        #canvas {
            width: 100%;
            height: 100%;
            display: block;
        }

        #info {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.7);
            padding: 15px 20px;
            border-radius: 10px;
            font-size: 14px;
            line-height: 1.6;
            max-width: 300px;
        }

        #info h2 {
            color: #4CAF50;
            margin-bottom: 10px;
            font-size: 18px;
        }

        #controls {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.7);
            padding: 15px 20px;
            border-radius: 10px;
        }

        .control-group {
            margin-bottom: 10px;
        }

        .control-group:last-child {
            margin-bottom: 0;
        }

        label {
            display: inline-block;
            width: 100px;
            color: #4CAF50;
        }

        input[type="range"] {
            width: 150px;
            vertical-align: middle;
        }

        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 5px;
        }

        button:hover {
            background: #45a049;
        }

        #loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.9);
            padding: 30px 50px;
            border-radius: 10px;
            text-align: center;
            font-size: 18px;
            color: #4CAF50;
        }

        .spinner {
            border: 4px solid #333;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div id="container">
        <canvas id="canvas"></canvas>

        <div id="loading">
            <div>加载点云数据中...</div>
            <div class="spinner"></div>
        </div>

        <div id="info" style="display: none;">
            <h2>🎥 {{ scene_name }}</h2>
            <div>点数: <span id="pointCount">0</span></div>
            <div>相机: <span id="cameraCount">0</span></div>
            <div style="margin-top: 10px; color: #888; font-size: 12px;">
                <strong>控制:</strong><br>
                • 左键拖动: 旋转<br>
                • 右键拖动: 平移<br>
                • 滚轮: 缩放<br>
            </div>
        </div>

        <div id="controls" style="display: none;">
            <div class="control-group">
                <label>点大小:</label>
                <input type="range" id="pointSize" min="0.5" max="5" step="0.1" value="1.5">
                <span id="pointSizeValue">1.5</span>
            </div>
            <div class="control-group">
                <button id="toggleCamera">显示相机</button>
                <button id="resetView">重置视角</button>
            </div>
        </div>
    </div>

    <script src="/js/three.min.js"></script>
    <script src="/js/OrbitControls.js"></script>

    <script>
        let scene, camera, renderer, controls;
        let pointCloud, cameraPath, cameraMarkers;
        let showCameras = true;

        // 初始化场景
        function init() {
            const container = document.getElementById('container');

            // 场景
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a1a);

            // 相机
            camera = new THREE.PerspectiveCamera(
                75,
                window.innerWidth / window.innerHeight,
                0.01,
                1000
            );
            camera.position.set(0, 0, 3);

            // 渲染器
            renderer = new THREE.WebGLRenderer({
                canvas: document.getElementById('canvas'),
                antialias: true
            });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);

            // 控制器
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            // 坐标轴
            const axesHelper = new THREE.AxesHelper(1);
            scene.add(axesHelper);

            // 网格
            const gridHelper = new THREE.GridHelper(10, 10, 0x444444, 0x222222);
            scene.add(gridHelper);

            // 光照
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.4);
            directionalLight.position.set(1, 1, 1);
            scene.add(directionalLight);

            // 窗口大小调整
            window.addEventListener('resize', onWindowResize);

            // 加载数据
            loadData();
        }

        // 加载点云数据
        async function loadData() {
            try {
                const response = await fetch('/api/pointcloud');
                const data = await response.json();

                createPointCloud(data.pointcloud);
                createCameraPath(data.cameras);

                document.getElementById('loading').style.display = 'none';
                document.getElementById('info').style.display = 'block';
                document.getElementById('controls').style.display = 'block';

                document.getElementById('pointCount').textContent = data.pointcloud.positions.length.toLocaleString();
                document.getElementById('cameraCount').textContent = data.cameras.length;

                // 自动调整视角
                fitCameraToScene();

                animate();
            } catch (error) {
                console.error('加载数据失败:', error);
                document.getElementById('loading').innerHTML = '<div style="color: #f44336;">加载失败: ' + error.message + '</div>';
            }
        }

        // 创建点云
        function createPointCloud(data) {
            const positions = new Float32Array(data.positions.flat());
            const colors = new Float32Array(data.colors.flat());

            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

            const material = new THREE.PointsMaterial({
                size: 1.5,
                vertexColors: true,
                sizeAttenuation: true
            });

            pointCloud = new THREE.Points(geometry, material);
            scene.add(pointCloud);
        }

        // 创建相机轨迹
        function createCameraPath(cameras) {
            // 轨迹线
            const points = cameras.map(pos => new THREE.Vector3(pos[0], pos[1], pos[2]));
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const material = new THREE.LineBasicMaterial({ color: 0x00ff00, linewidth: 2 });
            cameraPath = new THREE.Line(geometry, material);
            scene.add(cameraPath);

            // 相机标记
            cameraMarkers = new THREE.Group();
            const markerGeometry = new THREE.SphereGeometry(0.02, 8, 8);
            const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xff5722 });

            cameras.forEach((pos, i) => {
                const marker = new THREE.Mesh(markerGeometry, markerMaterial);
                marker.position.set(pos[0], pos[1], pos[2]);
                cameraMarkers.add(marker);
            });

            scene.add(cameraMarkers);
        }

        // 自动调整视角
        function fitCameraToScene() {
            const box = new THREE.Box3().setFromObject(pointCloud);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            cameraZ *= 1.5;

            camera.position.set(center.x, center.y + maxDim * 0.3, center.z + cameraZ);
            camera.lookAt(center);
            controls.target.copy(center);
            controls.update();
        }

        // 窗口大小调整
        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        // 动画循环
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }

        // 控制事件
        document.getElementById('pointSize').addEventListener('input', (e) => {
            const size = parseFloat(e.target.value);
            pointCloud.material.size = size;
            document.getElementById('pointSizeValue').textContent = size.toFixed(1);
        });

        document.getElementById('toggleCamera').addEventListener('click', () => {
            showCameras = !showCameras;
            cameraPath.visible = showCameras;
            cameraMarkers.visible = showCameras;
            document.getElementById('toggleCamera').textContent = showCameras ? '隐藏相机' : '显示相机';
        });

        document.getElementById('resetView').addEventListener('click', () => {
            fitCameraToScene();
        });

        // 启动
        init();
    </script>
</body>
</html>
"""

@app.route('/js/<path:filename>')
def static_files(filename):
    return send_from_directory(VISUAL_DIR, filename)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, scene_name=scene_name)

@app.route('/api/pointcloud')
def get_pointcloud():
    return jsonify({
        'pointcloud': pointcloud_data,
        'cameras': camera_poses
    })

def main():
    global pointcloud_data, camera_poses, scene_name

    import argparse
    parser = argparse.ArgumentParser(description='3D点云可视化服务器')
    parser.add_argument('scene_name', help='场景名称')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口（默认: 8080）')
    parser.add_argument('--max-points', type=int, default=100000, help='最大点数（默认: 100000）')
    parser.add_argument('--sample-frames', type=int, default=10, help='采样帧数（默认: 10）')
    parser.add_argument('--cvd-dir', default=None, help='outputs_cvd目录路径（默认: ../outputs_cvd）')
    args = parser.parse_args()

    scene_name = args.scene_name
    port = args.port

    print(f"\n{'='*60}")
    print(f"3D点云可视化服务器")
    print(f"{'='*60}")

    # 加载点云
    pointcloud_data, camera_poses = load_pointcloud(
        scene_name, args.max_points, args.sample_frames, cvd_dir=args.cvd_dir
    )

    if pointcloud_data is None:
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"服务器启动在: http://0.0.0.0:{port}")
    print(f"本地访问: http://localhost:{port}")
    print(f"{'='*60}\n")

    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
