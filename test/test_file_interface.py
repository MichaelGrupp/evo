#!/usr/bin/env python
"""
Unit test for file_interface module.
Author: Michael Grupp

This file is part of evo (github.com/MichaelGrupp/evo).

evo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

evo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with evo.  If not, see <http://www.gnu.org/licenses/>.
"""

import io
import tempfile
import unittest

import numpy as np
from rosbags.rosbag1 import (Reader as Rosbag1Reader, Writer as Rosbag1Writer)
from rosbags.rosbag2 import (Reader as Rosbag2Reader, Writer as Rosbag2Writer)

import helpers
import evo.core.lie_algebra as lie
from evo.core.result import Result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools import file_interface


class MockFileTestCase(unittest.TestCase):
    def __init__(self, in_memory_buffer, *args, **kwargs):
        super(MockFileTestCase, self).__init__(*args, **kwargs)
        self.mock_file = in_memory_buffer

    @staticmethod
    def run_and_clear(test_method):
        def _decorator(self, *args, **kwargs):
            try:
                test_method(self, *args, **kwargs)
            finally:
                self.mock_file.seek(0)
                self.mock_file.truncate()

        return _decorator

    @staticmethod
    def allow_import_error(test_method):
        def _decorator(self, *args, **kwargs):
            try:
                test_method(self, *args, **kwargs)
            except ImportError:
                pass

        return _decorator


class TestTumFile(MockFileTestCase):
    def __init__(self, *args, **kwargs):
        super(TestTumFile, self).__init__(io.StringIO(), *args, **kwargs)

    @MockFileTestCase.run_and_clear
    def test_write_read_integrity(self):
        traj_out = helpers.fake_trajectory(1000, 0.1)
        self.assertTrue(traj_out.check())
        file_interface.write_tum_trajectory_file(self.mock_file, traj_out)
        self.mock_file.seek(0)
        traj_in = file_interface.read_tum_trajectory_file(self.mock_file)
        self.assertIsInstance(traj_in, PoseTrajectory3D)
        self.assertTrue(traj_in.check())
        self.assertTrue(traj_out == traj_in)

    @MockFileTestCase.run_and_clear
    def test_trailing_delim(self):
        self.mock_file.write(u"0 0 0 0 0 0 0 1 ")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_tum_trajectory_file(self.mock_file)

    @MockFileTestCase.run_and_clear
    def test_too_many_columns(self):
        self.mock_file.write(u"1 2 3 4 5 6 7 8 9")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_tum_trajectory_file(self.mock_file)

    @MockFileTestCase.run_and_clear
    def test_too_few_columns(self):
        self.mock_file.write(u"1 2 3 4 5 6 7")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_tum_trajectory_file(self.mock_file)

    @MockFileTestCase.run_and_clear
    def test_too_few_columns_with_trailing_delim(self):
        self.mock_file.write(u"1 2 3 4 5 6 7 ")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_tum_trajectory_file(self.mock_file)


class TestKittiFile(MockFileTestCase):
    def __init__(self, *args, **kwargs):
        super(TestKittiFile, self).__init__(io.StringIO(), *args, **kwargs)

    @MockFileTestCase.run_and_clear
    def test_write_read_integrity(self):
        traj_out = helpers.fake_path(1000)
        self.assertTrue(traj_out.check())
        file_interface.write_kitti_poses_file(self.mock_file, traj_out)
        self.mock_file.seek(0)
        traj_in = file_interface.read_kitti_poses_file(self.mock_file)
        self.assertIsInstance(traj_in, PosePath3D)
        self.assertTrue(traj_in.check())
        self.assertTrue(traj_out == traj_in)

    @MockFileTestCase.run_and_clear
    def test_trailing_delim(self):
        self.mock_file.write(u"1 0 0 0.1 0 1 0 0.2 0 0 1 0.3 ")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_kitti_poses_file(self.mock_file)

    @MockFileTestCase.run_and_clear
    def test_too_many_columns(self):
        self.mock_file.write(u"1 2 3 4 5 6 7 8 9 10 11 12 13")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_kitti_poses_file(self.mock_file)

    @MockFileTestCase.run_and_clear
    def test_too_few_columns(self):
        self.mock_file.write(u"1 2 3 4 5 6 7 8 9 10 11")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_kitti_poses_file(self.mock_file)

    @MockFileTestCase.run_and_clear
    def test_too_few_columns_with_trailing_delim(self):
        self.mock_file.write(u"1 2 3 4 5 6 7 8 9 10 11 ")
        self.mock_file.seek(0)
        with self.assertRaises(file_interface.FileInterfaceException):
            file_interface.read_kitti_poses_file(self.mock_file)


