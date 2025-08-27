import os
import requests
import logging
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WEATHER_API_URL = os.getenv('WEATHER_API_URL', 'http://weather-dashboard-service')

@app.route('/')
def home():
    try:
        response = requests.get(f"{WEATHER_API_URL}/", timeout=10)
        response.raise_for_status()
        api_data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to weather API: {e}")
        api_data = {"error": "Unable to connect to weather API"}
    
    return render_template('index.html', api_status=api_data)

@app.route('/api/status')
def get_api_status():
    try:
        response = requests.get(f"{WEATHER_API_URL}/", timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to weather API: {e}")
        return jsonify({"error": "Unable to connect to weather API"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
