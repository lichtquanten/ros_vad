cmake_minimum_required(VERSION 2.8.3)
project(ros_vad)

find_package(catkin REQUIRED)

catkin_python_setup()

catkin_package(
	CATKIN_DEPENDS
	audio_io_msgs
	message_runtime
	rospy
	rospy_wrapper
	std_msgs
)
