import os
import requests
import logging
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WEATHER_API_URL = os.getenv('WEATHER_API_URL', 'http://weather-api-service')

@app.route('/')
def home():
    try:
        logger.info(f"Attempting to connect to: {WEATHER_API_URL}/")
        response = requests.get(f"{WEATHER_API_URL}/", timeout=10)
        logger.info(f"Response status: {response.status_code}")
        response.raise_for_status()
        api_data = response.json()
        logger.info(f"Successfully connected to weather API")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to weather API at {WEATHER_API_URL}/: {e}")
        api_data = {
            "error": f"Unable to connect to weather API at {WEATHER_API_URL}",
            "details": str(e)
        }
    
    return render_template('index.html', api_status=api_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