class TestBagFile(MockFileTestCase):
    def __init__(self, *args, **kwargs):
        super(TestBagFile, self).__init__(io.BytesIO(), *args, **kwargs)

    def test_write_read_integrity(self):
        for reader_t, writer_t in zip([Rosbag1Reader, Rosbag2Reader],
                                      [Rosbag1Writer, Rosbag2Writer]):
            # TODO: rosbags cannot overwrite existing paths, this forces us
            # to do this here to get only a filepath:
            tmp_filename = tempfile.NamedTemporaryFile(delete=True).name
            bag_out = writer_t(tmp_filename)
            bag_out.open()
            traj_out = helpers.fake_trajectory(1000, 0.1)
            self.assertTrue(traj_out.check())
            file_interface.write_bag_trajectory(bag_out, traj_out, "/test",
                                                frame_id="map")
            bag_out.close()
            bag_in = reader_t(tmp_filename)
            bag_in.open()
            traj_in = file_interface.read_bag_trajectory(bag_in, "/test")
            self.assertIsInstance(traj_in, PoseTrajectory3D)
            self.assertTrue(traj_in.check())
            self.assertTrue(traj_out == traj_in)
            self.assertEqual(traj_in.meta["frame_id"], "map")

class TestCsvFile(MockFileTestCase):
    def __init__(self, *args, **kwargs):
        super(TestCsvFile, self).__init__(io.StringIO(), *args, **kwargs)

        # The reference trajectory:
        stamps = [1739641583.660682927]
        xyz = [[-5.662295808104799e-05,0.00016827168702906548,3.5524415470101045e-05]]
        quat = [[1.9329304695625015e-06,1.3492393190741297e-05,-0.0005278167789287769,0.9999998606118238]]
        self.ref = PoseTrajectory3D(xyz, quat, stamps)
    
    @MockFileTestCase.run_and_clear
    def test_read_ros1tf(self):
        self.mock_file.write(u"%time,field.transforms0.header.seq,field.transforms0.header.stamp,field.transforms0.header.frame_id,field.transforms0.child_frame_id,field.transforms0.transform.translation.x,field.transforms0.transform.translation.y,field.transforms0.transform.translation.z,field.transforms0.transform.rotation.x,field.transforms0.transform.rotation.y,field.transforms0.transform.rotation.z,field.transforms0.transform.rotation.w\n")
        self.mock_file.write(u"1739641583661579370,0,1739641583660682927,camera_init,aft_mapped,-5.662295808104799e-05,0.00016827168702906548,3.5524415470101045e-05,1.9329304695625015e-06,1.3492393190741297e-05,-0.0005278167789287769,0.9999998606118238")
        for topic_type in [None, "ros1tf"]:
            self.mock_file.seek(0)
            traj = file_interface.read_csv_trajectory_file(self.mock_file, topic_type)
            self.assertEqual(traj.positions_xyz.all(), self.ref.positions_xyz.all())
            self.assertEqual(traj.orientations_quat_wxyz.all(), self.ref.orientations_quat_wxyz.all())
            self.assertEqual(traj.timestamps.all(), self.ref.timestamps.all())
    
    @MockFileTestCase.run_and_clear
    def test_read_ros1odo(self):
        self.mock_file.write(u"%time,field.header.seq,field.header.stamp,field.header.frame_id,field.child_frame_id,field.pose.pose.position.x,field.pose.pose.position.y,field.pose.pose.position.z,field.pose.pose.orientation.x,field.pose.pose.orientation.y,field.pose.pose.orientation.z,field.pose.pose.orientation.w,field.pose.covariance0,field.pose.covariance1,field.pose.covariance2,field.pose.covariance3,field.pose.covariance4,field.pose.covariance5,field.pose.covariance6,field.pose.covariance7,field.pose.covariance8,field.pose.covariance9,field.pose.covariance10,field.pose.covariance11,field.pose.covariance12,field.pose.covariance13,field.pose.covariance14,field.pose.covariance15,field.pose.covariance16,field.pose.covariance17,field.pose.covariance18,field.pose.covariance19,field.pose.covariance20,field.pose.covariance21,field.pose.covariance22,field.pose.covariance23,field.pose.covariance24,field.pose.covariance25,field.pose.covariance26,field.pose.covariance27,field.pose.covariance28,field.pose.covariance29,field.pose.covariance30,field.pose.covariance31,field.pose.covariance32,field.pose.covariance33,field.pose.covariance34,field.pose.covariance35,field.twist.twist.linear.x,field.twist.twist.linear.y,field.twist.twist.linear.z,field.twist.twist.angular.x,field.twist.twist.angular.y,field.twist.twist.angular.z,field.twist.covariance0,field.twist.covariance1,field.twist.covariance2,field.twist.covariance3,field.twist.covariance4,field.twist.covariance5,field.twist.covariance6,field.twist.covariance7,field.twist.covariance8,field.twist.covariance9,field.twist.covariance10,field.twist.covariance11,field.twist.covariance12,field.twist.covariance13,field.twist.covariance14,field.twist.covariance15,field.twist.covariance16,field.twist.covariance17,field.twist.covariance18,field.twist.covariance19,field.twist.covariance20,field.twist.covariance21,field.twist.covariance22,field.twist.covariance23,field.twist.covariance24,field.twist.covariance25,field.twist.covariance26,field.twist.covariance27,field.twist.covariance28,field.twist.covariance29,field.twist.covariance30,field.twist.covariance31,field.twist.covariance32,field.twist.covariance33,field.twist.covariance34,field.twist.covariance35\n")
        self.mock_file.write(u"1664948325587996960,0,1739641583660682927,/camera_init,/laser_odom,-5.662295808104799e-05,0.00016827168702906548,3.5524415470101045e-05,1.9329304695625015e-06,1.3492393190741297e-05,-0.0005278167789287769,0.9999998606118238,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0")
        for topic_type in [None, "ros1odo"]:
            self.mock_file.seek(0)
            traj = file_interface.read_csv_trajectory_file(self.mock_file, topic_type)
            self.assertEqual(traj.positions_xyz.all(), self.ref.positions_xyz.all())
            self.assertEqual(traj.orientations_quat_wxyz.all(), self.ref.orientations_quat_wxyz.all())
            self.assertEqual(traj.timestamps.all(), self.ref.timestamps.all())

