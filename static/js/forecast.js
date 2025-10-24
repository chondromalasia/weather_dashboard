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

function updateLocationInfo() {
    const infoSection = document.getElementById('selected-location-info');

    if (!selectedLocation && !selectedProvider) {
        clearLocationInfo();
        return;
    }

    let html = '<h3>Selected Parameters</h3>';

    if (selectedLocation) {
        html += `<p><strong>Location:</strong> ${selectedLocation}</p>`;
        html += `<p class="info-text">Location variable: <code>selectedLocation = "${selectedLocation}"</code></p>`;
    }

    if (selectedProvider) {
        html += `<p><strong>Provider:</strong> ${selectedProvider}</p>`;
        html += `<p class="info-text">Provider variable: <code>selectedProvider = "${selectedProvider}"</code></p>`;
    }

    infoSection.innerHTML = html;
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
