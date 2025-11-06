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

    try {
        const url = `/api/forecast/highs?location=${encodeURIComponent(selectedLocation)}&provider=${encodeURIComponent(selectedProvider)}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            showError(data.error, data.details);
            return;
        }

        // Display the first 2 forecast highs
        let html = `
            <h3>Selected Parameters</h3>
            <p><strong>Location:</strong> ${selectedLocation}</p>
            <p><strong>Provider:</strong> ${selectedProvider}</p>
            <hr>
            <h3>Forecast Highs</h3>
            <p><strong>Cutoff:</strong> ${data.cutoff}</p>
        `;

        if (data.forecasted_highs && data.forecasted_highs.length > 0) {
            const displayCount = Math.min(2, data.forecasted_highs.length);
            for (let i = 0; i < displayCount; i++) {
                const forecast = data.forecasted_highs[i];
                html += `<p><strong>${forecast.date}:</strong> ${forecast.forecasted_high}°F</p>`;
            }

            // Extract the oldest date (first item in the array)
            const oldestDate = data.forecasted_highs[0].date;

            infoSection.innerHTML = html;

            // Fetch observations using the oldest date
            await fetchObservationHighs(oldestDate);
        } else {
            html += '<p class="info-text">No forecast data available</p>';
            infoSection.innerHTML = html;
        }

    } catch (error) {
        console.error('Error fetching forecast highs:', error);
        showError('Failed to load forecast highs', error.message);
    }
}

async function fetchObservationHighs(startDate) {
    const infoSection = document.getElementById('selected-location-info');

    try {
        const url = `/api/observations/highs?station_id=${encodeURIComponent(selectedLocation)}&service=CLI&start=${encodeURIComponent(startDate)}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            // Append error to existing content
            infoSection.innerHTML += `
                <hr>
                <h3>Observation Highs</h3>
                <p style="color: red;"><strong>Error:</strong> ${data.error}</p>
            `;
            return;
        }

        // Append observations to existing content
        let html = `
            <hr>
            <h3>Observation Highs</h3>
            <p><strong>Start Date:</strong> ${startDate}</p>
            <p><strong>Service:</strong> CLI</p>
            <p><strong>Count:</strong> ${data.count}</p>
        `;

        if (data.observations && data.observations.length > 0) {
            const displayCount = Math.min(2, data.observations.length);
            for (let i = 0; i < displayCount; i++) {
                const observation = data.observations[i];
                // Extract just the date from the timestamp
                const dateOnly = observation.timestamp.split('T')[0];
                html += `<p><strong>${dateOnly}:</strong> ${parseFloat(observation.value).toFixed(1)}°${observation.unit}</p>`;
            }
        } else {
            html += '<p class="info-text">No observation data available</p>';
        }

        infoSection.innerHTML += html;

    } catch (error) {
        console.error('Error fetching observation highs:', error);
        infoSection.innerHTML += `
            <hr>
            <h3>Observation Highs</h3>
            <p style="color: red;"><strong>Error:</strong> Failed to load observation highs</p>
        `;
    }
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
