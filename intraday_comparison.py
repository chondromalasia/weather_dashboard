"""Intraday temperature comparison page.

Scoped deliberately small for now: KNYC only, one day at a time, and only
the Wunderground PWS temperature traces. The plan is to layer NWS hourly
forecast, NBM, and METAR observations onto the same chart later — this is
the plumbing for that.

Wunderground observations live in weather-api's `observations` table as
sub-hourly `instant` rows, tagged with each PWS station's own id (not
"KNYC"). `/observations/highs` can't return them (it filters
`observation_type='max'`), so this uses the raw `/observations/all`
passthrough. Timestamps in/out are epoch seconds; the local day boundary
is computed in America/New_York and passed as explicit epochs so it
doesn't depend on weather-api's per-location timezone lookup (which has no
entry for PWS station ids).
"""

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from flask import Blueprint, jsonify, render_template, request

intraday_bp = Blueprint('intraday', __name__)
logger = logging.getLogger(__name__)

WEATHER_API_URL = os.getenv('WEATHER_API_URL', 'http://weather-api-service')

# KNYC only for now. These PWS station ids are the ones weather-fetcher's
# config.yaml (`locations[].pws_stations`) posts under for KNYC — that repo
# is the source of truth if this list needs to change.
LOCATION = 'KNYC'
LOCATION_TZ = 'America/New_York'
PWS_STATIONS = ['KNYNEWYO1686', 'KNYNEWYO270', 'KNYNEWYO1796']

# NWS reported temperature: hourly METAR observations pulled live from
# api.weather.gov (not stored in weather-api — the only NWS observation
# there is the once-a-day CLI high/low). api.weather.gov requires a
# User-Agent identifying the caller.
NWS_API_URL = 'https://api.weather.gov'
NWS_STATION = 'KNYC'
# api.weather.gov asks callers to identify themselves and to include a
# contact. Set NWS_USER_AGENT to something like
# "my-app (you@example.com)" in the deploy env.
NWS_USER_AGENT = os.getenv('NWS_USER_AGENT', 'weather-dashboard/intraday-comparison')


def _api_get(path, params, timeout=30):
    url = f"{WEATHER_API_URL}/{path}"
    logger.info(f"GET {url} {params}")
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


# The "1-hour change" pairs a station's latest reading with whichever
# earlier reading sits closest to exactly one hour before it — not one hour
# before "now". A station that last reported at 10:14 is compared against
# ~9:14 even if the clock now says 10:40. If the closest earlier reading is
# more than this far off that mark (a data gap, or the station only started
# reporting recently), there's no honest 1-hour delta and it's reported as
# null.
LAST_HOUR_TOLERANCE_SECONDS = 20 * 60


