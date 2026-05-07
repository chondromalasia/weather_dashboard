import os
import logging
import traceback
import requests
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request

from forecast_comparison import create_forecast_comparison_df, error_histogram, get_comparison_summary
from kalshi_edge import calculate_kalshi_edge

forecast_bp = Blueprint('forecast', __name__)
logger = logging.getLogger(__name__)
WEATHER_API_URL = os.getenv('WEATHER_API_URL', 'http://weather-api-service')


# --- Backend API helpers ---

def _api_get(path, timeout=120):
    url = f"{WEATHER_API_URL}/{path}"
    logger.info(f"GET {url}")
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _fetch_forecast_highs(location, provider):
    return _api_get(f"forecast/highs?location={location}&provider={provider}")


def _fetch_observations(location, start):
    return _api_get(f"observations/highs?station_id={location}&service=CLI&start={start}")


def _fetch_kalshi_markets(location):
    return _api_get(f"kalshi/market?location={location}")


def _most_recent_forecast(forecast_data):
    highs = forecast_data.get('forecasted_highs', [])
    today = datetime.utcnow().date()
    past = [f for f in highs if f['forecasted_high'] is not None and datetime.utcfromtimestamp(f['date']).date() <= today]
    if not past:
        return None
    f = max(past, key=lambda x: x['date'])
    return {
        "date": datetime.utcfromtimestamp(f['date']).strftime('%Y-%m-%d'),
        "forecasted_high": f['forecasted_high'],
    }


# --- Page routes ---

@forecast_bp.route('/forecast-analysis')
def forecast_analysis():
    return render_template('forecast_analysis.html')


@forecast_bp.route('/kalshi-comparison')
def kalshi_comparison():
    return render_template('kalshi_comparison.html')


# --- Passthrough API routes ---

@forecast_bp.route('/api/forecast/locations')
def get_forecast_locations():
    try:
        return jsonify(_api_get("forecast/locations"))
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch locations: {e}")
        return jsonify({"error": "Unable to fetch forecast locations", "details": str(e)}), 500


@forecast_bp.route('/api/forecast/providers')
def get_forecast_providers():
    try:
        return jsonify(_api_get("forecast/providers"))
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch providers: {e}")
        return jsonify({"error": "Unable to fetch forecast providers", "details": str(e)}), 500


@forecast_bp.route('/api/forecast/highs')
def get_forecast_highs():
    location = request.args.get('location')
    provider = request.args.get('provider')
    if not location or not provider:
        return jsonify({"error": "location and provider are required"}), 400
    try:
        return jsonify(_fetch_forecast_highs(location, provider))
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch forecast highs: {e}")
        return jsonify({"error": "Unable to fetch forecast highs", "details": str(e)}), 500


@forecast_bp.route('/api/observations/highs')
def get_observation_highs():
    station_id = request.args.get('station_id')
    service = request.args.get('service')
    start = request.args.get('start')
    if not station_id or not service or not start:
        return jsonify({"error": "station_id, service, and start are required"}), 400
    try:
        return jsonify(_api_get(f"observations/highs?station_id={station_id}&service={service}&start={start}"))
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch observations: {e}")
        return jsonify({"error": "Unable to fetch observation highs", "details": str(e)}), 500


# --- Analysis API routes ---

@forecast_bp.route('/api/forecast/comparison')
def get_forecast_comparison():
    location = request.args.get('location')
    provider = request.args.get('provider')
    if not location or not provider:
        return jsonify({"error": "location and provider are required"}), 400

    try:
        forecast_data = _fetch_forecast_highs(location, provider)
        if not forecast_data.get('forecasted_highs'):
            return jsonify({"error": "No forecast data available"}), 404

        oldest_date = forecast_data['forecasted_highs'][0]['date']
        obs_data = _fetch_observations(location, oldest_date)
        comparison_df = create_forecast_comparison_df(forecast_data, obs_data)

        return jsonify({
            "location": location,
            "provider": provider,
            "oldest_date": oldest_date,
            "most_recent_forecast": _most_recent_forecast(forecast_data),
            "summary": get_comparison_summary(comparison_df),
            "error_histogram": error_histogram(comparison_df, bias=True).to_dict(orient='records'),
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Comparison fetch failed: {e}")
        return jsonify({"error": "Unable to fetch comparison data", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        return jsonify({"error": "Unable to create comparison", "details": str(e)}), 500


@forecast_bp.route('/api/kalshi/comparison')
def get_kalshi_comparison():
    location = request.args.get('location')
    provider = request.args.get('provider')
    if not location or not provider:
        return jsonify({"error": "location and provider are required"}), 400

    try:
        forecast_data = _fetch_forecast_highs(location, provider)
        if not forecast_data.get('forecasted_highs'):
            return jsonify({"error": "No forecast data available"}), 404

        oldest_date = forecast_data['forecasted_highs'][0]['date']
        obs_data = _fetch_observations(location, oldest_date)
        kalshi_data = _fetch_kalshi_markets(location)

        recent = _most_recent_forecast(forecast_data)
        if not recent:
            return jsonify({"error": "No current forecast available"}), 404
        forecast_high = round(float(recent['forecasted_high']))

        comparison_df = create_forecast_comparison_df(forecast_data, obs_data)
        histogram = error_histogram(comparison_df, bias=True).to_dict(orient='records')
        edge_table = calculate_kalshi_edge(forecast_high, histogram, kalshi_data.get('markets', []))

        return jsonify({
            "location": location,
            "provider": provider,
            "forecast_date": recent['date'],
            "forecast_high": forecast_high,
            "sample_size": len(comparison_df),
            "edge_table": edge_table,
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Kalshi comparison fetch failed: {e}")
        return jsonify({"error": "Unable to fetch data", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Kalshi comparison error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Unable to compute comparison", "details": str(e)}), 500
