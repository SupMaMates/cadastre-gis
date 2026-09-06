/**
 * CadastreGIS Interactive Map & Spatial Engine
 * Handles Leaflet map, vector styling, choropleth modes, spatial search, and parcel inspector.
 */

// Global state
let map = null;
let geojsonLayer = null;
let allFeatures = [];
let filteredFeatures = [];
let selectedParcelFeature = null;
let currentChoropleth = 'default';
let currentTheme = localStorage.getItem('cadastre_theme') || 'dark';

// Basemap tile layers
let baseLayers = {};

// Color palettes for choropleths
const USAGE_COLORS = {
  agriculture: '#10b981', // green
  residential: '#f59e0b', // amber
  yard: '#eab308',        // yellow
  forest: '#059669',     // emerald
  infrastructure: '#8b5cf6', // purple
  other: '#64748b'        // slate
};

const FRAGMENTATION_COLORS = [
  { max: 1, color: '#10b981', label: '1 vlasnik (100% čisto)' },
  { max: 3, color: '#eab308', label: '2 - 3 suvlasnika' },
  { max: 6, color: '#f97316', label: '4 - 6 suvlasnika' },
  { max: Infinity, color: '#ef4444', label: '7+ suvlasnika (visoka fragmentacija)' }
];

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initMap();
  loadData();
  setupSearch();
});

// Theme Management
function initTheme() {
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon();
}

function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', currentTheme);
  localStorage.setItem('cadastre_theme', currentTheme);
  updateThemeIcon();

  // Switch map basemap if appropriate
  if (map && baseLayers) {
    if (currentTheme === 'dark' && baseLayers['Tamna karta (CartoDB)']) {
      map.removeLayer(baseLayers['Svijetla karta (CartoDB)']);
      baseLayers['Tamna karta (CartoDB)'].addTo(map);
    } else if (currentTheme === 'light' && baseLayers['Svijetla karta (CartoDB)']) {
      map.removeLayer(baseLayers['Tamna karta (CartoDB)']);
      baseLayers['Svijetla karta (CartoDB)'].addTo(map);
    }
  }
}

function updateThemeIcon() {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.setAttribute('data-lucide', currentTheme === 'dark' ? 'sun' : 'moon');
    if (window.lucide) lucide.createIcons();
  }
}

// Map Initialization
function initMap() {
  // Center on Donji Žabar
  map = L.map('leaflet-map', {
    center: [44.94155, 18.64939],
    zoom: 13,
    zoomControl: false
  });

  L.control.zoom({ position: 'bottomright' }).addTo(map);
  L.control.scale({ metric: true, imperial: false, position: 'bottomleft' }).addTo(map);

  // Basemap tile definitions
  baseLayers = {
    'Satelit (Esri World Imagery)': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Esri, Maxar, Earthstar Geographics'
    }),
    'Tamna karta (CartoDB)': L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap, &copy; CARTO'
    }),
    'Svijetla karta (CartoDB)': L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap, &copy; CARTO'
    }),
    'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    })
  };

  // Add default basemap based on theme
  if (currentTheme === 'dark') {
    baseLayers['Tamna karta (CartoDB)'].addTo(map);
  } else {
    baseLayers['Svijetla karta (CartoDB)'].addTo(map);
  }

  L.control.layers(baseLayers, null, { position: 'topright' }).addTo(map);
}

// Load GeoJSON Dataset
async function loadData() {
  showToast('Učitavanje katastarskih parcela...');
  try {
    const res = await fetch('/api/parcels');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allFeatures = data.features || [];
    filteredFeatures = [...allFeatures];

    renderGeoJson(filteredFeatures);
    updateSidebarStats(filteredFeatures);
    updateLegend();
    showToast(`Uspješno učitano ${allFeatures.length} parcela.`);
  } catch (err) {
    console.error('Greška pri učitavanju podataka:', err);
    showToast('Greška pri preuzimanju parcela sa servera.');
  }
}

// Render GeoJSON Layer
function renderGeoJson(features) {
  if (geojsonLayer) {
    map.removeLayer(geojsonLayer);
  }

  const fc = {
    type: 'FeatureCollection',
    features: features
  };

  geojsonLayer = L.geoJSON(fc, {
    style: styleFeature,
    onEachFeature: bindFeatureEvents
  }).addTo(map);
}

