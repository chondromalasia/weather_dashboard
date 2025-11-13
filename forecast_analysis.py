import os
import requests
import logging
from flask import Blueprint, render_template, jsonify
from forecast_comparison import create_forecast_comparison_df, error_histogram, get_comparison_summary

# Create a Blueprint for forecast analysis
forecast_bp = Blueprint('forecast', __name__)

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
WEATHER_API_URL = os.getenv('WEATHER_API_URL', 'http://weather-api-service')


@forecast_bp.route('/forecast-analysis')
def forecast_analysis():
    """Render the forecast analysis page."""
    return render_template('forecast_analysis.html')


@forecast_bp.route('/api/forecast/locations')
def get_forecast_locations():
    """Fetch available forecast locations from the weather API."""
    try:
        logger.info(f"Fetching forecast locations from: {WEATHER_API_URL}/forecast/locations")
        response = requests.get(f"{WEATHER_API_URL}/forecast/locations", timeout=10)
        logger.info(f"Response status: {response.status_code}")
        response.raise_for_status()
        locations = response.json()
        logger.info(f"Successfully fetched forecast locations")
        return jsonify(locations)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch forecast locations: {e}")
        return jsonify({
            "error": f"Unable to fetch forecast locations",
            "details": str(e)
        }), 500


@forecast_bp.route('/api/forecast/providers')
def get_forecast_providers():
    """Fetch available forecast providers from the weather API."""
    try:
        logger.info(f"Fetching forecast providers from: {WEATHER_API_URL}/forecast/providers")
        response = requests.get(f"{WEATHER_API_URL}/forecast/providers", timeout=10)
        logger.info(f"Response status: {response.status_code}")
        response.raise_for_status()
        providers = response.json()
        logger.info(f"Successfully fetched forecast providers")
        return jsonify(providers)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch forecast providers: {e}")
        return jsonify({
            "error": f"Unable to fetch forecast providers",
            "details": str(e)
        }), 500


@forecast_bp.route('/api/forecast/highs')
def get_forecast_highs():
    """Fetch forecast highs from the weather API."""
    from flask import request

    location = request.args.get('location')
    provider = request.args.get('provider')

    if not location or not provider:
        return jsonify({
            "error": "Missing required parameters",
            "details": "Both location and provider are required"
        }), 400

    try:
        url = f"{WEATHER_API_URL}/forecast/highs?location={location}&provider={provider}"
        logger.info(f"Fetching forecast highs from: {url}")
        response = requests.get(url, timeout=10)
        logger.info(f"Response status: {response.status_code}")
        response.raise_for_status()
        highs = response.json()
        logger.info(f"Successfully fetched forecast highs")
        return jsonify(highs)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch forecast highs: {e}")
        return jsonify({
            "error": f"Unable to fetch forecast highs",
            "details": str(e)
        }), 500


@forecast_bp.route('/api/observations/highs')
def get_observation_highs():
    """Fetch observation highs from the weather API."""
    from flask import request

    station_id = request.args.get('station_id')
    service = request.args.get('service')
    start = request.args.get('start')

    if not station_id or not service or not start:
        return jsonify({
            "error": "Missing required parameters",
            "details": "station_id, service, and start are required"
        }), 400

    try:
        url = f"{WEATHER_API_URL}/observations/highs?station_id={station_id}&service={service}&start={start}"
        logger.info(f"Fetching observation highs from: {url}")
        response = requests.get(url, timeout=10)
        logger.info(f"Response status: {response.status_code}")
        response.raise_for_status()
        observations = response.json()
        logger.info(f"Successfully fetched observation highs")
        return jsonify(observations)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch observation highs: {e}")
        return jsonify({
            "error": f"Unable to fetch observation highs",
            "details": str(e)
        }), 500


@forecast_bp.route('/api/forecast/comparison')
def get_forecast_comparison():
    """Fetch forecast and observation data, then create comparison analysis."""
    from flask import request

    location = request.args.get('location')
    provider = request.args.get('provider')

    if not location or not provider:
        return jsonify({
            "error": "Missing required parameters",
            "details": "Both location and provider are required"
        }), 400

    try:
        # Fetch forecast data
        forecast_url = f"{WEATHER_API_URL}/forecast/highs?location={location}&provider={provider}"
        logger.info(f"Fetching forecast highs from: {forecast_url}")
        forecast_response = requests.get(forecast_url, timeout=10)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        # Get oldest date from forecasts
        if not forecast_data.get('forecasted_highs') or len(forecast_data['forecasted_highs']) == 0:
            return jsonify({
                "error": "No forecast data available",
                "details": "Cannot create comparison without forecast data"
            }), 404

        oldest_date = forecast_data['forecasted_highs'][0]['date']

        # Fetch observation data starting from oldest forecast date
        observation_url = f"{WEATHER_API_URL}/observations/highs?station_id={location}&service=CLI&start={oldest_date}"
        logger.info(f"Fetching observation highs from: {observation_url}")
        observation_response = requests.get(observation_url, timeout=10)
        observation_response.raise_for_status()
        observation_data = observation_response.json()

        # Get the most recent forecast (forecast with the maximum date)
        most_recent_forecast = None
        if forecast_data.get('forecasted_highs') and len(forecast_data['forecasted_highs']) > 0:
            most_recent = max(forecast_data['forecasted_highs'], key=lambda x: x['date'])
            most_recent_forecast = {
                "date": most_recent['date'],
                "forecasted_high": most_recent['forecasted_high']
            }

        # Create comparison dataframe
        comparison_df = create_forecast_comparison_df(forecast_data, observation_data)

        # Get summary statistics
        summary = get_comparison_summary(comparison_df)

        # Get error histogram
        histogram = error_histogram(comparison_df, bias=True)

        # Convert dataframe to dict for JSON serialization
        return jsonify({
            "location": location,
            "provider": provider,
            "oldest_date": oldest_date,
            "most_recent_forecast": most_recent_forecast,
            "summary": summary,
            "error_histogram": histogram.to_dict(orient='records')
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch comparison data: {e}")
        return jsonify({
            "error": f"Unable to fetch comparison data",
            "details": str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error creating comparison: {e}")
        return jsonify({
            "error": f"Unable to create comparison",
            "details": str(e)
        }), 500
