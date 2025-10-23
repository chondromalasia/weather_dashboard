// Store the selected location globally for later use
let selectedLocation = null;

// Fetch locations when page loads
document.addEventListener('DOMContentLoaded', async () => {
    await loadLocations();
    setupLocationDropdown();
});

async function loadLocations() {
    const dropdown = document.getElementById('location-dropdown');
    console.log('loadLocations called');

    try {
        const response = await fetch('/api/forecast/locations');
        console.log('Fetch completed, status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('API Response:', data);

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
                console.log('Location item:', item, 'Type:', typeof item, 'Value:', item.location);
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
            updateLocationInfo(value);
        } else {
            selectedLocation = null;
            clearLocationInfo();
        }
    });
}

function updateLocationInfo(location) {
    const infoSection = document.getElementById('selected-location-info');
    infoSection.innerHTML = `
        <h3>Selected Location</h3>
        <p><strong>Location:</strong> ${location}</p>
        <p class="info-text">Location variable is ready for use: <code>selectedLocation = "${location}"</code></p>
    `;
}

function clearLocationInfo() {
    const infoSection = document.getElementById('selected-location-info');
    infoSection.innerHTML = '<p class="info-text">Please select a location to view forecast analysis</p>';
}

function showError(error, details) {
    const infoSection = document.getElementById('selected-location-info');
    infoSection.innerHTML = `
        <p style="color: red;"><strong>Error:</strong> ${error}</p>
        ${details ? `<p style="color: red; font-size: 12px;">${details}</p>` : ''}
    `;
}
