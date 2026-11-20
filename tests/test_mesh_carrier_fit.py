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
        "weak-near-phase",
        "weak-replicated-phase",
        "weak-internal-phase",
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
    (
        "pooled",
        "pooled-color",
        "weak-posterior",
        "weak-phase-guard",
        "weak-phase-contrast",
        "weak-near-phase",
        "weak-replicated-phase",
        "weak-internal-phase",
    ),
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


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_near_phase_rejects_a_true_gap_inside_eligible_surroundings(pattern):
    from demosaic._mesh_near_phase import _near_taper
    from demosaic.mesh_carrier_fit import _positions

    origin = (151, 149)
    y, x = np.indices((480, 480), dtype=np.float64)
    frequencies = np.array(((0.1171875, 0.07421875), (0.08984375, -0.072265625)))
    strong = 0.014 * np.cos(2 * np.pi * (frequencies[0, 0] * x + frequencies[0, 1] * y))
    weak = 0.006 * np.cos(2 * np.pi * (frequencies[1, 0] * x + frequencies[1, 1] * y) - 0.8)
    inside = (x >= origin[0]) & (x < origin[0] + 160) & (y >= origin[1]) & (y < origin[1] + 160)
    gap = inside & (abs(x - 230.5) < 29)
    raw = pack(0.08 + strong + np.where(gap, 0, weak))
    eligible, weight = _near_taper(
        raw, origin, _positions(PATTERNS[pattern], *origin), frequencies, 1, 0.00128, 6.5536e-6
    )
    assert eligible.min() == 1
    assert weight[:, :32].mean() > 0.9
    assert weight[:, 68:92].mean() < 0.05


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_replicated_phase_requires_two_aligned_stations_and_caps_their_extent(pattern):
    from demosaic._mesh_near_phase import _replicated_taper
    from demosaic.mesh_carrier_fit import _positions

    origin = (151, 149)
    x0, y0 = origin
    y, x = np.indices((480, 480), dtype=np.float64)
    frequencies = np.asarray(((0.115, 0.074), (0.089, -0.079)))
    phase = 2 * np.pi * (x[..., None] * frequencies[:, 0] + y[..., None] * frequencies[:, 1])
    strong, weak = (0.018 * np.cos(phase + (0.8, -0.7))).transpose(2, 0, 1)
    crop = np.s_[y0 : y0 + 160, x0 : x0 + 160]
    upper = np.s_[y0 + 64 : y0 + 80, x0 + 64 : x0 + 80]
    lower = np.s_[y0 + 80 : y0 + 96, x0 + 80 : x0 + 96]
    raw = 0.09 + strong + weak
    raw[crop] -= weak[crop]
    raw[upper] += weak[upper]
    positions = _positions(PATTERNS[pattern], *origin)

    def strength(mosaic):
        return _replicated_taper(pack(mosaic), origin, positions, frequencies, 1, 0.0001, 6e-7)

    assert not strength(raw).any()
    raw[lower] += weak[lower]
    weight = strength(raw)
    allowed = np.zeros_like(weight, dtype=bool)
    allowed[64:80, 64:80] = True
    allowed[80:96, 80:96] = True
    assert weight[72, 72] > 0.8
    assert weight[88, 88] > 0.8
    assert not weight[~allowed].any()

    # A second station with only one supporting green cannot validate the pair.
    row, column = positions[0]
    raw[lower][row::2, column::2] -= weak[lower][row::2, column::2]
    assert not strength(raw).any()


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_replicated_phase_recovers_both_equally_ranked_wires(pattern):
    y, x = np.indices((480, 480), dtype=np.float64)
    raw = (
        0.08
        + 0.003 * np.cos(2 * np.pi * (0.1171875 * x + 0.07421875 * y) + 0.8)
        + 0.003 * np.cos(2 * np.pi * (0.08984375 * x - 0.072265625 * y) - 0.9)
    ).astype(np.float32)
    context = np.full((3, 192, 192), 0.08, dtype=np.float32)
    parent = context[:, 16:-16, 16:-16]
    arguments = (parent, pack(raw), PATTERNS[pattern], (151, 149, 160, 160))
    options = {
        "shot": 0.00128,
        "read": 6.5536e-6,
        "white_balance": np.ones(3),
        "camera_to_srgb": np.eye(3),
        "parent_context": context,
    }
    baseline = refine_raw_mesh_carriers(*arguments, method="weak-near-phase", **options)
    revised = refine_raw_mesh_carriers(*arguments, method="weak-replicated-phase", **options)
    target = raw[165:293, 167:295]
    baseline_error = np.mean((baseline[:, 16:-16, 16:-16] - target) ** 2)
    revised_error = np.mean((revised[:, 16:-16, 16:-16] - target) ** 2)
    assert revised_error < 0.8 * baseline_error


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_internal_phase_excludes_the_held_station_and_its_neighbors(pattern):
    from demosaic._mesh_internal_phase import _estimate_phases, _pool_phase
    from demosaic.mesh_carrier_fit import _positions

    origin = (151, 149)
    frequencies = np.asarray(((0.1171875, 0.07421875), (0.08984375, -0.072265625)))
    sites = _positions(PATTERNS[pattern], *origin)
    greens = tuple(2 * row + column for row, column in sites)
    x, y = origin
    station_y, station_x = 3, 4
    index = 10 * station_y + station_x
    top, left = y + (station_y - 1) * 16, x + (station_x - 1) * 16
    raw = scene_fixture()
    edited = raw.copy()
    edited[top : top + 48, left : left + 48] = np.random.default_rng(60).uniform(
        0.01, 0.20, (48, 48)
    )

    def estimate(mosaic):
        coefficients, precision = _estimate_phases(
            pack(mosaic), origin, frequencies, 0.00128, 6.5536e-6
        )
        return _pool_phase(coefficients[..., 0, :], precision[..., 0], frequencies[0], greens)

    original, valid = estimate(raw)
    changed, revised_valid = estimate(edited)
    assert valid[index] and revised_valid[index]
    np.testing.assert_array_equal(original[index], changed[index])


