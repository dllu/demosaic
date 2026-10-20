"""Local filenames must handle UTC date boundaries and daylight saving time."""

import datetime as dt
import json

import pytest

from diary import local_prefix, migrate, resolve


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-10-20T02:30:00+00:00", "2026-10-19-19-30-00"),
        ("2026-12-20T02:30:00+00:00", "2026-12-19-18-30-00"),
        ("2026-03-08T10:30:00+00:00", "2026-03-08-03-30-00"),
        ("2026-11-01T08:30:00+00:00", "2026-11-01-01-30-00"),
        ("2026-11-01T09:30:00+00:00", "2026-11-01-01-30-00"),
    ],
)
def test_timezone_conversion_includes_dst_and_previous_date(instant, expected):
    assert local_prefix(dt.datetime.fromisoformat(instant)) == expected


def test_naive_time_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        local_prefix(dt.datetime(2026, 10, 20))


def test_migration_preserves_body_and_resolves_historical_path(tmp_path):
    (tmp_path / "diary").mkdir()
    old = "diary/2026-10-20-02-30-00-example.md"
    new = "diary/2026-10-19-19-30-00-example.md"
    body = b"# Historical evidence\n\nLiteral UTC receipt stays unchanged.\n"
    (tmp_path / old).write_bytes(body)
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            [
                {
                    "path": old,
                    "new_path_if_UTC": new,
                    "kind": "UTC-candidate",
                    "UTC_delta_minutes": 0.2,
                    "local_delta_minutes": -419.8,
                    "birth_local": "2026-10-19T19:30:12-07:00",
                }
            ]
        )
    )
    assert len(migrate(tmp_path, audit)) == 1 and (tmp_path / old).exists()
    migrate(tmp_path, audit, apply=True)
    assert not (tmp_path / old).exists() and (tmp_path / new).read_bytes() == body
    assert resolve(tmp_path, old) == tmp_path / new
    assert resolve(tmp_path, new) == tmp_path / new
