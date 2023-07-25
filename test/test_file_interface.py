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
