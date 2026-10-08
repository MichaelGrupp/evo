import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.spatial.transform import Rotation

from evo.core.geometry import GeometryException, umeyama_alignment


@pytest.mark.parametrize("magnitude", [1.0, 1e-6, 1e-9])
@pytest.mark.parametrize("with_scale", [False, True])
def test_umeyama_rank_is_independent_of_coordinate_units(magnitude, with_scale):
    points = magnitude * np.array([[0, 1, 0, 0], [0, 0, 2, 0], [0, 0, 0, 3]])
    rotation = Rotation.from_euler("xyz", [0.2, -0.4, 0.7]).as_matrix()
    translation = magnitude * np.array([3, -2, 1])
    scale = 1.7 if with_scale else 1.0
    target = scale * rotation @ points + translation[:, None]
    actual_r, actual_t, actual_s = umeyama_alignment(points, target, with_scale)
    assert_allclose(actual_r, rotation, atol=1e-14)
    assert_allclose(actual_t / magnitude, translation / magnitude, atol=1e-14)
    assert actual_s == pytest.approx(scale)


@pytest.mark.parametrize("magnitude", [1.0, 1e-9])
def test_umeyama_still_rejects_collinear_points(magnitude):
    points = magnitude * np.array([[0, 1, 2], [0, 0, 0], [0, 0, 0]])
    with pytest.raises(GeometryException):
        umeyama_alignment(points, points)