def _iso_utc(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# --- Hardcoded hourly-change ladder model --------------------------------
# Multinomial logistic on the integer METAR hourly change (classes -3..+3 °F,
# the ends are catch-alls), from
#   weather/notebooks/Weather Analysis/PWS-METAR Hourly Ordinal Nowcast - KNYC.ipynb
# (fit 2026-08-28; held-out ladder log-loss ~0.27 vs ~0.36 for a time-of-day
# climatology baseline). The class probabilities give P(METAR(t) >= k) for the
# Kalshi hourly threshold ladder. Frozen snapshot — refit from the notebook.
#
# Feature order (10):
#   incr_1686, lvl_1686, incr_1796, lvl_1796, incr_270, lvl_270, prev_change,
#   tod_morning, tod_midday, tod_afternoon      (night = reference)
# where  incr_s = station latest temp - its reading ~1h earlier   [= last_hour_delta]
#        lvl_s  = station latest temp - metar_prev
#        prev_change = metar_prev - the METAR before it
# A station with no usable ~1h delta contributes 0 (matches the notebook fillna).
# The first seven (continuous) features are standardised before the linear layer.
# Refit 2026-08-31 on the full 2-year backfill (2024-08-27..) with all three
# KNYC PWS stations; 1796 is the densest/cleanest and now carries most weight.
NOWCAST_MODEL_TAG = 'mnl-change 3sta @ 2026-08-31'
NOWCAST_CLASSES = [-3, -2, -1, 0, 1, 2, 3]
NOWCAST_SCALER_MEAN = [0.0133964, 1.2573, 0.00262, 1.55098, -0.00137694, 1.14194, -0.00516351]
NOWCAST_SCALER_SCALE = [1.28294, 1.48708, 1.43336, 1.56256, 1.69688, 2.14837, 1.56039]
NOWCAST_INTERCEPT = [-3.00373, -0.245291, 2.19107, 2.88558, 1.63889, -1.08313, -2.38338]
NOWCAST_COEF = [
    [-0.825908, -0.998665, -1.11278, -1.56486, -1.65228, -0.0279741, 0.436493, -0.900043, -1.169, 0.318502],
    [-0.723712, -0.511558, -0.835749, -0.9506, -1.04971, -0.202573, 0.180271, -1.23985, -1.18944, 0.306263],
    [-0.298706, -0.0392245, -0.542871, -0.144196, -0.584903, -0.362838, 0.11271, -0.999427, -1.08159, -0.0234337],
    [0.18831, 0.152403, 0.0987927, 0.409545, 0.262543, -0.236917, -0.206568, -0.327447, -0.402684, -0.0402158],
    [0.440161, 0.273064, 0.643926, 0.617229, 0.667525, 0.0358211, -0.261062, 0.375499, 0.371259, -0.248207],
    [0.531728, 0.449303, 0.800662, 0.749726, 1.08439, 0.302708, -0.210565, 1.75832, 1.86047, 0.321306],
    [0.688127, 0.674677, 0.948014, 0.883156, 1.27244, 0.491773, -0.051279, 1.33295, 1.61098, -0.634214],
]

# k relative to round(metar_prev) to show on the ladder.
NOWCAST_LADDER_SPAN = (-2, 6)

# Held-out ladder log-loss by local-time band (model vs the no-model baseline).
NOWCAST_LADDER_LOGLOSS = {
    '05-10 morning': {'model': 0.22, 'baseline': 0.41},
    '10-15 midday': {'model': 0.35, 'baseline': 0.45},
    '15-20 afternoon': {'model': 0.29, 'baseline': 0.40},
    '20-05 night': {'model': 0.21, 'baseline': 0.30},
}


def _tod_band(hour):
    if 5 <= hour < 10:
        return '05-10 morning'
    if 10 <= hour < 15:
        return '10-15 midday'
    if 15 <= hour < 20:
        return '15-20 afternoon'
    return '20-05 night'


def _softmax(logits):
    top = max(logits)
    exps = [math.exp(v - top) for v in logits]
    total = sum(exps)
    return [v / total for v in exps]


def _station_change_features(series, station_id, metar_prev):
    """(incr, lvl, used) for one PWS station. incr = its ~1h change (the
    `last_hour_delta`), lvl = its latest reading minus `metar_prev`. Returns
    zeros with used=False when the station has no usable ~1h delta."""
    s = next((x for x in series
              if x['source'] == 'wunderground' and x['station_id'] == station_id), None)
    latest = s['points'][-1]['temp_f'] if s and s['points'] else None
    delta = s['last_hour_delta'] if s else None
    incr = delta['delta_f'] if delta else None
    lvl = round(latest - metar_prev, 2) if latest is not None else None
    if incr is None or lvl is None:
        return 0.0, 0.0, False
    return incr, lvl, True


def _compute_nowcast(series, metar_points, now_local):
    """Hardcoded multinomial-logistic nowcast of the next METAR's *change* from
    the last one, turned into a P(METAR(t) >= k) ladder.

    Returns {'available': False, 'reason': ...} when it can't be run.
    """
    if len(metar_points) < 2:
        return {'available': False, 'reason': 'need at least two METAR obs today'}

    metar_prev = metar_points[-1]['temp_f']
    prev_change = round(metar_prev - metar_points[-2]['temp_f'], 2)
    band = _tod_band(now_local.hour)

    incr_1686, lvl_1686, used_1686 = _station_change_features(series, 'KNYNEWYO1686', metar_prev)
    incr_1796, lvl_1796, used_1796 = _station_change_features(series, 'KNYNEWYO1796', metar_prev)
    incr_270, lvl_270, used_270 = _station_change_features(series, 'KNYNEWYO270', metar_prev)

    feats = [
        incr_1686, lvl_1686, incr_1796, lvl_1796, incr_270, lvl_270, prev_change,
        1.0 if band == '05-10 morning' else 0.0,
        1.0 if band == '10-15 midday' else 0.0,
        1.0 if band == '15-20 afternoon' else 0.0,
    ]
    # standardise the seven continuous features
    z = list(feats)
    for i, (mean, scale) in enumerate(zip(NOWCAST_SCALER_MEAN, NOWCAST_SCALER_SCALE)):
        z[i] = (feats[i] - mean) / scale

    logits = [
        b + sum(w * zj for w, zj in zip(row, z))
        for b, row in zip(NOWCAST_INTERCEPT, NOWCAST_COEF)
    ]
    probs = _softmax(logits)
    class_probs = [{'change': c, 'p': round(p, 4)} for c, p in zip(NOWCAST_CLASSES, probs)]
    expected_change = round(sum(c * p for c, p in zip(NOWCAST_CLASSES, probs)), 2)
    mode = max(range(len(probs)), key=probs.__getitem__)

    kbase = int(round(metar_prev))
    lo, hi = NOWCAST_LADDER_SPAN
    ladder = []
    for rel in range(lo, hi + 1):
        if rel <= NOWCAST_CLASSES[0]:
            p_ge = 1.0
        elif rel > NOWCAST_CLASSES[-1]:
            p_ge = 0.0
        else:
            p_ge = sum(p for c, p in zip(NOWCAST_CLASSES, probs) if c >= rel)
        ladder.append({'k': kbase + rel, 'p_ge': round(p_ge, 4)})

    return {
        'available': True,
        'model': NOWCAST_MODEL_TAG,
        'metar_prev_f': metar_prev,
        'metar_prev_t': metar_points[-1]['t'],
        'tod_band': band,
        'kbase': kbase,
        'class_probs': class_probs,
        'expected_change_f': expected_change,
        'most_likely': {
            'temp_f': kbase + NOWCAST_CLASSES[mode],
            'change': NOWCAST_CLASSES[mode],
            'p': round(probs[mode], 3),
        },
        'ladder': ladder,
        'inputs': {
            'KNYNEWYO1686': {'incr_f': round(incr_1686, 2), 'lvl_f': round(lvl_1686, 2),
                             'used': used_1686},
            'KNYNEWYO1796': {'incr_f': round(incr_1796, 2), 'lvl_f': round(lvl_1796, 2),
                             'used': used_1796},
            'KNYNEWYO270': {'incr_f': round(incr_270, 2), 'lvl_f': round(lvl_270, 2),
                            'used': used_270},
            'prev_change_f': prev_change,
        },
        'reliability': NOWCAST_LADDER_LOGLOSS[band],
    }


def _last_hour_delta(points):
    """Temperature change from ~1h before the latest reading to the latest
    reading. `points` must be sorted ascending by `t`. Returns None when it
    can't be computed honestly (fewer than 2 points, or no earlier reading
    close enough to the one-hour mark)."""
    if len(points) < 2:
        return None

    latest = points[-1]
    target = latest['t'] - 3600
    reference = min(points[:-1], key=lambda p: abs(p['t'] - target))
    if abs(reference['t'] - target) > LAST_HOUR_TOLERANCE_SECONDS:
        return None

    return {
        'delta_f': round(latest['temp_f'] - reference['temp_f'], 1),
        'from': {'t': reference['t'], 'temp_f': reference['temp_f']},
        'to': {'t': latest['t'], 'temp_f': latest['temp_f']},
        'span_minutes': round((latest['t'] - reference['t']) / 60),
    }


def _fetch_nws_observations(station, start_epoch, end_epoch):
    """Hourly METAR temperatures for the local day, from api.weather.gov.

    Temperatures come back in Celsius; converted to Fahrenheit here to match
    everything else on the chart. Returns points sorted ascending by time.
    """
    response = requests.get(
        f"{NWS_API_URL}/stations/{station}/observations",
        params={'start': _iso_utc(start_epoch), 'end': _iso_utc(end_epoch), 'limit': 500},
        headers={'User-Agent': NWS_USER_AGENT, 'Accept': 'application/geo+json'},
        timeout=30,
    )
    response.raise_for_status()

    points = []
    for feature in response.json().get('features', []):
        props = feature.get('properties') or {}
        temp_c = (props.get('temperature') or {}).get('value')
        ts = props.get('timestamp')
        if temp_c is None or not ts:
            continue
        t = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp())
        if not (start_epoch <= t < end_epoch):
            continue
        points.append({
            't': t,
            'hour': round((t - start_epoch) / 3600, 4),
            'temp_f': round(temp_c * 9 / 5 + 32, 1),
        })
    points.sort(key=lambda p: p['t'])
    return points


