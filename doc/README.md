Please see the [evo Wiki](https://github.com/MichaelGrupp/evo/wiki) for more documentation.

### Formats Overview

For details on supported trajectory input/output formats:
* **TUM**: Text file with space-delimited columns: `timestamp tx ty tz qx qy qz qw`. Timestamps are floating-point numbers in seconds, and quaternion components follow `qx qy qz qw` ordering.
* **KITTI**: Pose file with 12 space-delimited values representing the top 3x4 block of a 4x4 transformation matrix row-by-row (`r11 r12 r13 tx r21 r22 r23 ty r31 r32 r33 tz`).
* **EuRoC**: CSV groundtruth format or TUM trajectory file.
* **Bag (ROS 1 & ROS 2 / MCAP)**: Bag files containing supported topic types (`geometry_msgs/PoseStamped`, `geometry_msgs/TransformStamped`, `geometry_msgs/PoseWithCovarianceStamped`, `geometry_msgs/PointStamped`, `nav_msgs/Odometry`, or `/tf`).
