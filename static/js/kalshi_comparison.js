let selectedLocation = null;
let selectedProvider = null;

document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([loadLocations(), loadProviders()]);
    document.getElementById('location-dropdown').addEventListener('change', onSelectionChange);
    document.getElementById('provider-dropdown').addEventListener('change', onSelectionChange);
});

async function loadLocations() {
    const dropdown = document.getElementById('location-dropdown');
    try {
        const data = await apiFetch('/api/forecast/locations');
        dropdown.innerHTML = '<option value="">-- Select a location --</option>';
        (data.locations || []).forEach(item => {
            dropdown.appendChild(makeOption(item.location, item.location));
        });
    } catch (e) {
        dropdown.innerHTML = '<option value="">Error loading locations</option>';
    }
}

async function loadProviders() {
    const dropdown = document.getElementById('provider-dropdown');
    try {
        const data = await apiFetch('/api/forecast/providers');
        dropdown.innerHTML = '<option value="">-- Select a provider --</option>';
        (data.providers || []).forEach(item => {
            const name = typeof item === 'string' ? item : (item.provider || item.name);
            dropdown.appendChild(makeOption(name, name));
        });
    } catch (e) {
        dropdown.innerHTML = '<option value="">Error loading providers</option>';
    }
}

function onSelectionChange() {
    selectedLocation = document.getElementById('location-dropdown').value || null;
    selectedProvider = document.getElementById('provider-dropdown').value || null;
    if (selectedLocation && selectedProvider) {
        loadComparison();
    } else {
        document.getElementById('results-section').innerHTML =
            '<p class="info-text">Select a location and provider to compare model probabilities against Kalshi markets.</p>';
    }
}

async function loadComparison() {
    const section = document.getElementById('results-section');
    section.innerHTML = '<p class="info-text">Loading...</p>';

    try {
        const url = `/api/kalshi/comparison?location=${encodeURIComponent(selectedLocation)}&provider=${encodeURIComponent(selectedProvider)}`;
        const data = await apiFetch(url);
        section.innerHTML = renderResults(data);
    } catch (e) {
        section.innerHTML = `
            <p style="color:red"><strong>Error:</strong> ${e.message}</p>
            <button onclick="loadComparison()">Retry</button>
        `;
    }
}

function renderResults(data) {
    let html = `
        <h3>Forecast: ${data.forecast_high}°F on ${data.forecast_date}</h3>
        <p style="font-size:14px;color:#666">${data.provider} at ${data.location} &mdash; based on ${data.sample_size} days of history</p>
        <h4>Kalshi Edge Table</h4>
    `;

    if (!data.edge_table || data.edge_table.length === 0) {
        return html + '<p class="info-text">No Kalshi markets available for this location.</p>';
    }

    html += `
        <table style="border-collapse:collapse;width:100%">
            <thead>
                <tr style="border-bottom:2px solid #333;background:#f5f5f5">
                    <th style="text-align:left;padding:8px">Bucket</th>
                    <th style="text-align:right;padding:8px" colspan="2">Model</th>
                    <th style="text-align:right;padding:8px" colspan="2">Kalshi Market</th>
                    <th style="text-align:right;padding:8px" colspan="2">Edge</th>
                    <th style="text-align:center;padding:8px">Best Bet</th>
                </tr>
                <tr style="border-bottom:1px solid #aaa;font-size:12px;color:#666">
                    <th style="padding:4px 8px"></th>
                    <th style="text-align:right;padding:4px 8px">YES%</th>
                    <th style="text-align:right;padding:4px 8px">NO%</th>
                    <th style="text-align:right;padding:4px 8px">Bid YES</th>
                    <th style="text-align:right;padding:4px 8px">Bid NO</th>
                    <th style="text-align:right;padding:4px 8px">YES</th>
                    <th style="text-align:right;padding:4px 8px">NO</th>
                    <th style="padding:4px 8px"></th>
                </tr>
            </thead>
            <tbody>
    `;

    data.edge_table.forEach(row => {
        const modelNo = (100 - row.model_prob).toFixed(1);
        const yesEdgeColor = row.yes_edge > 0 ? 'color:#2a7a2a' : (row.yes_edge < 0 ? 'color:#c00' : '');
        const noEdgeColor = row.no_edge > 0 ? 'color:#2a7a2a' : (row.no_edge < 0 ? 'color:#c00' : '');
        const bestBetStyle = row.best_edge > 0 ? 'font-weight:bold;color:#2a7a2a' : 'color:#999';
        const mktYes = row.market_yes != null ? row.market_yes + '%' : '—';
        const mktNo = row.market_no != null ? row.market_no + '%' : '—';
        const yesEdge = row.yes_edge != null ? (row.yes_edge > 0 ? '+' : '') + row.yes_edge : '—';
        const noEdge = row.no_edge != null ? (row.no_edge > 0 ? '+' : '') + row.no_edge : '—';
        html += `
            <tr style="border-bottom:1px solid #ddd">
                <td style="padding:8px">${row.subtitle}</td>
                <td style="text-align:right;padding:8px">${row.model_prob}%</td>
                <td style="text-align:right;padding:8px">${modelNo}%</td>
                <td style="text-align:right;padding:8px">${mktYes}</td>
                <td style="text-align:right;padding:8px">${mktNo}</td>
                <td style="text-align:right;padding:8px;${yesEdgeColor}">${yesEdge}</td>
                <td style="text-align:right;padding:8px;${noEdgeColor}">${noEdge}</td>
                <td style="text-align:center;padding:8px;${bestBetStyle}">${row.best_edge > 0 ? row.best_bet : '—'}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

// --- Helpers ---

async function apiFetch(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    return data;
}

function makeOption(value, text) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = text;
    return opt;
}