@intraday_bp.route('/intraday-comparison')
def intraday_comparison():
    return render_template('intraday_comparison.html')


@intraday_bp.route('/api/intraday/temperature')
def intraday_temperature():
    tz = ZoneInfo(LOCATION_TZ)

    date_str = request.args.get('date')
    try:
        day = (
            datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_str else datetime.now(tz).date()
        )
    except ValueError:
        return jsonify({"error": "date must be in YYYY-MM-DD format"}), 400

    start_local = datetime(day.year, day.month, day.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start_epoch = int(start_local.timestamp())
    end_epoch = int(end_local.timestamp())

    metar_points = []
    series = []
    errors = []
    for station_id in PWS_STATIONS:
        try:
            data = _api_get('observations/all', {
                'station_id': station_id,
                'measurement_type': 'temperature',
                'service': 'wunderground',
                'start': start_epoch,
                'end': end_epoch - 1,
            })
        except requests.exceptions.RequestException as e:
            logger.error(f"intraday: failed to fetch {station_id}: {e}")
            errors.append({'station_id': station_id, 'error': str(e)})
            continue

        points = []
        for obs in data.get('observations', []):
            if obs.get('value') is None:
                continue
            t = obs['timestamp']
            points.append({
                't': t,
                # fractional hour of the local day, for a 0–24 x-axis
                'hour': round((t - start_epoch) / 3600, 4),
                'temp_f': float(obs['value']),
            })
        series.append({
            'source': 'wunderground',
            'station_id': station_id,
            'points': points,
            'last_hour_delta': _last_hour_delta(points),
        })

    try:
        metar_points = _fetch_nws_observations(NWS_STATION, start_epoch, end_epoch)
        series.append({
            'source': 'nws_metar',
            'station_id': f'{NWS_STATION} (NWS obs)',
            'points': metar_points,
            'last_hour_delta': _last_hour_delta(metar_points),
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"intraday: failed to fetch NWS observations: {e}")
        errors.append({'station_id': f'{NWS_STATION} (NWS obs)', 'error': str(e)})

    now_local = datetime.now(tz)
    nowcast = _compute_nowcast(series, metar_points, now_local) if day == now_local.date() else None

    return jsonify({
        'location': LOCATION,
        'date': day.isoformat(),
        'timezone': LOCATION_TZ,
        'start': start_epoch,
        'end': end_epoch,
        'series': series,
        'errors': errors,
        'nowcast': nowcast,
    })
