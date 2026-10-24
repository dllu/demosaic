import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import tifffile
import torch

from demosaic.cfa import color_indices, pack, unpack
from demosaic.cli import main, parser
from demosaic.inference import restore_tiled
from demosaic.io import write_rgb16
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.self_ensemble import predict_dihedral8


def numpy_view(value, index):
    value = np.rot90(value, index % 4, axes=(-2, -1))
    return (np.flip(value, -1) if index >= 4 else value).copy()


def test_all_cfa_phases_variances_and_inverse_geometry_against_numpy():
    torch.set_num_threads(2)
    rgb = np.arange(4 * 3 * 26 * 38, dtype=np.float32).reshape(4, 3, 26, 38) / 8000 - .2
    colors = torch.stack([color_indices(p) for p in ['RGGB', 'BGGR', 'GRBG', 'GBRG']])
    raw = np.empty((4, 1, 26, 38), dtype=np.float32)
    for b in range(4):
        for phase, channel in enumerate(colors[b].tolist()):
            y, x = divmod(phase, 2)
            raw[b, 0, y::2, x::2] = rgb[b, channel, y::2, x::2]
    packed = pack(torch.from_numpy(raw))
    variance = torch.arange(packed.numel(), dtype=torch.float32).reshape_as(packed) / 1e9
    wb, matrix = torch.ones(4, 3), torch.eye(3)[None].repeat(4, 1, 1)
    original = [t.clone() for t in [packed, variance, colors, wb, matrix]]
    rng = torch.random.get_rng_state().clone()

    class Oracle(torch.nn.Module):
        calls = 0

        def forward(self, samples, noise, cfa, camera_wb, camera_matrix):
            i = self.calls
            expected_raw = numpy_view(raw, i)
            expected_noise = numpy_view(unpack(variance).numpy(), i)
            for actual, value in [(samples, expected_raw), (noise, expected_noise)]:
                expected = np.concatenate(
                    [value[..., y::2, x::2] for y, x in [(0, 0), (0, 1), (1, 0), (1, 1)]],
                    axis=1,
                )
                np.testing.assert_array_equal(actual.numpy(), expected)
            expected_colors = numpy_view(colors.numpy().reshape(4, 2, 2), i).reshape(4, 4)
            np.testing.assert_array_equal(cfa.numpy(), expected_colors)
            assert camera_wb is wb and camera_matrix is matrix
            self.calls += 1
            return torch.from_numpy(numpy_view(rgb, i))

    model = Oracle().eval()
    actual = predict_dihedral8(model, packed, variance, colors, wb, matrix)
    np.testing.assert_array_equal(actual.numpy(), rgb)
    assert model.calls == 8 and actual.dtype == torch.float32
    assert packed.min() < 0 and packed.max() > 1
    assert all(torch.equal(a, b) for a, b in zip(original, [packed, variance, colors, wb, matrix]))
    assert torch.equal(torch.random.get_rng_state(), rng)


def test_mean_uses_unclipped_linear_rgb_and_float64_reduction():
    class Values(torch.nn.Module):
        calls = 0

        def forward(self, raw, _variance, _colors, wb, matrix):
            assert wb is None and matrix is None
            values = [-.5, -.25, 0, .125, .25, .5, 1, 2]
            output = torch.full((1, 3, 2 * raw.shape[-2], 2 * raw.shape[-1]), values[self.calls])
            self.calls += 1
            return output

    raw = torch.zeros(1, 4, 5, 9)
    actual = predict_dihedral8(Values().eval(), raw, raw, color_indices('GRBG'))
    expected = float(np.mean(np.array([-.5, -.25, 0, .125, .25, .5, 1, 2], dtype=np.float64)))
    assert torch.equal(actual, torch.full((1, 3, 10, 18), expected))


class SensorView(torch.nn.Module):
    calls = 0

    def forward(self, samples, *_args):
        self.calls += 1
        return unpack(samples).expand(-1, 3, -1, -1)