// Styling Engine
function styleFeature(feature) {
  const p = feature.properties || {};
  let fillColor = '#3b82f6';
  let fillOpacity = 0.35;
  let strokeColor = '#2563eb';
  let weight = 1.2;

  if (currentChoropleth === 'usage') {
    const cat = p.usage_category || 'other';
    fillColor = USAGE_COLORS[cat] || '#64748b';
    strokeColor = fillColor;
    fillOpacity = 0.6;
  } else if (currentChoropleth === 'fragmentation') {
    const n = p.n_owners || 1;
    if (n === 1) fillColor = '#10b981';
    else if (n <= 3) fillColor = '#eab308';
    else if (n <= 6) fillColor = '#f97316';
    else fillColor = '#ef4444';
    strokeColor = fillColor;
    fillOpacity = 0.65;
  } else if (currentChoropleth === 'ownership_type') {
    fillColor = p.is_entity ? '#8b5cf6' : '#3b82f6';
    strokeColor = fillColor;
    fillOpacity = 0.55;
  } else if (currentChoropleth === 'area') {
    const a = p.area_sqm || 0;
    if (a < 1000) fillColor = '#93c5fd';
    else if (a < 3000) fillColor = '#3b82f6';
    else if (a < 8000) fillColor = '#1d4ed8';
    else if (a < 20000) fillColor = '#4338ca';
    else fillColor = '#312e81';
    strokeColor = '#1e3a8a';
    fillOpacity = 0.7;
  }

  // Highlight if selected
  if (selectedParcelFeature && selectedParcelFeature.id === feature.id) {
    strokeColor = '#f59e0b';
    weight = 3.5;
    fillOpacity = 0.8;
  }

  return {
    fillColor: fillColor,
    weight: weight,
    opacity: 0.9,
    color: strokeColor,
    fillOpacity: fillOpacity
  };
}

// Feature Interactions (Hover & Click)
function bindFeatureEvents(feature, layer) {
  layer.on({
    mouseover: (e) => {
      const p = feature.properties || {};
      const card = document.getElementById('map-hover-card');
      if (card) {
        card.innerHTML = `
          <strong>Parcela ${p.parcel_id || 'N/A'}</strong> &bull; ${(p.area_sqm || 0).toLocaleString()} m²<br/>
          <span style="color:var(--text-secondary);font-size:0.75rem;">${p.primary_owner || 'Nepoznato'}</span>
        `;
        card.style.display = 'block';
      }
      e.target.setStyle({ weight: 2.5, fillOpacity: 0.85 });
    },
    mouseout: (e) => {
      const card = document.getElementById('map-hover-card');
      if (card) card.style.display = 'none';
      if (!selectedParcelFeature || selectedParcelFeature.id !== feature.id) {
        geojsonLayer.resetStyle(e.target);
      }
    },
    click: (e) => {
      selectParcel(feature, e.target);
    }
  });
}