@pytest.mark.parametrize("pattern", tuple(PATTERNS))
def test_junction_phase_recovers_signed_interaction_and_leaves_additive_mesh(pattern):
    x, y = 151, 149
    v, u = np.indices((480, 480), dtype=np.float64)
    first = 2 * np.pi * (0.115234375 * u + 0.07421875 * v) + 0.4
    second = 2 * np.pi * (0.087890625 * u - 0.072265625 * v) - 0.8
    additive = (0.13 + 0.025 * np.cos(first) + 0.024 * np.cos(second)).astype(np.float32)
    interaction = -0.008 * np.cos(first - second)
    restored = np.repeat(additive[None], 3, axis=0)
    parent = restored[:, y : y + 160, x : x + 160]
    options = {
        "shot": 0.00128,
        "read": 6.5536e-6,
        "white_balance": np.ones(3),
        "camera_to_srgb": np.eye(3),
    }

    def refine(raw, method, halo):
        return refine_raw_mesh_carriers(
            parent,
            pack(raw.astype(np.float32)),
            PATTERNS[pattern],
            (x, y, 160, 160),
            method=method,
            parent_context=restored[:, y - halo : y + 160 + halo, x - halo : x + 160 + halo],
            **options,
        )

    with pytest.raises(ValueError, match="48-pixel halo"):
        refine(additive, "weak-junction-phase", 16)
    no_interaction = refine(additive, "weak-internal-phase", 16)
    np.testing.assert_array_equal(refine(additive, "weak-junction-phase", 48), no_interaction)

    old = refine(additive + interaction, "weak-internal-phase", 16)
    new = refine(additive + interaction, "weak-junction-phase", 48)
    truth = interaction[y + 16 : y + 144, x + 16 : x + 144]
    change = new[1, 16:144, 16:144] - old[1, 16:144, 16:144]
    assert (change * truth).sum() > 0.35 * (truth**2).sum()


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
