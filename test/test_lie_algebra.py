#!/usr/bin/env python
"""
unit test for lie_algebra module - mainly test mathematical correctness
author: Michael Grupp

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

import random
import timeit
import unittest

import numpy as np

from evo.core import lie_algebra as lie


class TestSE3(unittest.TestCase):
    def test_is_se3(self):
        # yapf: disable
        p = np.array([[1, 0, 0, 1],
                      [0, 0, -1, 2],
                      [0, 1, 0, 3],
                      [0, 0, 0, 1]])
        self.assertTrue(lie.is_se3(p))
        p_false = np.array([[1, 0, 0, 1],
                            [0, 0, -4223, 2],
                            [0, 111, 0, 3],
                            [0, 0, 0, 1]])
        self.assertFalse(lie.is_se3(p_false))
        # yapf: enable

    def test_random_se3(self):
        self.assertTrue(lie.is_se3(lie.random_se3()))

    def test_se3_inverse(self):
        p = lie.random_se3()
        p_inv = lie.se3_inverse(p)
        self.assertTrue(lie.is_se3(p_inv))
        self.assertTrue(np.allclose(p_inv.dot(p), np.eye(4)))

    def test_relative_se3(self):
        a = lie.random_se3()
        b = lie.random_se3()
        self.assertTrue(lie.is_se3(a) and lie.is_se3(b))
        a_to_b = lie.relative_se3(a, b)
        self.assertTrue(lie.is_se3(a_to_b))
        b_from_a = a.dot(a_to_b)
        self.assertTrue(np.allclose(b_from_a, b))


class TestSO3(unittest.TestCase):
    def test_is_so3(self):
        # yapf: disable
        r = np.array([[1, 0, 0],
                      [0, 0, -1],
                      [0, 1, 0]])
        self.assertTrue(lie.is_so3(r))
        # yapf: enable

    def test_random_so3(self):
        r = lie.random_so3()
        self.assertTrue(lie.is_so3(r))

    def test_relative_so3(self):
        a = lie.random_so3()
        b = lie.random_so3()
        self.assertTrue(lie.is_so3(a) and lie.is_so3(b))
        a_to_b = lie.relative_so3(a, b)
        b_from_a = a.dot(a_to_b)
        self.assertTrue(np.allclose(b_from_a, b))

    def test_so3_from_se3(self):
        p = lie.random_se3()
        r = lie.so3_from_se3(p)
        self.assertTrue(lie.is_so3(r))

    def test_so3_log_exp(self):
        r = lie.random_so3()
        self.assertTrue(lie.is_so3(r))
        rotvec = lie.so3_log(r, return_angle_only=False)
        self.assertTrue(np.allclose(r, lie.so3_exp(rotvec), atol=1e-6))
        angle = lie.so3_log(r)
        self.assertAlmostEqual(np.linalg.norm(rotvec), angle)

    def test_so3_log_exp_skew(self):
        r = lie.random_so3()
        log = lie.so3_log(r, return_skew=True)  # skew-symmetric tangent space
        # here, axis is a rotation vector with norm = angle
        rotvec = lie.vee(log)
        self.assertTrue(np.allclose(r, lie.so3_exp(rotvec)))


class TestSim3(unittest.TestCase):
    def test_is_sim3(self):
        r = lie.random_so3()
        t = np.array([1, 2, 3])
        s = 3
        p = lie.sim3(r, t, s)
        self.assertTrue(lie.is_sim3(p, s))

    def test_sim3_scale_effect(self):
        r = lie.random_so3()
        t = np.array([0, 0, 0])
        s = random.random() * 10
        x = np.array([1, 0, 0, 1]).T  # homogeneous vector
        p = lie.sim3(r, t, s)
        self.assertTrue(lie.is_sim3(p, s))
        x = p.dot(x)  # apply Sim(3) transformation
        self.assertTrue(
            np.equal(x,
                     lie.se3(r).dot(np.array([s, 0, 0, 1]))).all())

    def test_sim3_inverse(self):
        r = lie.random_so3()
        t = np.array([1, 2, 3])
        s = random.random() * 10
        p = lie.sim3(r, t, s)
        self.assertTrue(lie.is_sim3(p, s))
        p_inv = lie.sim3_inverse(p)
        self.assertTrue(np.allclose(p_inv.dot(p), np.eye(4)))


if __name__ == '__main__':
    """
    benchmarks
    """
    print("\ncheck speed of SE(3) inverse:")
    setup = "from evo.core import lie_algebra as lie; " \
            "import numpy as np; se3 = lie.random_se3()"
    print("time for 1000*lie.se3_inverse(se3): ",
          timeit.timeit("lie.se3_inverse(se3)", setup=setup, number=1000))
    print("time for 1000*np.linalg.inv(se3): ",
          timeit.timeit("np.linalg.inv(se3)", setup=setup, number=1000))

    print("\ncheck speed of  SO(3) log:")
    setup = "from evo.core import lie_algebra as lie; " \
            "import numpy as np; so3 = lie.random_so3()"
    print("time for 1000*lie.so3_log(so3, skew=True): ",
          timeit.timeit("lie.so3_log(so3, True)", setup=setup, number=1000))
    print("time for 1000*lie.so3_log(so3): ",
          timeit.timeit("lie.so3_log(so3)", setup=setup, number=1000))
    setup = "from evo.core import lie_algebra as lie; import numpy as np; " \
            "import evo.core.transformations as tr; " \
            "so3 = lie.se3(lie.random_so3(), [0, 0, 0])"
    print("time for 1000*tr.rotation_from_matrix(so3): ",
          timeit.timeit("tr.rotation_from_matrix(so3)", setup=setup,
                        number=1000))
    setup = "from evo.core import lie_algebra as lie; " \
            "import numpy as np; so3 = lie.random_so3(); " \
            "rotvec = lie.so3_log(so3, False)"
    print("time for 1000*lie.so3_exp(rotvec): ",
          timeit.timeit("lie.so3_exp(rotvec)", setup=setup, number=1000))
    """
    unit test
    """
    unittest.main(verbosity=2)
