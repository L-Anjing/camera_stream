/// @file camera_node.cpp
/// @brief USB Camera ROS2 发布节点（V4L2 + MJPEG）
///
/// 设备路径通过参数传入:
///   ros2 run camera_stream camera_node --ros-args \
///     -p device:=/dev/camera_left \
///     -p camera_name:=cam_left \
///     -p image_width:=1280 \
///     -p image_height:=720 \
///     -p framerate:=30

#include <chrono>
#include <memory>
#include <string>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <cv_bridge/cv_bridge.h>

#include <opencv2/core.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>

class CameraNode : public rclcpp::Node {
public:
  CameraNode() : Node("camera_node") {
    declare_parameter<std::string>("device", "/dev/video0");
    declare_parameter<std::string>("camera_name", "cam");
    declare_parameter<int>("image_width", 1280);
    declare_parameter<int>("image_height", 720);
    declare_parameter<int>("framerate", 30);

    device_      = get_parameter("device").as_string();
    camera_name_ = get_parameter("camera_name").as_string();
    width_       = get_parameter("image_width").as_int();
    height_      = get_parameter("image_height").as_int();
    fps_         = get_parameter("framerate").as_int();

    // ── 打开摄像头 ──
    cap_.open(device_, cv::CAP_V4L2);
    if (!cap_.isOpened()) {
      RCLCPP_FATAL(get_logger(), "Failed to open %s", device_.c_str());
      throw std::runtime_error("Camera open failed: " + device_);
    }

    // ── 设置 MJPEG 格式 + 分辨率 ──
    cap_.set(cv::CAP_PROP_FOURCC,
             cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
    cap_.set(cv::CAP_PROP_FRAME_WIDTH, width_);
    cap_.set(cv::CAP_PROP_FRAME_HEIGHT, height_);
    cap_.set(cv::CAP_PROP_FPS, fps_);

    double actual_w = cap_.get(cv::CAP_PROP_FRAME_WIDTH);
    double actual_h = cap_.get(cv::CAP_PROP_FRAME_HEIGHT);
    double actual_fps = cap_.get(cv::CAP_PROP_FPS);

    // ── 发布器 ──
    pub_ = create_publisher<sensor_msgs::msg::Image>(
        "/" + camera_name_ + "/image_raw", rclcpp::QoS(2).best_effort());

    // ── 定时器拉流 ──
    int interval_ms = static_cast<int>(1000.0 / fps_);
    timer_ = create_wall_timer(
        std::chrono::milliseconds(interval_ms),
        std::bind(&CameraNode::timer_cb, this));

    RCLCPP_INFO(get_logger(), "===========================================");
    RCLCPP_INFO(get_logger(), "  CameraNode [%s]", camera_name_.c_str());
    RCLCPP_INFO(get_logger(), "  Device: %s", device_.c_str());
    RCLCPP_INFO(get_logger(), "  Req: %dx%d @ %d MJPEG",
                width_, height_, fps_);
    RCLCPP_INFO(get_logger(), "  Act: %dx%d @ %.1f",
                (int)actual_w, (int)actual_h, actual_fps);
    RCLCPP_INFO(get_logger(), "  Pub: /%s/image_raw", camera_name_.c_str());
    RCLCPP_INFO(get_logger(), "===========================================");
  }

  ~CameraNode() { if (cap_.isOpened()) cap_.release(); }

private:
  void timer_cb() {
    cv::Mat frame;
    if (!cap_.read(frame) || frame.empty()) {
      RCLCPP_WARN(get_logger(), "Frame grab failed");
      return;
    }
    auto msg = cv_bridge::CvImage(
        std_msgs::msg::Header(), "bgr8", frame).toImageMsg();
    msg->header.stamp = now();
    msg->header.frame_id = camera_name_;
    pub_->publish(*msg);
  }

  std::string device_, camera_name_;
  int width_, height_, fps_;
  cv::VideoCapture cap_;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<CameraNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
