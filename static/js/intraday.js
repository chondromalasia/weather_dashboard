// Intraday temperature comparison — KNYC.
// Wunderground PWS traces + NWS (METAR) observed temperature.

const PWS_COLORS = ['#007bff', '#e8590c', '#2b8a3e', '#ae3ec9'];
let chart = null;

// Per-source styling. PWS stations cycle through PWS_COLORS as thin lines;
// the NWS observation trace is a bold dark reference line.
function styleFor(series, pwsIndex) {
    if (series.source === 'nws_metar') {
        return { borderColor: '#212529', backgroundColor: '#212529', borderWidth: 3, pointRadius: 3, tension: 0.2 };
    }
    const c = PWS_COLORS[pwsIndex % PWS_COLORS.length];
    return { borderColor: c, backgroundColor: c, borderWidth: 2, pointRadius: 1.5, tension: 0.25 };
}

document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date-input');
    const today = new Date().toISOString().slice(0, 10);
    dateInput.value = today;
    dateInput.max = today;
    dateInput.addEventListener('change', () => load(dateInput.value));
    load(today);
});

async function load(date) {
    const status = document.getElementById('status');
    status.textContent = 'Loading…';

    try {
        const resp = await fetch(`/api/intraday/temperature?date=${encodeURIComponent(date)}`);
        const data = await resp.json();

        if (data.error) {
            status.textContent = `Error: ${data.error}`;
            document.getElementById('nowcast').innerHTML = '';
            document.getElementById('deltas').innerHTML = '';
            return;
        }

        render(data);
        renderNowcast(data);
        renderDeltas(data);

        const total = data.series.reduce((n, s) => n + s.points.length, 0);
        let msg = `${total} readings across ${data.series.length} station(s) — ${data.date} (${data.timezone})`;
        if (data.errors && data.errors.length) {
            msg += ` — ${data.errors.length} station(s) failed: ` + data.errors.map(e => e.station_id).join(', ');
        }
        status.textContent = msg;
    } catch (err) {
        console.error(err);
        status.textContent = `Failed to load: ${err.message}`;
    }
}

// Hardcoded multinomial-logistic nowcast of the next METAR's change, shown as
// a P(METAR >= k) ladder (see backend `_compute_nowcast`). Only present for
// today; null for past dates.
function renderNowcast(data) {
    const el = document.getElementById('nowcast');
    const nc = data.nowcast;

    if (!nc) { el.innerHTML = ''; return; }
    if (!nc.available) {
        el.innerHTML = `<h3>Nowcast &mdash; next METAR</h3><p class="muted">${nc.reason}</p>`;
        return;
    }

    const prevTime = new Date(nc.metar_prev_t * 1000)
        .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const rel = nc.reliability;
    const signed = v => (v > 0 ? '+' : '') + v.toFixed(1);
    const ml = nc.most_likely;

    const ladderRows = nc.ladder.map(r => {
        const pct = (100 * r.p_ge).toFixed(0);
        const w = Math.round(r.p_ge * 100);
        return `<tr>
            <td>&ge; ${r.k}&deg;F</td>
            <td class="bar-cell"><span class="bar" style="width:${w}%"></span>${pct}%</td>
        </tr>`;
    }).join('');

    const inp = nc.inputs;
    const inputBits = [
        ['KNYNEWYO1686', inp.KNYNEWYO1686],
        ['KNYNEWYO1796', inp.KNYNEWYO1796],
        ['KNYNEWYO270', inp.KNYNEWYO270],
    ].filter(([, i]) => i).map(([st, i]) => i.used
        ? `${st}: Δ1h ${signed(i.incr_f)}°, vs METAR ${signed(i.lvl_f)}°`
        : `${st}: no data`
    ).concat(`prev METAR move ${signed(inp.prev_change_f)}°`).join(' &nbsp;&middot;&nbsp; ');

    el.innerHTML = `
        <h3>Nowcast &mdash; next METAR (P &ge; k ladder)</h3>
        <table class="delta-table">
            <tbody>
                <tr><td>last observed</td>
                    <td>${nc.metar_prev_f.toFixed(0)}&deg;F <span class="muted">@ ${prevTime}</span></td></tr>
                <tr><td>most likely</td>
                    <td><strong style="font-size:18px">${ml.temp_f}&deg;F</strong>
                        <span class="muted">(${signed(ml.change)}°, ${(100 * ml.p).toFixed(0)}%) &nbsp;
                        expected ${signed(nc.expected_change_f)}°</span></td></tr>
                <tr><td>reliability now</td>
                    <td>${nc.tod_band} &mdash; ladder log-loss ${rel.model.toFixed(2)}
                        <span class="muted">vs ${rel.baseline.toFixed(2)} no-model</span></td></tr>
            </tbody>
        </table>
        <table class="delta-table ladder-table">
            <thead><tr><th>contract</th><th>P(next METAR &ge; threshold)</th></tr></thead>
            <tbody>${ladderRows}</tbody>
        </table>
        <p class="muted">${nc.model} &nbsp;&middot;&nbsp; ${inputBits}</p>`;
}

