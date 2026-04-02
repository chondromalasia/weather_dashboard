// Store the selected location and provider globally for later use
let selectedLocation = null;
let selectedProvider = null;

// Fetch locations and providers when page loads
document.addEventListener('DOMContentLoaded', async () => {
    await loadLocations();
    await loadProviders();
    setupLocationDropdown();
    setupProviderDropdown();
});

async function loadLocations() {
    const dropdown = document.getElementById('location-dropdown');

    try {
        const response = await fetch('/api/forecast/locations');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            dropdown.innerHTML = '<option value="">Error loading locations</option>';
            showError(data.error, data.details);
            return;
        }

        // Clear the dropdown
        dropdown.innerHTML = '<option value="">-- Select a location --</option>';

        // Populate dropdown with locations
        if (data.locations && Array.isArray(data.locations)) {
            data.locations.forEach(item => {
                const option = document.createElement('option');
                option.value = item.location;
                option.textContent = item.location;
                dropdown.appendChild(option);
            });
        } else {
            console.warn('Unexpected data structure:', data);
            dropdown.innerHTML = '<option value="">No locations available</option>';
        }

    } catch (error) {
        console.error('Error fetching locations:', error);
        dropdown.innerHTML = '<option value="">Error loading locations</option>';
        showError('Failed to load locations', error.message);
    }
}

function setupLocationDropdown() {
    const dropdown = document.getElementById('location-dropdown');

    dropdown.addEventListener('change', (event) => {
        const value = event.target.value;

        if (value) {
            selectedLocation = value;
            updateLocationInfo();
        } else {
            selectedLocation = null;
            clearLocationInfo();
        }
    });
}

async function loadProviders() {
    const dropdown = document.getElementById('provider-dropdown');

    try {
        const response = await fetch('/api/forecast/providers');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            dropdown.innerHTML = '<option value="">Error loading providers</option>';
            showError(data.error, data.details);
            return;
        }

        // Clear the dropdown
        dropdown.innerHTML = '<option value="">-- Select a provider --</option>';

        // Populate dropdown with providers
        if (data.providers && Array.isArray(data.providers)) {
            data.providers.forEach(item => {
                const option = document.createElement('option');
                // Handle both string and object formats
                const providerName = typeof item === 'string' ? item : (item.provider || item.name || JSON.stringify(item));
                option.value = providerName;
                option.textContent = providerName;
                dropdown.appendChild(option);
            });
        } else {
            console.warn('Unexpected data structure:', data);
            dropdown.innerHTML = '<option value="">No providers available</option>';
        }

    } catch (error) {
        console.error('Error fetching providers:', error);
        dropdown.innerHTML = '<option value="">Error loading providers</option>';
        showError('Failed to load providers', error.message);
    }
}

function setupProviderDropdown() {
    const dropdown = document.getElementById('provider-dropdown');

    dropdown.addEventListener('change', (event) => {
        const value = event.target.value;

        if (value) {
            selectedProvider = value;
            updateLocationInfo();
        } else {
            selectedProvider = null;
            clearLocationInfo();
        }
    });
}

async function updateLocationInfo() {
    const infoSection = document.getElementById('selected-location-info');

    if (!selectedLocation && !selectedProvider) {
        clearLocationInfo();
        return;
    }

    let html = '<h3>Selected Parameters</h3>';

    if (selectedLocation) {
        html += `<p><strong>Location:</strong> ${selectedLocation}</p>`;
    }

    if (selectedProvider) {
        html += `<p><strong>Provider:</strong> ${selectedProvider}</p>`;
    }

    infoSection.innerHTML = html;

    // Fetch forecast highs if both location and provider are selected
    if (selectedLocation && selectedProvider) {
        await fetchForecastHighs();
    }
}

async function fetchForecastHighs() {
    const infoSection = document.getElementById('selected-location-info');

    // Clear the section while loading
    infoSection.innerHTML = '<p class="info-text">Loading analysis...</p>';

    // Fetch comparison analysis
    await fetchComparisonAnalysis();
}

