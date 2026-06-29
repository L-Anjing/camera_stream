cmake_minimum_required(VERSION 3.10)
project(camera_stream)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS core imgproc highgui videoio)

include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(camera_node src/camera_node.cpp)

target_link_libraries(camera_node ${OpenCV_LIBS})
ament_target_dependencies(camera_node rclcpp sensor_msgs cv_bridge)

install(TARGETS camera_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(DIRECTORY config DESTINATION share/${PROJECT_NAME})

ament_package()