// Temperature change over the last available hour, per station. Anchored on
// each station's own latest reading (see backend `_last_hour_delta`), not
// wall-clock now.
function renderDeltas(data) {
    const el = document.getElementById('deltas');

    const rows = data.series.map(s => {
        const latest = s.points.length ? s.points[s.points.length - 1] : null;
        const latestCell = latest
            ? `${latest.temp_f.toFixed(1)}°F <span class="muted">@ ${formatHour(latest.hour)}</span>`
            : '—';

        const d = s.last_hour_delta;
        let changeCell;
        if (!d) {
            changeCell = '<span class="muted">n/a</span>';
        } else {
            const arrow = d.delta_f > 0 ? '▲' : (d.delta_f < 0 ? '▼' : '▪');
            const color = d.delta_f > 0 ? '#c92a2a' : (d.delta_f < 0 ? '#1971c2' : '#333');
            const sign = d.delta_f > 0 ? '+' : '';
            changeCell =
                `<span style="color:${color}">${arrow} ${sign}${d.delta_f.toFixed(1)}°F</span> ` +
                `<span class="muted">over ${d.span_minutes} min</span>`;
        }

        return `<tr><td>${s.station_id}</td><td>${latestCell}</td><td>${changeCell}</td></tr>`;
    }).join('');

    el.innerHTML = `
        <h3>1-hour change</h3>
        <table class="delta-table">
            <thead><tr><th>Station</th><th>Latest</th><th>Change vs. ~1h earlier</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function formatHour(h) {
    const hh = Math.floor(h);
    const mm = Math.round((h - hh) * 60);
    return String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
}

function render(data) {
    let pwsIndex = 0;
    const datasets = data.series.map(s => {
        const style = styleFor(s, s.source === 'nws_metar' ? 0 : pwsIndex++);
        return {
            label: s.station_id,
            data: s.points.map(p => ({ x: p.hour, y: p.temp_f })),
            ...style,
        };
    });

    const options = {
        responsive: true,
        interaction: { mode: 'nearest', intersect: false },
        scales: {
            x: {
                type: 'linear',
                min: 0,
                max: 24,
                title: { display: true, text: `Hour of day (${data.timezone})` },
                ticks: { stepSize: 2, callback: v => String(v).padStart(2, '0') + ':00' },
            },
            y: { title: { display: true, text: '°F' } },
        },
        plugins: {
            title: {
                display: true,
                text: `Intraday temperature — ${data.location} — ${data.date}`,
            },
            tooltip: {
                callbacks: {
                    title: items => formatHour(items[0].parsed.x),
                    label: item => `${item.dataset.label}: ${item.parsed.y.toFixed(1)}°F`,
                },
            },
        },
    };

    if (chart) {
        chart.data = { datasets };
        chart.options = options;
        chart.update();
    } else {
        chart = new Chart(document.getElementById('intraday-chart'), {
            type: 'line',
            data: { datasets },
            options,
        });
    }
}