// Select Parcel & Open Inspector
function selectParcel(feature, layer) {
  selectedParcelFeature = feature;
  const p = feature.properties || {};

  // Update styles across map
  geojsonLayer.setStyle(styleFeature);

  // Zoom / pan smoothly to parcel
  if (layer && layer.getBounds) {
    map.fitBounds(layer.getBounds(), { maxZoom: 17, padding: [50, 50] });
  }

  // Populate Inspector Drawer
  document.getElementById('insp-parcel-title').innerText = `Parcela ${p.parcel_id || 'N/A'}`;
  document.getElementById('insp-ko-badge').innerText = p.ko_naziv_cir || p.ko_naziv || 'Доњи Жабар';
  document.getElementById('insp-area').innerText = `${(p.area_sqm || 0).toLocaleString()} m²`;
  document.getElementById('insp-area-ha').innerText = `${((p.area_sqm || 0) / 10000).toFixed(4)} ha`;
  document.getElementById('insp-pl').innerText = p.pl_broj || 'N/A';
  document.getElementById('insp-owners-count').innerText = p.n_owners || 0;
  document.getElementById('insp-eff-owners').innerText = `N_eff = ${p.effective_n_owners || 1.0}`;
  document.getElementById('insp-updated').innerText = p.updated_date || 'N/A';

  // Action links
  const kmlBtn = document.getElementById('btn-download-kml');
  if (kmlBtn) {
    kmlBtn.href = `/api/parcels/${encodeURIComponent(p.parcel_id)}/kml`;
  }

  // Compute centroid for Google Maps
  let lat = 44.94155, lon = 18.64939;
  if (feature.geometry && feature.geometry.coordinates) {
    const coords = feature.geometry.type === 'Polygon' 
      ? feature.geometry.coordinates[0][0] 
      : feature.geometry.coordinates[0][0][0];
    lon = coords[0];
    lat = coords[1];
  }
  const gmBtn = document.getElementById('btn-google-maps');
  if (gmBtn) {
    gmBtn.href = `https://www.google.com/maps?q=${lat},${lon}`;
  }

  // Owners Table
  const ownersTbody = document.getElementById('insp-owners-tbody');
  ownersTbody.innerHTML = '';
  const owners = p.owners || [];
  document.getElementById('insp-owners-badge').innerText = owners.length;

  if (owners.length === 0) {
    ownersTbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Nema uknjiženih vlasnika</td></tr>';
  } else {
    owners.forEach(o => {
      const tr = document.createElement('tr');
      const sharePct = ((o.share || 1) * 100).toFixed(2);
      tr.innerHTML = `
        <td>
          <div style="font-weight:600">${o.name}</div>
          <div style="font-size:0.7rem;color:var(--text-muted)">Otac: ${o.father || '-'} | ${o.gender}</div>
        </td>
        <td><span class="badge badge-primary">${o.share_raw || '1/1'}</span> (${sharePct}%)</td>
        <td class="right">${(o.wealth_sqm || 0).toLocaleString()} m²</td>
      `;
      ownersTbody.appendChild(tr);
    });
  }

  // Parts Table
  const partsTbody = document.getElementById('insp-parts-tbody');
  partsTbody.innerHTML = '';
  const parts = p.parts || [];
  document.getElementById('insp-parts-badge').innerText = parts.length;

  if (parts.length === 0) {
    partsTbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Nema uknjiženih kultura</td></tr>';
  } else {
    parts.forEach(pt => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${pt.usage_type}</td>
        <td>${pt.land_class ? `${pt.land_class}. klasa` : '-'}</td>
        <td class="right">${(pt.area_sqm || 0).toLocaleString()} m²</td>
      `;
      partsTbody.appendChild(tr);
    });
  }

  // Open Drawer
  const inspector = document.getElementById('parcel-inspector');
  if (inspector) inspector.classList.add('open');
}

function closeInspector() {
  const inspector = document.getElementById('parcel-inspector');
  if (inspector) inspector.classList.remove('open');
  selectedParcelFeature = null;
  if (geojsonLayer) geojsonLayer.setStyle(styleFeature);
}

// Copy GPS coordinates
function copyGpsCoordinates() {
  if (!selectedParcelFeature) return;
  const geom = selectedParcelFeature.geometry;
  if (!geom || !geom.coordinates) return;
  const coords = geom.type === 'Polygon' ? geom.coordinates[0][0] : geom.coordinates[0][0][0];
  const str = `${coords[1].toFixed(6)}, ${coords[0].toFixed(6)}`;
  navigator.clipboard.writeText(str).then(() => {
    showToast(`GPS koordinate kopirane: ${str}`);
  });
}

// Filtering & Search
function setupSearch() {
  const input = document.getElementById('parcel-search-input');
  const resultsDiv = document.getElementById('search-results');
  const clearBtn = document.getElementById('clear-search-btn');

  let debounceTimer;

  input.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim().toLowerCase();

    if (query.length > 0) {
      clearBtn.style.display = 'block';
    } else {
      clearBtn.style.display = 'none';
      resultsDiv.style.display = 'none';
      return;
    }

    debounceTimer = setTimeout(() => {
      const matches = allFeatures.filter(f => {
        const p = f.properties || {};
        const pId = String(p.parcel_id || '').toLowerCase();
        const pl = String(p.pl_broj || '').toLowerCase();
        const owners = String(p.owner_names || '').toLowerCase();
        return pId.includes(query) || pl.includes(query) || owners.includes(query);
      }).slice(0, 10);

      resultsDiv.innerHTML = '';
      if (matches.length === 0) {
        resultsDiv.innerHTML = '<div style="padding:10px;color:var(--text-muted);font-size:0.8rem;">Nema pronađenih parcela.</div>';
      } else {
        matches.forEach(m => {
          const p = m.properties || {};
          const item = document.createElement('div');
          item.className = 'search-result-item';
          item.innerHTML = `
            <div>
              <span class="search-res-id">Parcela ${p.parcel_id}</span>
              <div class="search-res-owner">${p.primary_owner || 'Nepoznato'}</div>
            </div>
            <span class="badge badge-primary">${(p.area_sqm || 0).toLocaleString()} m²</span>
          `;
          item.onclick = () => {
            resultsDiv.style.display = 'none';
            selectParcel(m, null);
          };
          resultsDiv.appendChild(item);
        });
      }
      resultsDiv.style.display = 'block';
    }, 200);
  });
}

function clearSearch() {
  const input = document.getElementById('parcel-search-input');
  input.value = '';
  document.getElementById('clear-search-btn').style.display = 'none';
  document.getElementById('search-results').style.display = 'none';
  applyFilters();
}

function applyFilters() {
  const usageFilter = document.getElementById('filter-usage').value;
  const coownedOnly = document.getElementById('filter-coowned').checked;
  const anomaliesOnly = document.getElementById('filter-anomalies').checked;

  filteredFeatures = allFeatures.filter(f => {
    const p = f.properties || {};

    if (usageFilter !== 'all' && p.usage_category !== usageFilter) {
      return false;
    }
    if (coownedOnly && !p.is_coowned) {
      return false;
    }
    if (anomaliesOnly && !p.has_share_anomaly) {
      return false;
    }
    return true;
  });

  renderGeoJson(filteredFeatures);
  updateSidebarStats(filteredFeatures);
  showToast(`Primijenjen filter: prikazano ${filteredFeatures.length} parcela.`);
}

function resetFilters() {
  document.getElementById('filter-usage').value = 'all';
  document.getElementById('filter-coowned').checked = false;
  document.getElementById('filter-anomalies').checked = false;
  document.getElementById('choropleth-mode').value = 'default';
  currentChoropleth = 'default';
  clearSearch();
  filteredFeatures = [...allFeatures];
  renderGeoJson(filteredFeatures);
  updateSidebarStats(filteredFeatures);
  updateLegend();
  showToast('Svi filteri su resetovani.');
}

function updateMapStyle() {
  currentChoropleth = document.getElementById('choropleth-mode').value;
  if (geojsonLayer) {
    geojsonLayer.setStyle(styleFeature);
  }
  updateLegend();
}

function updateLegend() {
  const leg = document.getElementById('map-legend');
  if (!leg) return;

  if (currentChoropleth === 'default') {
    leg.innerHTML = `
      <div class="legend-title">Standardne granice</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#3b82f6;"></div> Katastarska parcela</div>
    `;
  } else if (currentChoropleth === 'usage') {
    leg.innerHTML = `
      <div class="legend-title">Kategorija namjene</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#10b981;"></div> Poljoprivredno</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#f59e0b;"></div> Stambeno / Objekti</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#eab308;"></div> Dvorište</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#059669;"></div> Šuma</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#8b5cf6;"></div> Infrastruktura / Voda</div>
    `;
  } else if (currentChoropleth === 'fragmentation') {
    leg.innerHTML = `
      <div class="legend-title">Fragmentacija (Broj suvlasnika)</div>
      ${FRAGMENTATION_COLORS.map(c => `
        <div class="legend-item"><div class="legend-color-box" style="background:${c.color};"></div> ${c.label}</div>
      `).join('')}
    `;
  } else if (currentChoropleth === 'ownership_type') {
    leg.innerHTML = `
      <div class="legend-title">Tip nosioca prava</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#3b82f6;"></div> Privatno fizičko lice</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#8b5cf6;"></div> Pravno lice / Opština / Republika</div>
    `;
  } else if (currentChoropleth === 'area') {
    leg.innerHTML = `
      <div class="legend-title">Površina parcele</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#93c5fd;"></div> &lt; 1,000 m²</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#3b82f6;"></div> 1,000 - 3,000 m²</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#1d4ed8;"></div> 3,000 - 8,000 m²</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#4338ca;"></div> 8,000 - 20,000 m²</div>
      <div class="legend-item"><div class="legend-color-box" style="background:#312e81;"></div> &gt; 20,000 m²</div>
    `;
  }
}

function updateSidebarStats(features) {
  const countEl = document.getElementById('visible-parcel-count');
  const areaEl = document.getElementById('visible-parcel-area');

  const count = features.length;
  const areaM2 = features.reduce((sum, f) => sum + (f.properties.area_sqm || 0), 0);
  const areaHa = (areaM2 / 10000).toFixed(1);

  if (countEl) countEl.innerText = count.toLocaleString();
  if (areaEl) areaEl.innerText = Number(areaHa).toLocaleString();
}

function fitMunicipalityBounds() {
  if (geojsonLayer && geojsonLayer.getBounds().isValid()) {
    map.fitBounds(geojsonLayer.getBounds(), { padding: [20, 20] });
  }
}

function toggleSidebar() {
  const sb = document.getElementById('map-sidebar');
  if (sb) sb.classList.toggle('collapsed');
}

// Toast Notifications
function showToast(msg) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerText = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

// View Switching
function switchView(viewName) {
  document.getElementById('tab-map').classList.toggle('active', viewName === 'map');
  document.getElementById('tab-dashboard').classList.toggle('active', viewName === 'dashboard');

  document.getElementById('view-map').classList.toggle('active', viewName === 'map');
  document.getElementById('view-dashboard').classList.toggle('active', viewName === 'dashboard');

  if (viewName === 'map' && map) {
    setTimeout(() => map.invalidateSize(), 100);
  } else if (viewName === 'dashboard' && window.initDashboard) {
    window.initDashboard();
  }
}

// Data Export Trigger
function exportData(fmt) {
  window.location.href = `/api/export?format=${fmt}`;
}
