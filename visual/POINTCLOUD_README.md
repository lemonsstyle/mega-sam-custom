# 3D点云可视化工具

交互式3D点云查看器，支持鼠标控制视角，在浏览器中查看重建结果。

## 使用方法

### 基本用法

```bash
cd /root/mega-sam-main/visual
python pointcloud_viewer.py <scene_name> [port] [max_points] [sample_frames]
```

### 参数说明

- `scene_name`: 场景名称（必需）
- `port`: 服务器端口，默认8080
- `max_points`: 最大点数，默认100000（控制点云密度）
- `sample_frames`: 采样帧数，默认10（从所有帧中采样多少帧生成点云）

### 示例

```bash
# 使用默认参数
python pointcloud_viewer.py my_video

# 指定端口
python pointcloud_viewer.py my_video 8888

# 高密度点云（更多点，更慢）
python pointcloud_viewer.py my_video 8080 200000 20

# 低密度点云（更快加载）
python pointcloud_viewer.py my_video 8080 50000 5
```

## 访问方式

### 本地端口转发

在你的本地电脑上运行：
```bash
ssh -L 8080:localhost:8080 user@server
```

然后在本地浏览器打开：`http://localhost:8080`

### 直接访问（如果服务器有公网IP）

```
http://服务器IP:8080
```

## 交互控制

- **左键拖动**: 旋转视角
- **右键拖动**: 平移场景
- **滚轮**: 缩放
- **点大小滑块**: 调整点的显示大小
- **显示/隐藏相机**: 切换相机轨迹显示
- **重置视角**: 自动调整到最佳观察角度

## 功能特性

- ✅ 3D点云显示（带RGB颜色）
- ✅ 相机轨迹可视化（绿色线条）
- ✅ 相机位置标记（红色球体）
- ✅ 鼠标交互控制
- ✅ 实时调整点大小
- ✅ 坐标轴和网格参考
- ✅ 自动视角调整

## 性能优化建议

- 如果加载慢，减少 `max_points` 和 `sample_frames`
- 如果点云太稀疏，增加这两个参数
- 推荐配置：
  - 快速预览: `50000` 点, `5` 帧
  - 标准质量: `100000` 点, `10` 帧
  - 高质量: `200000` 点, `20` 帧

## 数据来源

工具会读取：
- `../outputs_cvd/<scene_name>_sgd_cvd_hr.npz` - RGB图像、深度图、相机位姿

## 技术栈

- **后端**: Flask (Python)
- **前端**: Three.js (WebGL)
- **控制**: OrbitControls

## 停止服务器

按 `Ctrl+C` 停止服务器
