# MEGA-SAM 结果可视化工具

提供两种可视化方式：静态HTML文件和交互式3D点云查看器。

---

## 工具1: 静态HTML可视化 (visualize_results.py)

生成独立的HTML文件，包含RGB图像、深度图、相机轨迹等。

### 使用方法

```bash
cd visual
python visualize_results.py <scene_name> [output.html]
```

### 示例

```bash
# 可视化 my_video 场景
python visualize_results.py my_video

# 指定输出文件名
python visualize_results.py my_video my_results.html
```

### 功能特性

- ✅ RGB图像和深度图并排显示
- ✅ 相机轨迹俯视图
- ✅ 位姿信息（位置+四元数）
- ✅ 播放/暂停、帧切换
- ✅ 速度调节
- ✅ 键盘快捷键（空格、左右箭头）

### 查看方式

生成的HTML文件完全独立，可以：
1. 下载到本地用浏览器打开
   ```bash
   scp user@server:/path/to/visualization.html ./
   ```
2. 在服务器启动HTTP服务
   ```bash
   python -m http.server 8000
   ```

---

## 工具2: 3D点云查看器 (pointcloud_viewer.py)

启动Web服务器，在浏览器中交互式查看3D点云。

### 使用方法

```bash
cd visual
python pointcloud_viewer.py <scene_name> [port] [max_points] [sample_frames]
```

### 参数说明

- `scene_name`: 场景名称（必需）
- `port`: 服务器端口，默认8080
- `max_points`: 最大点数，默认100000
- `sample_frames`: 采样帧数，默认10

### 示例

```bash
# 使用默认参数
python pointcloud_viewer.py my_video

# 指定端口
python pointcloud_viewer.py my_video 8888

# 高密度点云
python pointcloud_viewer.py my_video 8080 200000 20

# 快速预览（低密度）
python pointcloud_viewer.py my_video 8080 50000 5
```

### 访问方式

**本地端口转发**（推荐）：
```bash
# 在本地电脑运行
ssh -L 8080:localhost:8080 user@server

# 然后浏览器打开
http://localhost:8080
```

**直接访问**（如果服务器有公网IP）：
```
http://服务器IP:8080
```

### 交互控制

- **左键拖动**: 旋转视角
- **右键拖动**: 平移场景
- **滚轮**: 缩放
- **点大小滑块**: 调整点的显示大小
- **显示/隐藏相机**: 切换相机轨迹
- **重置视角**: 自动调整最佳角度

### 功能特性

- ✅ 3D点云显示（RGB颜色）
- ✅ 相机轨迹可视化
- ✅ 鼠标交互控制
- ✅ 实时调整点大小
- ✅ 坐标轴和网格参考

### 性能建议

- 快速预览: `50000` 点, `5` 帧
- 标准质量: `100000` 点, `10` 帧
- 高质量: `200000` 点, `20` 帧

---

## 数据来源

两个工具都会读取：
- `../outputs_cvd/<scene_name>_sgd_cvd_hr.npz` - RGB图像、深度图、相机位姿
- `../reconstructions/<scene_name>/poses.npy` - 相机位姿（四元数格式）

---

## 选择哪个工具？

| 场景 | 推荐工具 |
|------|---------|
| 快速查看单帧图像和深度 | visualize_results.py |
| 需要离线查看 | visualize_results.py |
| 想要3D视角观察场景 | pointcloud_viewer.py |
| 需要交互式探索 | pointcloud_viewer.py |
| 服务器无法端口转发 | visualize_results.py |
