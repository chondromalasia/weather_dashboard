"""Tests for the intraday comparison helpers — the hardcoded hourly-change
ladder nowcast and the 1-hour delta.
Run with pytest, or directly: python test_intraday_comparison.py
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from intraday_comparison import (
    NOWCAST_CLASSES,
    NOWCAST_LADDER_SPAN,
    _compute_nowcast,
    _last_hour_delta,
    _softmax,
    _tod_band,
)

NY_MIDDAY = datetime(2026, 8, 28, 12, 40, tzinfo=ZoneInfo("America/New_York"))


def _wunderground(station_id, latest_f, delta_f):
    return {
        "source": "wunderground",
        "station_id": station_id,
        "points": [{"t": 1, "temp_f": latest_f}] if latest_f is not None else [],
        "last_hour_delta": {"delta_f": delta_f} if delta_f is not None else None,
    }


def _metar(*temps):
    return [{"t": 100 * (i + 1), "temp_f": t} for i, t in enumerate(temps)]


def test_tod_band_boundaries():
    assert _tod_band(4) == "20-05 night"
    assert _tod_band(5) == "05-10 morning"
    assert _tod_band(10) == "10-15 midday"
    assert _tod_band(15) == "15-20 afternoon"
    assert _tod_band(19) == "15-20 afternoon"
    assert _tod_band(20) == "20-05 night"


def test_softmax_normalises():
    p = _softmax([1.0, 2.0, 3.0, -1.0])
    assert abs(sum(p) - 1.0) < 1e-12
    assert all(0.0 < x < 1.0 for x in p)
    assert p[2] == max(p)  # largest logit -> largest prob


def test_nowcast_needs_two_metar_obs():
    series = [_wunderground("KNYNEWYO1686", 73.0, 0.5)]
    assert _compute_nowcast(series, _metar(70.0), NY_MIDDAY) == {
        "available": False, "reason": "need at least two METAR obs today",
    }
    assert _compute_nowcast(series, [], NY_MIDDAY)["available"] is False


def test_nowcast_shape_and_ladder_monotonicity():
    series = [
        _wunderground("KNYNEWYO1686", 73.4, 0.8),
        _wunderground("KNYNEWYO1796", 73.6, 0.9),
        _wunderground("KNYNEWYO270", 74.0, 1.5),
    ]
    nc = _compute_nowcast(series, _metar(70.0, 71.0), NY_MIDDAY)

    assert nc["available"] is True
    assert nc["kbase"] == 71
    assert nc["metar_prev_f"] == 71.0
    assert nc["inputs"]["prev_change_f"] == 1.0
    assert {"KNYNEWYO1686", "KNYNEWYO1796", "KNYNEWYO270"} <= set(nc["inputs"])
    assert nc["inputs"]["KNYNEWYO1796"]["used"] is True

    probs = [c["p"] for c in nc["class_probs"]]
    assert [c["change"] for c in nc["class_probs"]] == NOWCAST_CLASSES
    assert abs(sum(probs) - 1.0) < 1e-6
    assert all(0.0 <= p <= 1.0 for p in probs)

    lo, hi = NOWCAST_LADDER_SPAN
    assert [r["k"] for r in nc["ladder"]] == [71 + rel for rel in range(lo, hi + 1)]
    pgs = [r["p_ge"] for r in nc["ladder"]]
    assert all(pgs[i] >= pgs[i + 1] for i in range(len(pgs) - 1)), pgs
    assert all(0.0 <= p <= 1.0 for p in pgs)

    ml = nc["most_likely"]
    assert ml["temp_f"] == nc["kbase"] + ml["change"]
    assert -3 <= nc["expected_change_f"] <= 3


def test_nowcast_missing_station_is_zeroed_not_fatal():
    series = [_wunderground("KNYNEWYO270", 74.0, 1.5)]  # 1686 absent entirely
    nc = _compute_nowcast(series, _metar(70.0, 71.0), NY_MIDDAY)

    assert nc["available"] is True
    assert nc["inputs"]["KNYNEWYO1686"]["used"] is False
    assert nc["inputs"]["KNYNEWYO1686"]["incr_f"] == 0.0
    assert nc["inputs"]["KNYNEWYO1796"]["used"] is False
    assert nc["inputs"]["KNYNEWYO270"]["used"] is True
    assert abs(sum(c["p"] for c in nc["class_probs"]) - 1.0) < 1e-6


def test_nowcast_positive_pws_trend_shifts_expectation_up():
    metar = _metar(70.0, 71.0)
    up = _compute_nowcast(
        [_wunderground("KNYNEWYO1686", 75.0, 2.5), _wunderground("KNYNEWYO1796", 75.0, 2.5),
         _wunderground("KNYNEWYO270", 75.0, 2.5)],
        metar, NY_MIDDAY,
    )
    down = _compute_nowcast(
        [_wunderground("KNYNEWYO1686", 68.0, -2.5), _wunderground("KNYNEWYO1796", 68.0, -2.5),
         _wunderground("KNYNEWYO270", 68.0, -2.5)],
        metar, NY_MIDDAY,
    )
    assert up["expected_change_f"] > down["expected_change_f"]
    assert up["ladder"][3]["p_ge"] > down["ladder"][3]["p_ge"]  # P(>= kbase+1)


def test_last_hour_delta_needs_two_points():
    assert _last_hour_delta([{"t": 1000, "temp_f": 70.0}]) is None


def test_last_hour_delta_picks_nearest_to_one_hour_back():
    points = [
        {"t": 0, "temp_f": 68.0},
        {"t": 3600, "temp_f": 70.0},
        {"t": 4200, "temp_f": 70.4},
        {"t": 7200, "temp_f": 72.5},
    ]
    d = _last_hour_delta(points)
    assert d["delta_f"] == 2.5
    assert d["from"]["t"] == 3600
    assert d["span_minutes"] == 60


def test_last_hour_delta_none_when_no_reference_near_one_hour():
    points = [{"t": 2400, "temp_f": 70.0}, {"t": 3600, "temp_f": 72.0}]
    assert _last_hour_delta(points) is None


if __name__ == "__main__":
    import traceback

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok   {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)