def test_odd_multitile_native_output_and_rgb16_precision(tmp_path):
    raw = np.linspace(-.02, 1.02, 69 * 73, dtype=np.float32).reshape(69, 73)
    kwargs = {'shot': .001, 'read': 1e-6, 'tile': 64, 'overlap': 18, 'batch_size': 3, 'device': 'cpu'}
    single, original_stats = restore_tiled(SensorView(), raw, color_indices('GBRG'), **kwargs)
    model = SensorView()
    ensemble, stats = restore_tiled(
        model, raw, color_indices('GBRG'), self_ensemble='dihedral8', **kwargs
    )
    torch.testing.assert_close(ensemble, single, rtol=0, atol=0)
    torch.testing.assert_close(ensemble, torch.from_numpy(raw)[None].expand(3, -1, -1), rtol=0, atol=2e-7)
    assert stats['self_ensemble'] == 'dihedral8' and stats['model_views_per_tile'] == 8
    assert original_stats['self_ensemble'] == 'none' and original_stats['model_views_per_tile'] == 1
    assert model.calls == 8 * ((stats['tiles'] + 2) // 3)
    path = tmp_path / 'ensemble.tiff'
    write_rgb16(path, ensemble.permute(1, 2, 0).numpy())
    pixels = tifffile.imread(path)
    assert pixels.dtype == np.uint16 and pixels.shape == (69, 73, 3)
    np.testing.assert_array_equal(pixels, np.rint(np.clip(ensemble.permute(1, 2, 0).numpy(), 0, 1) * 65535).astype(np.uint16))
    assert len(np.unique(pixels)) > 256


def test_invalid_policy_and_training_mode_fail_before_inference():
    model = SensorView()
    with pytest.raises(ValueError, match='policy'):
        restore_tiled(model, np.zeros((32, 32)), color_indices('RGGB'), shot=0, read=0,
                      tile=32, overlap=0, device='cpu', self_ensemble='invalid')
    with pytest.raises(ValueError, match='evaluation-mode'):
        predict_dihedral8(model, torch.zeros(1, 4, 16, 16), torch.zeros(1, 4, 16, 16), color_indices('RGGB'))
    assert model.calls == 0


def test_actual_cli_inference_records_policy_and_writes_native_rgb16(tmp_path):
    model = JointDemosaic(ModelConfig(width=4, encoder_blocks=(0, 0, 0), middle_blocks=0,
                                      decoder_blocks=(0, 0, 0), attention=False)).eval()
    checkpoint, source, output = (tmp_path / name for name in ['tiny.pt', 'input.npy', 'output.tiff'])
    torch.save({'model_config': model.config.to_dict(), 'model': model.restoration_state_dict()}, checkpoint)
    np.save(source, np.linspace(0, 65535, 33 * 35, dtype=np.uint16).reshape(33, 35))
    main(['infer', str(checkpoint), str(source), str(output), '--device', 'cpu',
          '--tile', '32', '--overlap', '0', '--precision', 'float32', '--shot', '0', '--read', '0',
          '--self-ensemble', 'dihedral8'])
    pixels = tifffile.imread(output)
    receipt = json.loads(output.with_suffix('.json').read_text())
    assert pixels.dtype == np.uint16 and pixels.shape == (33, 35, 3)
    assert receipt['self_ensemble'] == 'dihedral8' and receipt['model_views_per_tile'] == 8
    assert receipt['megapixels'] == 33 * 35 / 1e6


def test_benchmark_and_dng_parser_expose_explicit_optional_policy(tmp_path):
    args = parser().parse_args(['benchmark', 'weights.pt', '--output', str(tmp_path / 'speed.json'),
                                '--self-ensemble', 'dihedral8'])
    assert args.self_ensemble == 'dihedral8'
    spec = importlib.util.spec_from_file_location('export_raw_dng', Path('scripts/export_raw_dng.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module.parser().parse_args(['weights.pt', 'source.raf', '--output-dir', str(tmp_path),
                                       '--self-ensemble', 'dihedral8'])
    assert args.self_ensemble == 'dihedral8'
