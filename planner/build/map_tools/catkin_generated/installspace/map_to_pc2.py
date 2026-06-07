#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2
from std_msgs.msg import Header
from nav_msgs.srv import GetMap

class MapToPointCloud:
    def __init__(self):
        rospy.init_node('map_to_pc2_node')
        self.frame_id = rospy.get_param("~frame_id", "map")
        # 保持 latch=True，但增加频率
        self.pc2_pub = rospy.Publisher('/map_generator/global_cloud', PointCloud2, queue_size=1, latch=True)
        self.cached_pc2 = None 
        
        rospy.loginfo("Waiting for static_map service...")
        rospy.wait_for_service('/static_map')
        
        self.fetch_and_convert()
        
        # 提高重发频率到 1Hz，帮助 Ego-Planner 的 local_mapping 持续更新
        self.timer = rospy.Timer(rospy.Duration(0.1), self.republish)

    def fetch_and_convert(self):
        try:
            get_map = rospy.ServiceProxy('/static_map', GetMap)
            response = get_map()
            self.cached_pc2 = self.convert_map_to_pc2(response.map)
            self.pc2_pub.publish(self.cached_pc2)
            rospy.loginfo("Map converted and first cloud published!")
        except Exception as e:
            rospy.logerr("Fetch map failed: %s", e)

    def convert_map_to_pc2(self, msg):
        points = []
        res = msg.info.resolution
        width = msg.info.width
        height = msg.info.height
        origin_x = msg.info.origin.position.x
        origin_y = msg.info.origin.position.y
        
        for i in range(height):
            for j in range(width):
                # 占据率判断
                if msg.data[i * width + j] > 30:
                    x = j * res + origin_x
                    y = i * res + origin_y
                    
                    # --- 改进点：Z轴范围必须覆盖机器人的 0.5m 高度 ---
                    # 如果机器人中心在 0.5m，点云必须在它上下都有分布
                    # 我们从 -0.2m 模拟到 1.2m，确保是一堵实心的墙
                    for z_idx in range(0, 10):  
                        z = -0.2 + z_idx * 0.14
                        points.append([x, y, z])
        
        header = Header()
        header.stamp = rospy.Time.now()
        header.frame_id = self.frame_id 
        return pc2.create_cloud_xyz32(header, points)

    def republish(self, event):
        if self.cached_pc2 is not None:
            self.cached_pc2.header.stamp = rospy.Time.now()
            self.pc2_pub.publish(self.cached_pc2)

if __name__ == '__main__':
    node = MapToPointCloud()
    rospy.spin()
