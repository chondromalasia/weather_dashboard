import os
import requests
import logging
from flask import Blueprint, render_template, jsonify

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