function clearLocationInfo() {
    const infoSection = document.getElementById('selected-location-info');
    infoSection.innerHTML = '<p class="info-text">Please select a location and/or provider to view forecast analysis</p>';
}

function showError(error, details) {
    const infoSection = document.getElementById('selected-location-info');
    infoSection.innerHTML = `
        <p style="color: red;"><strong>Error:</strong> ${error}</p>
        ${details ? `<p style="color: red; font-size: 12px;">${details}</p>` : ''}
    `;
}

async function fetchComparisonAnalysis() {
    const infoSection = document.getElementById('selected-location-info');

    try {
        const url = `/api/forecast/comparison?location=${encodeURIComponent(selectedLocation)}&provider=${encodeURIComponent(selectedProvider)}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            infoSection.innerHTML = `
                <h3>Forecast Comparison Analysis</h3>
                <p style="color: red;"><strong>Error:</strong> ${data.error}</p>
            `;
            return;
        }

        // Build HTML starting with most recent forecast
        let html = `
            <h3>Most Recent Forecast</h3>
        `;

        if (data.most_recent_forecast) {
            html += `
                <p><strong>Date:</strong> ${data.most_recent_forecast.date}</p>
                <p><strong>Forecasted High:</strong> ${data.most_recent_forecast.forecasted_high}°F</p>
            `;
        } else {
            html += '<p class="info-text">No recent forecast available</p>';
        }

        html += `
            <hr>
            <h3>Forecast Comparison Analysis</h3>
            <h4>Error Distribution</h4>
            <p style="font-size: 14px; color: #666;">Negative means forecast under observation, e.g. Forecast 85°F, Observation 87°F</p>
        `;

        // Build HTML for error histogram
        if (data.error_histogram && data.error_histogram.length > 0) {
            html += `
                <table style="border-collapse: collapse; width: 100%; max-width: 400px;">
                    <thead>
                        <tr style="border-bottom: 2px solid #333;">
                            <th style="text-align: left; padding: 8px;">Error (°F)</th>
                            <th style="text-align: right; padding: 8px;">Count</th>
                            <th style="text-align: right; padding: 8px;">Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.error_histogram.forEach(row => {
                html += `
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px;">${row['Error (°F)'].toFixed(1)}</td>
                        <td style="text-align: right; padding: 8px;">${row['Count']}</td>
                        <td style="text-align: right; padding: 8px;">${row['Percentage']}%</td>
                    </tr>
                `;
            });

            html += `
                    </tbody>
                </table>
            `;
        } else {
            html += '<p class="info-text">No error distribution data available</p>';
        }

        // Add summary statistics after error distribution
        html += `<h4>Summary Statistics</h4>`;
        if (data.summary.count === 0) {
            html += `<p class="info-text">${data.summary.message || 'No overlapping forecast and observation data available'}</p>`;
        } else {
            html += `
                <p><strong>Sample Size:</strong> ${data.summary.count} days</p>
                <p><strong>Mean Error:</strong> ${data.summary.mean_error.toFixed(2)}°F</p>
                <p><strong>Mean Absolute Error (MAE):</strong> ${data.summary.mean_absolute_error.toFixed(2)}°F</p>
                <p><strong>Root Mean Square Error (RMSE):</strong> ${data.summary.rmse.toFixed(2)}°F</p>
                <p><strong>Max Error:</strong> ${data.summary.max_error.toFixed(2)}°F</p>
                <p><strong>Min Error:</strong> ${data.summary.min_error.toFixed(2)}°F</p>
            `;
        }

        infoSection.innerHTML = html;

    } catch (error) {
        console.error('Error fetching comparison analysis:', error);
        infoSection.innerHTML = `
            <h3>Forecast Comparison Analysis</h3>
            <p style="color: red;"><strong>Error:</strong> Failed to load comparison analysis</p>
        `;
    }
}
