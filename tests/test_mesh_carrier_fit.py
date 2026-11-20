import numpy as np
import pytest

from demosaic.cfa import PATTERNS
from demosaic.mesh_carrier_fit import _spacing, refine_raw_mesh_carriers

pytest.importorskip("scipy")


def scene_fixture():
    y, x = np.indices((480, 480), dtype=np.float32)
    return (
        0.08
        + 0.003 * np.cos(2 * np.pi * (0.1171875 * x + 0.07421875 * y) + 0.8)
        + 0.002 * np.cos(2 * np.pi * (0.08984375 * x - 0.072265625 * y) - 0.9)
    ).astype(np.float32)


def pack(raw):
    return np.stack([raw[p // 2 :: 2, p % 2 :: 2] for p in range(4)])


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_measured_mesh_with_odd_native_origin(pattern):
    image = scene_fixture()
    crop = (151, 149, 160, 160)
    clean = image[149:309, 151:311]
    previous = np.full((3, 160, 160), 0.08, dtype=np.float32)
    restored = refine_raw_mesh_carriers(
        previous,
        pack(image),
        PATTERNS[pattern],
        crop,
        shot=0.00128,
        read=6.5536e-6,
        white_balance=np.ones(3),
        camera_to_srgb=np.eye(3),
    )
    center = np.s_[..., 16:-16, 16:-16]
    expected = np.repeat(clean[None], 3, axis=0)
    error = np.sqrt(np.mean((restored[center] - expected[center]) ** 2))
    starting_error = np.sqrt(np.mean((previous[center] - expected[center]) ** 2))
    assert error < 0.55 * starting_error
    assert restored.dtype == previous.dtype


@pytest.mark.parametrize("method", ("local64", "ring-posterior"))
def test_ring_of_donors_does_not_fill_measured_flat_center(method):
    image = scene_fixture()
    image[149:309, 151:311] = 0.08
    previous = np.full((3, 160, 160), 0.08, dtype=np.float32)
    args = {
        "shot": 0.00128,
        "read": 6.5536e-6,
        "white_balance": np.ones(3),
        "camera_to_srgb": np.eye(3),
        "method": method,
    }
    result = refine_raw_mesh_carriers(
        previous, pack(image), PATTERNS["RGGB"], (151, 149, 160, 160), **args
    )
    np.testing.assert_array_equal(result, previous)
    edge = refine_raw_mesh_carriers(
        previous, pack(image), PATTERNS["RGGB"], (16, 16, 160, 160), **args
    )
    np.testing.assert_array_equal(edge, previous)
    if method == "ring-posterior":
        with pytest.raises(ValueError, match="at least 16"):
            refine_raw_mesh_carriers(
                previous,
                pack(image),
                PATTERNS["RGGB"],
                (151, 149, 160, 160),
                donor_clearance=15,
                **args,
            )


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_frequency_donors_exclude_the_verification_halo(pattern):
    raw = scene_fixture()
    x, y, halo = 151, 149, 16
    original = _spacing(pack(raw), PATTERNS[pattern], x, y, clearance=halo)
    assert original is not None

    changed = raw.copy()
    held = changed[y - halo : y + 160 + halo, x - halo : x + 160 + halo]
    held[:] = np.random.default_rng(812).uniform(0.03, 0.15, held.shape)
    replay = _spacing(pack(changed), PATTERNS[pattern], x, y, clearance=halo)
    np.testing.assert_array_equal(replay, original)


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
@pytest.mark.parametrize(
    "method",
    (
        "pooled",
        "pooled-color",
        "ring-posterior",
        "weak-posterior",
        "weak-phase-guard",
        "weak-phase-contrast",
    ),
)
def test_contextual_weak_phase_on_an_odd_native_origin(pattern, method):
    y, x = np.indices((480, 480), dtype=np.float32)
    x, y = x - 230, y - 228
    envelope = np.clip((122 - np.maximum(abs(x), abs(y))) / 33, 0, 1)
    warp = envelope * (2.5 * (x + y) / 110 + (x - y) ** 2 / 30000)
    strong = 0.008 * np.cos(2 * np.pi * (0.1171875 * x + 0.07421875 * y) + 0.8)
    weak = 0.004 * np.cos(2 * np.pi * (0.08984375 * x - 0.072265625 * y) - 0.9 + warp)
    context = np.full((3, 192, 192), 0.08, dtype=np.float32)
    parent = context[:, 16:-16, 16:-16]
    result = refine_raw_mesh_carriers(
        parent,
        pack(0.08 + strong + weak),
        PATTERNS[pattern],
        (151, 149, 160, 160),
        shot=0.00128,
        read=6.5536e-6,
        white_balance=np.ones(3),
        camera_to_srgb=np.eye(3),
        method=method,
        parent_context=None if method == "ring-posterior" else context,
    )

    core = np.s_[165:293, 167:295]
    restored = result[1, 16:-16, 16:-16] - 0.08
    for carrier in (strong[core], weak[core]):
        assert np.sum(restored * carrier) > 0.45 * np.sum(carrier**2)
    np.testing.assert_array_equal(result[0], result[1])
    assert result.dtype == parent.dtype


@pytest.mark.parametrize(
    "method",
    ("pooled", "pooled-color", "weak-posterior", "weak-phase-guard", "weak-phase-contrast"),
)
def test_pooled_fit_requires_context_and_independent_donors(method):
    raw = scene_fixture()
    raw[133:325, 135:327] = 0.08
    context = np.full((3, 192, 192), 0.08, dtype=np.float32)
    parent = context[:, 16:-16, 16:-16]

    def refine(roi, **kwargs):
        return refine_raw_mesh_carriers(
            parent,
            pack(raw),
            PATTERNS["RGGB"],
            roi,
            shot=0.00128,
            read=6.5536e-6,
            white_balance=np.ones(3),
            camera_to_srgb=np.eye(3),
            method=method,
            **kwargs,
        )

    center = (151, 149, 160, 160)
    with pytest.raises(ValueError, match="requires a 192×192 parent_context"):
        refine(center)
    with pytest.raises(ValueError, match="exact RGB parent"):
        refine(center, parent_context=context + 0.01)
    with pytest.raises(ValueError, match="at least 16"):
        refine(center, parent_context=context, donor_clearance=15)
    assert refine(center, parent_context=context) is parent
    assert refine((16, 16, 160, 160), parent_context=context) is parent


def test_weak_phase_guard_transports_absolute_cfa_phase_at_odd_clearance():
    from demosaic._mesh_weak_phase import _taper

    origin = (151, 149)
    y, x = np.indices((480, 480), dtype=np.float64)
    frequencies = np.array(((0.1171875, 0.07421875), (0.08984375, -0.072265625)))
    strong = 0.014 * np.cos(2 * np.pi * (frequencies[0, 0] * x + frequencies[0, 1] * y))
    phase = 2 * np.pi * (frequencies[1, 0] * x + frequencies[1, 1] * y)
    gap = (abs(x - 232) < 20) & (y >= origin[1]) & (y < origin[1] + 160)
    weak_amplitude = np.where(gap, 0.0, 0.005)
    raw = 0.08 + strong
    for angle, (r, c) in zip((0, 0.7, 2, 3), np.ndindex(2, 2), strict=True):
        raw[r::2, c::2] += (weak_amplitude * np.cos(phase + angle))[r::2, c::2]
    scene = pack(raw)
    greens = ((0, 1), (1, 0))
    even = _taper(scene, origin, greens, frequencies, 1, 0.00128, 6.5536e-6, 16)
    odd = _taper(scene, origin, greens, frequencies, 1, 0.00128, 6.5536e-6, 17)

    assert even[:, :32].mean() > 0.9
    assert even[:, 68:92].mean() < 0.1
    np.testing.assert_allclose(odd, even, rtol=1e-8, atol=1e-8)


def test_weak_phase_contrast_falls_back_to_guard_when_exterior_phase_is_unreliable(monkeypatch):
    from demosaic import _mesh_weak_phase

    monkeypatch.setattr(_mesh_weak_phase, "_taper", lambda *args: _mesh_weak_phase._GAIN)
    context = np.full((3, 192, 192), 0.08, dtype=np.float32)
    parent = context[:, 16:-16, 16:-16]
    args = (parent, pack(scene_fixture()), PATTERNS["RGGB"], (151, 149, 160, 160))
    kwargs = {
        "shot": 0.00128,
        "read": 6.5536e-6,
        "white_balance": np.ones(3),
        "camera_to_srgb": np.eye(3),
        "parent_context": context,
    }
    guarded = refine_raw_mesh_carriers(*args, method="weak-phase-guard", **kwargs)
    contrast = refine_raw_mesh_carriers(*args, method="weak-phase-contrast", **kwargs)
    assert np.any(guarded != parent)
    np.testing.assert_array_equal(contrast, guarded)


def test_pooled_color_keeps_flat_green_when_red_and_blue_have_carriers():
    raw = scene_fixture()
    packed = pack(raw)
    colors = PATTERNS["BGGR"]
    for phase, color in enumerate(colors):
        if color == 1:
            # The halo starts on an odd native row and column.
            row, col = 67 - phase // 2, 68 - phase % 2
            packed[phase, row : row + 96, col : col + 96] = 0.08
    context = np.full((3, 192, 192), 0.08, dtype=np.float32)
    parent = context[:, 16:-16, 16:-16]
    assert _spacing(packed, colors, 151, 149, clearance=16) is not None
    restored = refine_raw_mesh_carriers(
        parent,
        packed,
        colors,
        (151, 149, 160, 160),
        shot=0.00128,
        read=6.5536e-6,
        white_balance=np.ones(3),
        camera_to_srgb=np.eye(3),
        method="pooled-color",
        parent_context=context,
    )
    np.testing.assert_array_equal(restored, parent)
