# Weather Dashboard

A Flask-based weather dashboard application that integrates with a weather API service.

## Endpoints

### Web Pages
- `GET /` - Main dashboard page showing API status
- `GET /forecast-analysis` - Forecast analysis page with location selector

### API Endpoints
- `GET /api/forecast/locations` - Fetch available forecast locations from the weather service
  - Proxies to: `{WEATHER_API_URL}/forecast/locations`
  - Returns: `{"locations": [{"location": "..."}, ...]}`
