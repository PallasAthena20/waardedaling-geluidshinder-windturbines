(function () {
  'use strict';

  const API = '';

  /* ---------------------------------------------------------------------
     Theme toggle
     --------------------------------------------------------------------- */
  (function themeInit() {
    const t = document.querySelector('[data-theme-toggle]');
    const r = document.documentElement;
    let d = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
    r.setAttribute('data-theme', d);
    t &&
      t.addEventListener('click', () => {
        d = d === 'dark' ? 'light' : 'dark';
        r.setAttribute('data-theme', d);
        t.setAttribute('aria-label', 'Schakel naar ' + (d === 'dark' ? 'lichte' : 'donkere') + ' modus');
        t.innerHTML =
          d === 'dark'
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
      });
  })();

  /* ---------------------------------------------------------------------
     Accordion
     --------------------------------------------------------------------- */
  document.querySelectorAll('.accordion-trigger').forEach((btn) => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.accordion-item');
      const isOpen = item.getAttribute('data-open') === 'true';
      item.setAttribute('data-open', String(!isOpen));
    });
  });

  /* ---------------------------------------------------------------------
     Toast
     --------------------------------------------------------------------- */
  const toastEl = document.getElementById('toast');
  let toastTimer;
  function showToast(msg, isError) {
    clearTimeout(toastTimer);
    toastEl.textContent = msg;
    toastEl.classList.toggle('error', !!isError);
    toastEl.classList.add('visible');
    toastTimer = setTimeout(() => toastEl.classList.remove('visible'), 4000);
  }

  /* ---------------------------------------------------------------------
     Formatting helpers
     --------------------------------------------------------------------- */
  const fmtEuro = (n) => new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n || 0);
  const fmtNum = (n, d) => new Intl.NumberFormat('nl-NL', { maximumFractionDigits: d ?? 0 }).format(n || 0);
  const fmtDist = (m) => (m >= 1000 ? fmtNum(m / 1000, 2) + ' km' : fmtNum(m) + ' m');

  /* ---------------------------------------------------------------------
     Category info (loaded from backend)
     --------------------------------------------------------------------- */
  let categories = {};
  async function loadCategories() {
    try {
      const res = await fetch(`${API}/api/categories`);
      categories = await res.json();
      updateCategoryHint();
    } catch (e) {
      console.error('categories', e);
    }
  }

  const categorySelect = document.getElementById('category-select');
  const methodField = document.getElementById('method-field');
  const categoryHint = document.getElementById('category-hint');

  function updateCategoryHint() {
    const key = categorySelect.value;
    const cat = categories[key];
    methodField.style.display = key === 'hoog' ? '' : 'none';
    if (cat) {
      categoryHint.textContent = cat.significant
        ? `Invloedsradius ${cat.radius_m / 1000} km · vlak effect ${cat.flat_effect_pct}%`
        : `Invloedsradius ${cat.radius_m / 1000} km · effect (${cat.flat_effect_pct}%) is in het onderzoek niet statistisch significant — indicatief.`;
    }
  }
  categorySelect.addEventListener('change', updateCategoryHint);

  /* ---------------------------------------------------------------------
     Address search / geocoding
     --------------------------------------------------------------------- */
  const searchInput = document.getElementById('location-search');
  const suggestionsEl = document.getElementById('suggestions');
  const locationHint = document.getElementById('location-hint');
  let selectedLocation = null;
  let searchDebounce;

  function closeSuggestions() {
    suggestionsEl.classList.remove('open');
    suggestionsEl.innerHTML = '';
  }

  async function runSearch(q) {
    if (!q || q.length < 2) {
      closeSuggestions();
      return;
    }
    try {
      const res = await fetch(`${API}/api/geocode?q=${encodeURIComponent(q)}`);
      if (!res.ok) {
        closeSuggestions();
        return;
      }
      const data = await res.json();
      renderSuggestions(data.suggestions || []);
    } catch (e) {
      console.error('geocode', e);
    }
  }

  function renderSuggestions(list) {
    if (!list.length) {
      closeSuggestions();
      return;
    }
    suggestionsEl.innerHTML = '';
    list.forEach((item) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'suggestion-item';
      btn.setAttribute('role', 'option');
      btn.innerHTML = `${escapeHtml(item.label)}<span class="type-tag">${escapeHtml(item.type || '')}</span>`;
      btn.addEventListener('click', () => {
        selectedLocation = item;
        searchInput.value = item.label;
        closeSuggestions();
        locationHint.textContent = `Geselecteerd: ${item.label} (${item.lat.toFixed(5)}, ${item.lon.toFixed(5)})`;
      });
      suggestionsEl.appendChild(btn);
    });
    suggestionsEl.classList.add('open');
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  searchInput.addEventListener('input', (e) => {
    selectedLocation = null;
    clearTimeout(searchDebounce);
    const q = e.target.value;
    searchDebounce = setTimeout(() => runSearch(q), 350);
  });
  searchInput.addEventListener('focus', () => {
    if (suggestionsEl.children.length) suggestionsEl.classList.add('open');
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrap')) closeSuggestions();
  });

  /* ---------------------------------------------------------------------
     Location input mode: search vs. raw coordinates
     (turbines are often placed in a field, with no address at all)
     --------------------------------------------------------------------- */
  const modeTabSearch = document.getElementById('mode-tab-search');
  const modeTabCoords = document.getElementById('mode-tab-coords');
  const modePanelSearch = document.getElementById('mode-panel-search');
  const modePanelCoords = document.getElementById('mode-panel-coords');
  const coordsInput = document.getElementById('coords-input');
  const coordsHint = document.getElementById('coords-hint');
  const coordsConfirmBtn = document.getElementById('coords-confirm-btn');
  let locationMode = 'search';

  function setLocationMode(mode) {
    locationMode = mode;
    const isSearch = mode === 'search';
    modeTabSearch.classList.toggle('active', isSearch);
    modeTabCoords.classList.toggle('active', !isSearch);
    modeTabSearch.setAttribute('aria-selected', String(isSearch));
    modeTabCoords.setAttribute('aria-selected', String(!isSearch));
    modePanelSearch.style.display = isSearch ? '' : 'none';
    modePanelCoords.style.display = isSearch ? 'none' : '';
    selectedLocation = null;
    if (isSearch) {
      searchInput.value = '';
      locationHint.textContent = 'Begin met typen — resultaten via de PDOK Locatieserver.';
    } else {
      coordsInput.value = '';
      coordsHint.textContent = 'WGS84-decimale graden — plak dit rechtstreeks vanuit Google Maps (rechtsklik op de kaart) of een GPS-toestel.';
      coordsHint.classList.remove('hint-error');
    }
  }
  modeTabSearch.addEventListener('click', () => setLocationMode('search'));
  modeTabCoords.addEventListener('click', () => setLocationMode('coords'));

  // Netherlands bounding box (generous, incl. Wadden islands / Caribbean excluded)
  const NL_BOUNDS = { latMin: 50.7, latMax: 53.6, lonMin: 3.3, lonMax: 7.3 };

  function parseCoordsInput(raw) {
    if (!raw) return { error: 'Vul coördinaten in, bijv. 52.04041, 4.95839.' };
    // Accept comma or whitespace separated, comma or dot as decimal separator per number
    const cleaned = raw.trim().replace(/[;\t]+/g, ',');
    const parts = cleaned.split(/[\s,]+/).filter(Boolean);
    if (parts.length !== 2) {
      return { error: 'Gebruik het formaat "breedtegraad, lengtegraad", bijv. 52.04041, 4.95839.' };
    }
    const lat = parseFloat(parts[0].replace(',', '.'));
    const lon = parseFloat(parts[1].replace(',', '.'));
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      return { error: 'Coördinaten konden niet worden herkend als getallen.' };
    }
    if (lat < NL_BOUNDS.latMin || lat > NL_BOUNDS.latMax || lon < NL_BOUNDS.lonMin || lon > NL_BOUNDS.lonMax) {
      return { error: 'Deze coördinaten liggen buiten Nederland. Controleer of breedtegraad en lengtegraad niet zijn verwisseld (breedtegraad ligt in NL rond 50,7–53,6; lengtegraad rond 3,3–7,3).' };
    }
    return { lat, lon };
  }

  function confirmCoords() {
    const result = parseCoordsInput(coordsInput.value);
    if (result.error) {
      coordsHint.textContent = result.error;
      coordsHint.classList.add('hint-error');
      coordsInput.classList.add('input-error');
      selectedLocation = null;
      return;
    }
    const { lat, lon } = result;
    selectedLocation = {
      label: `Coördinaten ${lat.toFixed(5)}, ${lon.toFixed(5)}`,
      lat,
      lon,
      type: 'coordinaat',
    };
    coordsHint.classList.remove('hint-error');
    coordsInput.classList.remove('input-error');
    coordsHint.textContent = `Bevestigd: ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  }
  coordsConfirmBtn.addEventListener('click', confirmCoords);
  coordsInput.addEventListener('input', () => {
    selectedLocation = null;
    coordsInput.classList.remove('input-error');
    coordsHint.classList.remove('hint-error');
  });
  coordsInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      confirmCoords();
    }
  });

  const coordsPickMapBtn = document.getElementById('coords-pick-map-btn');
  let pickingOnMap = false;

  function setPickingOnMap(active) {
    pickingOnMap = active;
    coordsPickMapBtn.classList.toggle('active', active);
    coordsPickMapBtn.textContent = '';
    const icon = document.createElement('span');
    icon.innerHTML = active
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-6.2-7-11a7 7 0 1 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>';
    coordsPickMapBtn.appendChild(icon);
    coordsPickMapBtn.appendChild(document.createTextNode(active ? 'Annuleren — klik op de kaart' : 'Of wijs de locatie aan op de kaart'));
    if (map.getCanvas) map.getCanvas().style.cursor = active ? 'crosshair' : '';
    if (active) {
      coordsHint.classList.remove('hint-error');
      coordsHint.textContent = 'Klik op de gewenste plek op de kaart rechts om de turbinelocatie te kiezen.';
    }
  }
  coordsPickMapBtn.addEventListener('click', () => setPickingOnMap(!pickingOnMap));

  /* ---------------------------------------------------------------------
     Turbine state + map
     --------------------------------------------------------------------- */
  let turbines = []; // { id, label, lat, lon, category, method }
  let idCounter = 1;

  const map = new maplibregl.Map({
    container: 'map',
    style: 'https://tiles.openfreemap.org/styles/positron',
    center: [5.2913, 52.1326],
    zoom: 6.4,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

  let mapReady = false;
  map.on('load', () => {
    mapReady = true;
    map.addSource('influence-circles', { type: 'geojson', data: emptyFC() });
    map.addLayer({
      id: 'influence-fill',
      type: 'fill',
      source: 'influence-circles',
      paint: { 'fill-color': '#0d6f66', 'fill-opacity': 0.08 },
    });
    map.addLayer({
      id: 'influence-line',
      type: 'line',
      source: 'influence-circles',
      paint: { 'line-color': '#0d6f66', 'line-width': 1.5, 'line-dasharray': [2, 2] },
    });

    map.addSource('buurten', { type: 'geojson', data: emptyFC() });
    map.addLayer({
      id: 'buurten-fill',
      type: 'fill',
      source: 'buurten',
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.55,
      },
    });
    map.addLayer({
      id: 'buurten-line',
      type: 'line',
      source: 'buurten',
      paint: { 'line-color': '#ffffff', 'line-width': 0.6 },
    });

    map.on('click', (e) => {
      if (!pickingOnMap) return;
      const { lat, lng } = e.lngLat;
      coordsInput.value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      selectedLocation = {
        label: `Coördinaten ${lat.toFixed(5)}, ${lng.toFixed(5)}`,
        lat,
        lon: lng,
        type: 'coordinaat',
      };
      coordsHint.classList.remove('hint-error');
      coordsHint.textContent = `Bevestigd via kaart: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      setPickingOnMap(false);
      showToast('Locatie gekozen op de kaart.');
    });

    map.on('click', 'buurten-fill', (e) => {
      if (pickingOnMap) return;
      const f = e.features[0];
      const p = f.properties;
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div class="popup-title">${escapeHtml(p.buurtnaam)} — ${escapeHtml(p.gemeentenaam)}</div>` +
            `<div class="popup-row"><span>Geraakte woningen</span><strong>${fmtNum(p.geraakte_woningen, 1)}</strong></div>` +
            `<div class="popup-row"><span>Waardedaling</span><strong>${p.gewogen_waardedaling_pct}%</strong></div>` +
            `<div class="popup-row"><span>Gem. WOZ</span><strong>${fmtEuro(p.gemiddelde_woz)}</strong></div>` +
            `<div class="popup-row"><span>Totale waardedaling</span><strong>${fmtEuro(p.totale_waardedaling_euro)}</strong></div>`
        )
        .addTo(map);
    });
    map.on('mouseenter', 'buurten-fill', () => (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', 'buurten-fill', () => (map.getCanvas().style.cursor = ''));

    renderMapCircles();
  });

  function emptyFC() {
    return { type: 'FeatureCollection', features: [] };
  }

  function renderMapCircles() {
    if (!mapReady) return;
    const features = [];
    turbines.forEach((t) => {
      const radiusKm = categories[t.category] ? categories[t.category].radius_m / 1000 : 2;
      const circle = turf.circle([t.lon, t.lat], radiusKm, { steps: 64, units: 'kilometers' });
      circle.properties = { id: t.id };
      features.push(circle);
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [t.lon, t.lat] },
        properties: { id: t.id, marker: true },
      });
    });
    map.getSource('influence-circles') && map.getSource('influence-circles').setData({ type: 'FeatureCollection', features: features.filter((f) => f.geometry.type !== 'Point') });
    updateMarkers();
    fitMapToTurbines();
  }

  let markerEls = [];
  function updateMarkers() {
    markerEls.forEach((m) => m.remove());
    markerEls = [];
    turbines.forEach((t, i) => {
      const el = document.createElement('div');
      el.style.width = '26px';
      el.style.height = '26px';
      el.style.borderRadius = '50%';
      el.style.background = '#0d6f66';
      el.style.border = '2px solid white';
      el.style.boxShadow = '0 2px 6px rgba(0,0,0,.3)';
      el.style.display = 'flex';
      el.style.alignItems = 'center';
      el.style.justifyContent = 'center';
      el.style.color = 'white';
      el.style.fontSize = '11px';
      el.style.fontWeight = '700';
      el.style.fontFamily = 'sans-serif';
      el.textContent = String(i + 1);
      const marker = new maplibregl.Marker({ element: el }).setLngLat([t.lon, t.lat]).addTo(map);
      markerEls.push(marker);
    });
  }

  function fitMapToTurbines() {
    if (!turbines.length) return;
    if (turbines.length === 1) {
      map.flyTo({ center: [turbines[0].lon, turbines[0].lat], zoom: 12 });
      return;
    }
    const bounds = new maplibregl.LngLatBounds();
    turbines.forEach((t) => bounds.extend([t.lon, t.lat]));
    map.fitBounds(bounds, { padding: 80, maxZoom: 13 });
  }

  /* ---------------------------------------------------------------------
     Turbine list UI
     --------------------------------------------------------------------- */
  const turbineListEl = document.getElementById('turbine-list');
  const emptyStateEl = document.getElementById('empty-state');
  const calculateBtn = document.getElementById('calculate-btn');
  const addBtn = document.getElementById('add-turbine-btn');

  function renderTurbineList() {
    turbineListEl.innerHTML = '';
    emptyStateEl.style.display = turbines.length ? 'none' : '';
    calculateBtn.disabled = turbines.length === 0;
    turbines.forEach((t, i) => {
      const cat = categories[t.category];
      const row = document.createElement('div');
      row.className = 'turbine-item';
      row.innerHTML = `
        <div class="turbine-badge">${i + 1}</div>
        <div class="turbine-info">
          <div class="name">${escapeHtml(t.label)}</div>
          <div class="meta">${cat ? escapeHtml(cat.label) : t.category}${t.category === 'hoog' ? ' · ' + (t.method === 'afstandsband' ? 'per afstandsband' : 'vlak') : ''}</div>
        </div>
      `;
      const removeBtn = document.createElement('button');
      removeBtn.className = 'btn btn-ghost';
      removeBtn.type = 'button';
      removeBtn.setAttribute('aria-label', 'Verwijder turbine ' + (i + 1));
      removeBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>';
      removeBtn.addEventListener('click', () => {
        turbines = turbines.filter((x) => x.id !== t.id);
        renderTurbineList();
        renderMapCircles();
        hideResults();
      });
      row.appendChild(removeBtn);
      turbineListEl.appendChild(row);
    });
  }

  addBtn.addEventListener('click', () => {
    if (!selectedLocation) {
      if (locationMode === 'coords') {
        showToast('Vul coördinaten in en klik op "Bevestig".', true);
        coordsInput.focus();
      } else {
        showToast('Kies eerst een locatie uit de suggesties.', true);
        searchInput.focus();
      }
      return;
    }
    const category = categorySelect.value;
    const method = category === 'hoog' ? document.querySelector('input[name="method"]:checked').value : 'vlak';
    turbines.push({
      id: idCounter++,
      label: selectedLocation.label,
      lat: selectedLocation.lat,
      lon: selectedLocation.lon,
      category,
      method,
    });
    renderTurbineList();
    renderMapCircles();
    hideResults();
    searchInput.value = '';
    coordsInput.value = '';
    selectedLocation = null;
    locationHint.textContent = 'Begin met typen — resultaten via de PDOK Locatieserver.';
    coordsHint.textContent = 'WGS84-decimale graden — plak dit rechtstreeks vanuit Google Maps (rechtsklik op de kaart) of een GPS-toestel.';
    coordsHint.classList.remove('hint-error');
    showToast('Turbine toegevoegd.');
  });

  /* ---------------------------------------------------------------------
     Calculate
     --------------------------------------------------------------------- */
  const resultsSection = document.getElementById('results');
  const kpiGrid = document.getElementById('kpi-grid');
  const resultsTbody = document.getElementById('results-tbody');
  const resultsTotalRow = document.getElementById('results-total-row');
  let lastResult = null;
  let sortKey = 'afstand_centroide_m';
  let sortAsc = true;

  function hideResults() {
    resultsSection.classList.remove('visible');
  }

  function severityColor(pct) {
    const a = Math.abs(pct);
    if (a < 2) return 'var(--sev-0)';
    if (a < 3) return 'var(--sev-1)';
    if (a < 4.5) return 'var(--sev-2)';
    if (a < 6.5) return 'var(--sev-3)';
    return 'var(--sev-4)';
  }
  function severityHex(pct) {
    const a = Math.abs(pct);
    if (a < 2) return '#cfe4e0';
    if (a < 3) return '#ffe08a';
    if (a < 4.5) return '#ffb454';
    if (a < 6.5) return '#f2793a';
    return '#d43d3d';
  }

  calculateBtn.addEventListener('click', async () => {
    calculateBtn.disabled = true;
    calculateBtn.innerHTML = '<span class="spinner"></span> Berekenen…';
    try {
      const res = await fetch(`${API}/api/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turbines: turbines.map((t) => ({ label: t.label, lat: t.lat, lon: t.lon, category: t.category, method: t.method })),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Berekening mislukt');
      lastResult = data;
      renderResults(data);

      try {
        const noiseRes = await fetch(`${API}/api/calculate-noise`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            turbines: turbines.map((t) => ({ label: t.label, lat: t.lat, lon: t.lon, category: t.category, method: t.method })),
          }),
        });
        const noiseData = await noiseRes.json();
        if (!noiseRes.ok) throw new Error(noiseData.detail || 'Geluidsberekening mislukt');
        renderNoiseResults(noiseData);
      } catch (noiseErr) {
        console.error(noiseErr);
        showToast(noiseErr.message || 'Er ging iets mis bij de geluidsberekening.', true);
      }

      showToast('Berekening voltooid.');
    } catch (e) {
      console.error(e);
      showToast(e.message || 'Er ging iets mis bij het berekenen.', true);
    } finally {
      calculateBtn.disabled = false;
      calculateBtn.textContent = 'Berekenen';
    }
  });

  const noiseTbody = document.getElementById('noise-tbody');
  const noiseEmpty = document.getElementById('noise-empty');

  function renderNoiseResults(data) {
    if (noiseEmpty) noiseEmpty.style.display = 'none';
    const rows = data.rijen || [];
    noiseTbody.innerHTML = rows
      .map((row) => {
        const [t10, t30] = row.drempels;
        const cell = (d) => `
          <td class="num">${fmtNum(d.aantal_woningen, 1)}</td>
          <td class="num">${fmtEuro(d.kosten_per_jaar_euro)}</td>
          <td class="num">${fmtEuro(d.kosten_25jaar_euro)}</td>`;
        return `
      <tr>
        <td class="num">${fmtDist(row.afstand_m)}</td>
        <td class="num">${fmtNum(row.aantal_woningen, 1)}</td>
        <td class="num">${fmtNum(row.dba_7ms, 1)} dB(A)</td>
        <td class="num">${fmtNum(row.db_onweighted, 1)} dB</td>
        <td class="num">${fmtNum(row.pct_hinder, 1)}%</td>
        <td class="num">${fmtNum(row.pct_ernstige_hinder, 1)}%</td>
        ${cell(t10)}
        ${cell(t30)}
      </tr>`;
      })
      .join('');
  }

  function renderResults(data) {
    const warningsEl = document.getElementById('result-warnings');
    const warnings = data.warnings || [];
    warningsEl.innerHTML = warnings
      .map(
        (w) => `
      <div class="result-warning">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>
        <span>${escapeHtml(w)}</span>
      </div>`
      )
      .join('');

    const t = data.totalen;
    kpiGrid.innerHTML = `
      <div class="kpi-card accent">
        <div class="kpi-label">Geraakte woningen</div>
        <div class="kpi-value">${fmtNum(t.totaal_geraakte_woningen, 0)}</div>
        <div class="kpi-sub">verdeeld over ${t.aantal_buurten} buurten</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Totale waardedaling</div>
        <div class="kpi-value">${fmtEuro(t.totale_waardedaling_euro)}</div>
        <div class="kpi-sub">gem. ${fmtEuro(t.gemiddelde_waardedaling_per_woning_euro)} per woning</div>
      </div>
      <div class="kpi-card warning">
        <div class="kpi-label">Eigen risico (NMR, tot 4%)</div>
        <div class="kpi-value">${fmtEuro(t.totaal_normaal_maatschappelijk_risico_euro)}</div>
        <div class="kpi-sub">komt voor rekening van de eigenaar</div>
      </div>
      <div class="kpi-card success">
        <div class="kpi-label">Compensabele planschade (&gt;4%)</div>
        <div class="kpi-value">${fmtEuro(t.totaal_nadeelcompensatie_euro)}</div>
        <div class="kpi-sub">gem. ${fmtEuro(t.gemiddelde_nadeelcompensatie_per_woning_euro)} per woning</div>
      </div>
    `;
    renderTable();
    resultsSection.classList.add('visible');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    renderChoropleth(data.buurten);
  }

  function renderTable() {
    if (!lastResult) return;
    const rows = [...lastResult.buurten].sort((a, b) => {
      const va = a[sortKey],
        vb = b[sortKey];
      if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortAsc ? va - vb : vb - va;
    });
    resultsTbody.innerHTML = rows
      .map(
        (b) => `
      <tr>
        <td>${escapeHtml(b.buurtnaam || '—')}</td>
        <td>${escapeHtml(b.gemeentenaam || '—')}</td>
        <td class="num">${fmtDist(b.afstand_centroide_m)}</td>
        <td class="num">${fmtNum(b.geraakte_woningen, 1)}</td>
        <td class="num">${fmtEuro(b.gemiddelde_woz)}</td>
        <td class="num"><span class="severity-chip" style="background:${severityHex(b.gewogen_waardedaling_pct)}22;color:${severityHex(b.gewogen_waardedaling_pct)}"><span class="dot" style="background:${severityHex(b.gewogen_waardedaling_pct)}"></span>${b.gewogen_waardedaling_pct}%</span></td>
        <td class="num">${fmtEuro(b.totale_waardedaling_euro)}</td>
        <td class="num">${fmtEuro(b.eigen_risico_euro)}</td>
        <td class="num">${fmtEuro(b.nadeelcompensatie_euro)}</td>
      </tr>`
      )
      .join('');

    const t = lastResult.totalen;
    resultsTotalRow.innerHTML = `
      <td colspan="3">Totaal</td>
      <td class="num">${fmtNum(t.totaal_geraakte_woningen, 1)}</td>
      <td class="num">—</td>
      <td class="num">—</td>
      <td class="num">${fmtEuro(t.totale_waardedaling_euro)}</td>
      <td class="num">${fmtEuro(t.totaal_normaal_maatschappelijk_risico_euro)}</td>
      <td class="num">${fmtEuro(t.totaal_nadeelcompensatie_euro)}</td>
    `;
  }

  document.querySelectorAll('#results-table thead th[data-key]').forEach((th) => {
    th.addEventListener('click', () => {
      const key = th.dataset.key;
      if (sortKey === key) sortAsc = !sortAsc;
      else {
        sortKey = key;
        sortAsc = true;
      }
      renderTable();
    });
  });

  function renderChoropleth(buurten) {
    if (!mapReady) return;
    const features = buurten
      .filter((b) => b.geometry)
      .map((b) => ({
        type: 'Feature',
        geometry: b.geometry,
        properties: {
          buurtnaam: b.buurtnaam,
          gemeentenaam: b.gemeentenaam,
          geraakte_woningen: b.geraakte_woningen,
          gewogen_waardedaling_pct: b.gewogen_waardedaling_pct,
          gemiddelde_woz: b.gemiddelde_woz,
          totale_waardedaling_euro: b.totale_waardedaling_euro,
          color: severityHex(b.gewogen_waardedaling_pct),
        },
      }));
    map.getSource('buurten') && map.getSource('buurten').setData({ type: 'FeatureCollection', features });
  }

  /* ---------------------------------------------------------------------
     CSV export
     --------------------------------------------------------------------- */
  document.getElementById('export-csv-btn').addEventListener('click', () => {
    if (!turbines.length) {
      showToast('Voeg eerst turbines toe.', true);
      return;
    }
    const payload = turbines.map((t) => ({ label: t.label, lat: t.lat, lon: t.lon, category: t.category, method: t.method }));
    const url = `${API}/api/export/csv?data=${encodeURIComponent(JSON.stringify(payload))}`;
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  loadCategories();
  renderTurbineList();
})();
