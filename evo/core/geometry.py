"""
Provides generic geometry algorithms.
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

import typing

import numpy as np

from evo import EvoException


class GeometryException(EvoException):
    pass


UmeyamaResult = typing.Tuple[np.ndarray, np.ndarray, float]

def umeyama_alignment(x: np.ndarray, y: np.ndarray,
                      with_scale: bool = False, yaw_only: bool = False) -> UmeyamaResult:
    """
    Computes the least squares solution parameters of an Sim(m) matrix
    that minimizes the distance between a set of registered points.
    Umeyama, Shinji: Least-squares estimation of transformation parameters
                     between two point patterns. IEEE PAMI, 1991
    :param x: mxn matrix of points, m = dimension, n = nr. of data points
    :param y: mxn matrix of points, m = dimension, n = nr. of data points
    :param with_scale: set to True to align also the scale (default: 1.0 scale)
    :return: r, t, c - rotation matrix, translation vector and scale factor
    """
    if x.shape != y.shape:
        raise GeometryException("data matrices must have the same shape")

    # m = dimension, n = nr. of data points
    m, n = x.shape

    # means, eq. 34 and 35
    mean_x = x.mean(axis=1)
    mean_y = y.mean(axis=1)

    # variance, eq. 36
    # "transpose" for column subtraction
    sigma_x = 1.0 / n * (np.linalg.norm(x - mean_x[:, np.newaxis])**2)

    # covariance matrix, eq. 38
    outer_sum = np.zeros((m, m))
    for i in range(n):
        outer_sum += np.outer((y[:, i] - mean_y), (x[:, i] - mean_x))
    cov_xy = np.multiply(1.0 / n, outer_sum)

    # SVD (text betw. eq. 38 and 39)
    u, d, v = np.linalg.svd(cov_xy)
    if np.count_nonzero(d > np.finfo(d.dtype).eps) < m - 1:
        raise GeometryException("Degenerate covariance rank, "
                                "Umeyama alignment is not possible")

    # S matrix, eq. 43
    s = np.eye(m)
    if np.linalg.det(u) * np.linalg.det(v) < 0.0:
        # Ensure a RHS coordinate system (Kabsch algorithm).
        s[m - 1, m - 1] = -1

    if yaw_only:
        # See equations (15)-(17) in A Tutorial on Quantitative Trajectory Evaluation
        # for Visual(-Inertial) Odometry, by Zhang and Scaramuzza
        rot_C = (x - mean_x[:, np.newaxis]).dot((y - mean_y[:, np.newaxis]).T)
        theta = get_best_yaw(rot_C)
        r = rot_z(theta)
    else:
        # rotation, eq. 40
        r = u.dot(s).dot(v)

    # scale & translation, eq. 42 and 41
    c = 1 / sigma_x * np.trace(np.diag(d).dot(s)) if with_scale else 1.0
    t = mean_y - np.multiply(c, r.dot(mean_x))

    return r, t, c


def arc_len(x: np.ndarray) -> float:
    """
    :param x: nxm array of points, m=dimension
    :return: the (discrete approximated) arc-length of the point sequence
    """
    return np.sum(np.linalg.norm(x[:-1] - x[1:], axis=1))


def accumulated_distances(x: np.ndarray) -> np.ndarray:
    """
    :param x: nxm array of points, m=dimension
    :return: the accumulated distances along the point sequence
    """
    return np.concatenate(
        (np.array([0]), np.cumsum(np.linalg.norm(x[:-1] - x[1:], axis=1))))

def get_best_yaw(C: np.ndarray) -> float:
    """Maximizes trace(Rz(theta) * C)
    :param C: 3x3 rotation matrix
    :return: yaw angle in radians
    """
    if C.shape != (3, 3):
        raise GeometryException("C must be a 3x3 matrix")

    A = C[0, 1] - C[1, 0]
    B = C[0, 0] + C[1, 1]
    theta = np.pi / 2.0 - np.arctan2(B, A)
    return theta

def rot_z(theta: float) -> np.ndarray:
    """
    Creates a rotation about the z-axis by an angle theta.
    :param theta: rotation angle in radians
    :return: 3x3 rotation matrix
    """
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    
    return np.array([
        [cos_theta, -sin_theta, 0],
        [sin_theta,  cos_theta, 0],
        [0,          0,         1]
    ])