class TestResultFile(MockFileTestCase):
    def __init__(self, *args, **kwargs):
        super(TestResultFile, self).__init__(io.BytesIO(), *args, **kwargs)

    @MockFileTestCase.run_and_clear
    def test_write_read_integrity(self):
        result_out = Result()
        result_out.add_np_array("test-array", np.ones(1000))
        result_out.add_info({"name": "test", "number": 666})
        result_out.add_trajectory("traj", helpers.fake_trajectory(1000, 0.1))
        file_interface.save_res_file(self.mock_file, result_out)
        result_in = file_interface.load_res_file(self.mock_file,
                                                 load_trajectories=True)
        self.assertEqual(result_in, result_out)


class TestHasUtf8Bom(unittest.TestCase):
    def test_no_bom(self):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        with open(tmp_file.name, 'w') as f:
            f.write("foo")
        self.assertFalse(file_interface.has_utf8_bom(tmp_file.name))

    def test_with_bom(self):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        with open(tmp_file.name, 'wb') as f:
            f.write(b"\xef\xbb\xbf")
        self.assertTrue(file_interface.has_utf8_bom(tmp_file.name))


class TestLoadTransform(unittest.TestCase):
    def test_json(self):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        with open(tmp_file.name, 'w') as f:
            f.write(""" {
                "x": 1.0,
                "y": 2.5,
                "z": 3.0,
                "qx": 0.0,
                "qy": 0.0,
                "qz": 0.0,
                "qw": 1.0,
                "scale": 0.5
            }
            """)
        transform = file_interface.load_transform(tmp_file.name)
        self.assertTrue(lie.is_sim3(transform))
        self.assertTrue(np.allclose(transform[:3, :3], np.eye(3) * 0.5))
        self.assertTrue(np.allclose(transform[:3, 3], [1, 2.5, 3]))
        self.assertAlmostEqual(lie.sim3_scale(transform), 0.5)

    def test_npy(self):
        transform_out = lie.sim3(lie.random_so3(), np.random.random(3),
                                 np.random.random_sample())
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        np.save(tmp_file.name, transform_out)
        # np.save automatically adds ".npy" to the file name
        transform_in = file_interface.load_transform(tmp_file.name + ".npy")
        self.assertTrue(np.allclose(transform_out, transform_in))

    def test_txt(self):
        transform_out = lie.sim3(lie.random_so3(), np.random.random(3),
                                 np.random.random_sample())
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        np.savetxt(tmp_file.name, transform_out)
        transform_in = file_interface.load_transform(tmp_file.name)
        self.assertTrue(np.allclose(transform_out, transform_in))


if __name__ == '__main__':
    unittest.main(verbosity=2)
