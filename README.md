# UAV/Robot SLAM Path Planning Project

## 项目简介

本项目实现了一个自主路径规划与 SLAM 建图系统，面向室内环境，结合 **PX4 飞控、Jetson Orin Nano、激光雷达** 和 ROS/MAVROS 构建的无人机/地面机器人自主导航系统。  
主要功能包括：

- 二维地图读取与点云转换
- 局部路径规划（B-spline + A*）
- 仿真/真实机器人速度控制
- 可视化轨迹与状态（RViz）

---

## 1️⃣ 参数设置

| 参数 | 值 | 作用 |
|------|------|------|
| 地图分辨率 | 0.05 | 栅格地图精度 |
| grid_map/map_size_x | 20.0 | 地图 X 方向尺寸（米） |
| grid_map/map_size_y | 15.0 | 地图 Y 方向尺寸（米） |
| grid_map/map_size_z | 1.0 | 地图 Z 方向尺寸（米） |
| 障碍物膨胀 | 0.001 | 安全距离膨胀 |
| 固定高度 | 0.2 | 机器人规划 Z 高度 |
| 局部规划距离 planning_horizon | 5.0 | 局部路径规划前视距离 |
| 最大速度 max_vel | 0.5 | 局部轨迹最大线速度 |
| 最大加速度 max_acc | 0.8 | 最大加速度 |
| 最大 jerk max_jerk | 4.0 | 最大加加速度变化率 |
| B-spline 控制点间距 | 0.2 | 控制点分布距离 |
| B-spline 碰撞权重 | 500 | 碰撞避障优化权重 |
| B-spline 平滑权重 | 2.0 | 轨迹平滑优化权重 |
| traj_server 最大线速度 | 0.5 | 控制层速度上限 |
| traj_server 最大角速度 | 1.0 | 控制层角速度上限 |
| lookahead_time | 0.6 | 前视时间 |
| goal_tolerance | 0.25 | 到达目标判定半径 |
| fake_odom 最大线速度 | 0.8 | 仿真里程计速度上限 |
| fake_odom 最大角速度 | 1.5 | 仿真里程计角速度上限 |
| A* 强制步长 | 0.05 | 网格搜索精度 |
| 起点 | (0.00, 0.00, 0.20) | 初始位置 |
| 终点 | (5.00, -4.00, 0.20) | 目标位置 |
| A* 搜索结果 | Path found | 是否成功找到路径 |
| A* 扩展节点数 | 100 | 搜索节点数 |
| 局部目标点 | (3.54, -3.54, 0.20) | 局部规划目标 |
| 路径点数 | 101 | 最终轨迹点数 |

---

## 2️⃣ 核心节点与功能

| 节点 | 包 | 主要作用 | 输入接口 | 输出接口 |
|------|----|---------|----------|----------|
| map_server | map_server | 读取 map.yaml/map.png，发布二维地图 | map_tools/maps/map.yaml | /map, /static_map |
| map_to_pc2 | map_tools | 将二维栅格地图转换为点云 | /static_map 服务 | /map_generator/global_cloud |
| fake_odom | map_tools | 模拟机器人里程计 | /cmd_vel, /initialpose | /odom_world, odom->base_link TF |
| ego_planner_node | ego_planner | 核心规划器，生成 B-spline 轨迹 | /odom_world, /map_generator/global_cloud, /waypoint_generator/waypoints | /planning/bspline, 可视化 Marker |
| traj_server | ego_planner | 将 B-spline 转为速度指令 | /planning/bspline, /odom_world | /cmd_vel |
| waypoint_generator | waypoint_generator | 生成/转发目标点 | /odom_world, RViz 目标交互 | /waypoint_generator/waypoints |
| rviz | rviz | 可视化地图、机器人、轨迹 | 多个话题与 TF | 图形界面显示 |
| map_to_world | tf2_ros | 静态 TF: map -> world | launch 参数 | map->world TF |
| map_to_odom | tf2_ros | 静态 TF: map -> odom | launch 参数 | map->odom TF |

---

## 3️⃣ 核心话题数据流

**地图流**
map_server → /map → /static_map → map_to_pc2 → /map_generator/global_cloud → ego_planner_node/grid_map
**规划流**
/odom_world + /waypoint_generator/waypoints + /map_generator/global_cloud
→ ego_planner_node → /planning/bspline
**控制流**
/planning/bspline + /odom_world → traj_server → /cmd_vel → fake_odom 或真实底盘
**反馈流**
/cmd_vel → fake_odom → /odom_world → ego_planner_node + traj_server + waypoint_generator


---

## 4️⃣ TF 坐标系接口

| TF | 发布者 | 作用 |
|----|-------|----|
| map → world | map_to_world | 兼容 world 坐标系，RViz Fixed Frame 使用 map |
| map → odom | map_to_odom | 连接地图和里程计，保证 TF 连通 |
| odom → base_link | fake_odom | 表示机器人在 odom 下的位姿 |

建议 RViz Fixed Frame 设置为 **map**。

---

## 5️⃣ 外部接口

| 类型 | 接口 | 来源 | 作用 | 说明 |
|------|------|------|------|------|
| 地图 | /map | map_server | 二维占据地图 | 可替换为 SLAM 地图 |
| 地图服务 | /static_map | map_server | 提供一次性地图 | map_to_pc2 订阅此服务 |
| 里程计 | /odom_world | fake_odom | 提供机器人位姿 | 可替换为真实里程计或 SLAM 输出 |
| 目标点 | /waypoint_generator/waypoints | waypoint_generator | 规划目标 | RViz 交互或预设路径 |
| 目标姿态 | /initialpose | RViz 2D Pose Estimate | 重置机器人起点 | fake_odom 会根据此设置位姿 |
| 控制 | /cmd_vel | traj_server | 输出速度指令 | 底盘订阅 geometry_msgs/Twist |
