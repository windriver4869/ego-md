#!/usr/bin/env python3
import math

import rospy
import tf
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav_msgs.msg import Odometry


def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class FakeOdom:
    def __init__(self):
        rospy.init_node("fake_odom_node")

        self.frame_id = rospy.get_param("~frame_id", "odom")
        self.child_frame_id = rospy.get_param("~child_frame_id", "base_link")
        self.odom_topic = rospy.get_param("~odom_topic", "/odom_world")
        self.fixed_z = rospy.get_param("~fixed_z", 0.2)
        self.max_linear_vel = rospy.get_param("~max_linear_vel", 0.8)
        self.max_angular_vel = rospy.get_param("~max_angular_vel", 1.5)

        self.x = rospy.get_param("~initial_x", 0.0)
        self.y = rospy.get_param("~initial_y", 0.0)
        self.yaw = rospy.get_param("~initial_yaw", 0.0)
        self.linear_vel = 0.0
        self.angular_vel = 0.0
        self.last_time = rospy.Time.now()

        self.odom_pub = rospy.Publisher(self.odom_topic, Odometry, queue_size=20)
        self.cmd_sub = rospy.Subscriber("/cmd_vel", Twist, self.cmd_callback)
        self.pose_sub = rospy.Subscriber("/initialpose", PoseWithCovarianceStamped, self.pose_callback)
        self.br = tf.TransformBroadcaster()
        self.timer = rospy.Timer(rospy.Duration(0.02), self.publish_odom)

        rospy.loginfo("Fake differential-drive odom publishes %s -> %s on %s",
                      self.frame_id, self.child_frame_id, self.odom_topic)

    def pose_callback(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        _, _, self.yaw = tf.transformations.euler_from_quaternion([q.x, q.y, q.z, q.w])
        rospy.loginfo("Fake odom reset to x=%.2f, y=%.2f, yaw=%.2f", self.x, self.y, self.yaw)

    def cmd_callback(self, msg):
        self.linear_vel = max(-self.max_linear_vel, min(self.max_linear_vel, msg.linear.x))
        self.angular_vel = max(-self.max_angular_vel, min(self.max_angular_vel, msg.angular.z))

    def publish_odom(self, _event):
        now = rospy.Time.now()
        dt = (now - self.last_time).to_sec()
        self.last_time = now

        if dt > 0.0:
            self.yaw = normalize_angle(self.yaw + self.angular_vel * dt)
            self.x += self.linear_vel * math.cos(self.yaw) * dt
            self.y += self.linear_vel * math.sin(self.yaw) * dt

        q = tf.transformations.quaternion_from_euler(0.0, 0.0, self.yaw)

        self.br.sendTransform(
            (self.x, self.y, self.fixed_z),
            q,
            now,
            self.child_frame_id,
            self.frame_id,
        )

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = self.fixed_z
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        odom.twist.twist.linear.x = self.linear_vel
        odom.twist.twist.angular.z = self.angular_vel
        odom.pose.covariance = [0.0] * 36
        odom.twist.covariance = [0.0] * 36
        self.odom_pub.publish(odom)


if __name__ == "__main__":
    try:
        FakeOdom()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
