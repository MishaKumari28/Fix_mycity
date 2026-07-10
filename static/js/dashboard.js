/**
 * FixMyCity — Dashboard JS
 * Leaflet map integration, table search
 */

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initTableSearch();
});

// ── Leaflet Map ───────────────────────────────────────────────────
function initMap() {
  const mapEl = document.getElementById('issueMap');
  if (!mapEl || typeof L === 'undefined') return;

  // Default center: India
  const map = L.map('issueMap').setView([20.5937, 78.9629], 4);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 18,
  }).addTo(map);

  const severityColor = { critical: '#ef4444', high: '#f59e0b', medium: '#3b82d4', low: '#10b981' };

  fetch('/api/complaints')
    .then(r => r.json())
    .then(data => {
      const geoPoints = data.filter(c => c.latitude && c.longitude);
      if (!geoPoints.length) {
        document.getElementById('mapStatus').textContent =
          'No geotagged reports yet. Submit a complaint with GPS location to see it here.';
        return;
      }

      const group = L.featureGroup();
      geoPoints.forEach(c => {
        const color = severityColor[c.severity] || '#3b82d4';
        const marker = L.circleMarker([parseFloat(c.latitude), parseFloat(c.longitude)], {
          radius: 9,
          fillColor: color,
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.85,
        });
        marker.bindPopup(`
          <div style="min-width:180px">
            <div style="font-weight:600;margin-bottom:4px">${c.category_label}</div>
            <div style="font-size:12px;color:#666;margin-bottom:6px">${c.location}</div>
            <span style="background:${color};color:#fff;padding:2px 8px;border-radius:99px;font-size:11px">${c.severity}</span>
            <div style="margin-top:8px;font-size:11px;color:#888">${c.submitted_at.slice(0,10)}</div>
            <a href="/result/${c.id}" style="display:block;margin-top:8px;font-size:12px;color:#3b82d4">View details →</a>
          </div>
        `);
        marker.addTo(group);
      });
      group.addTo(map);
      map.fitBounds(group.getBounds().pad(0.2));
      document.getElementById('mapStatus').textContent = `${geoPoints.length} geotagged report(s) shown.`;
    })
    .catch(() => {
      document.getElementById('mapStatus').textContent = 'Could not load map data.';
    });
}

// ── Table Search ──────────────────────────────────────────────────
function initTableSearch() {
  const input = document.getElementById('tableSearch');
  const table = document.getElementById('complaintsTable');
  if (!input || !table) return;

  input.addEventListener('input', () => {
    const query = input.value.toLowerCase();
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  });
}
