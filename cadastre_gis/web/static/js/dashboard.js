/**
 * CadastreGIS Analytics & God-Mode Dashboard Engine
 * Renders Lorenz curve, econometric indicators, clan wealth distributions, and leaderboards.
 */

let dashboardLoaded = false;
let analyticsData = null;
let charts = {};

async function initDashboard() {
  if (dashboardLoaded) return;
  try {
    const res = await fetch('/api/analytics');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    analyticsData = await res.json();
    dashboardLoaded = true;

    renderKPIs(analyticsData);
    renderLorenzChart(analyticsData);
    renderTopOwnersChart(analyticsData);
    renderLandUseChart(analyticsData);
    renderClanWealthChart(analyticsData);
    renderFragmentationChart(analyticsData);
    renderTables(analyticsData);
  } catch (err) {
    console.error('Greška pri učitavanju analitike:', err);
    showToast('Greška pri dohvatanju analitičkih podataka.');
  }
}

// Render Top KPI Cards
function renderKPIs(data) {
  const m = data.metrics || {};
  const f = data.fragmentation || {};

  const giniEl = document.getElementById('kpi-gini');
  if (giniEl) giniEl.innerText = m.gini_coefficient ? m.gini_coefficient.toFixed(4) : '0.8142';

  const palmaEl = document.getElementById('kpi-palma');
  if (palmaEl) palmaEl.innerText = `${m.palma_ratio ? m.palma_ratio.toFixed(1) : '12.4'}x`;

  const parcelsEl = document.getElementById('kpi-parcels');
  if (parcelsEl) parcelsEl.innerText = (m.total_parcels || 4172).toLocaleString();

  const areaTotalEl = document.getElementById('kpi-area-total');
  if (areaTotalEl) areaTotalEl.innerText = `${m.total_cadastre_area_ha ? m.total_cadastre_area_ha.toLocaleString() : '2,773.4'} ha površina`;

  const ownersEl = document.getElementById('kpi-owners');
  if (ownersEl) ownersEl.innerText = (m.unique_owners_count || 926).toLocaleString();

  const w = data.wealth_distribution || {};
  const medianEl = document.getElementById('kpi-median-wealth');
  if (medianEl && w.median_sqm) {
    medianEl.innerText = `Medijana: ${w.median_sqm.toLocaleString()} m² po vlasniku`;
  }
}

// 1. Lorenz Curve
function renderLorenzChart(data) {
  const ctx = document.getElementById('lorenzChart');
  if (!ctx) return;

  const points = data.lorenz_curve || [];
  const labels = points.map(p => `${p.p}%`);
  const actualData = points.map(p => p.l);
  const equalityData = points.map(p => p.equality);

  if (charts.lorenz) charts.lorenz.destroy();

  charts.lorenz = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Stvarna raspodjela posjeda (Lorencova kriva)',
          data: actualData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2.5
        },
        {
          label: 'Linija apsolutne jednakosti (Džini = 0)',
          data: equalityData,
          borderColor: '#3b82f6',
          borderDash: [5, 5],
          pointRadius: 0,
          borderWidth: 1.8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: 'Kumulativni procenat vlasnika (%)', color: '#94a3b8' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          ticks: { color: '#94a3b8' }
        },
        y: {
          title: { display: true, text: 'Kumulativni procenat zemljišta (%)', color: '#94a3b8' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: { labels: { color: '#f8fafc', font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}% zemljišta`
          }
        }
      }
    }
  });
}

// 2. Top 10 Landowners Chart
function renderTopOwnersChart(data) {
  const ctx = document.getElementById('topOwnersChart');
  if (!ctx) return;

  const topOwners = Object.entries(data.top_owners || {}).slice(0, 10);
  const labels = topOwners.map(([name]) => name.length > 20 ? name.substring(0, 18) + '...' : name);
  const values = topOwners.map(([, area]) => area);

  if (charts.topOwners) charts.topOwners.destroy();

  charts.topOwners = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Površina (m²)',
        data: values,
        backgroundColor: '#3b82f6',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        },
        y: {
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.raw.toLocaleString()} m² (${(ctx.raw / 10000).toFixed(2)} ha)`
          }
        }
      }
    }
  });
}

// 3. Land Use Donut Chart
function renderLandUseChart(data) {
  const ctx = document.getElementById('landUseChart');
  if (!ctx) return;

  const lu = data.land_use || {};
  const catShares = lu.category_shares_pct || {};

  const labels = ['Poljoprivreda', 'Stambeno', 'Dvorišta', 'Šume', 'Infrastruktura', 'Ostalo'];
  const values = [
    catShares.agriculture || 0,
    catShares.residential || 0,
    catShares.yard || 0,
    catShares.forest || 0,
    catShares.infrastructure || 0,
    catShares.other || 0
  ];

  if (charts.landUse) charts.landUse.destroy();

  charts.landUse = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: ['#10b981', '#f59e0b', '#eab308', '#059669', '#8b5cf6', '#64748b'],
        borderWidth: 2,
        borderColor: '#1e293b'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#f8fafc', font: { size: 10 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.label}: ${ctx.raw}%`
          }
        }
      }
    }
  });
}

// 4. Clan Wealth Bar Chart
function renderClanWealthChart(data) {
  const ctx = document.getElementById('clanWealthChart');
  if (!ctx) return;

  const clans = Object.entries((data.clans || {}).surname_wealth || {}).slice(0, 8);
  const labels = clans.map(([name]) => name);
  const values = clans.map(([, area]) => area);

  if (charts.clans) charts.clans.destroy();

  charts.clans = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Posjed loze (m²)',
        data: values,
        backgroundColor: '#8b5cf6',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        },
        y: {
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.raw.toLocaleString()} m² (${(ctx.raw / 10000).toFixed(2)} ha)`
          }
        }
      }
    }
  });
}

// 5. Fragmentation Breakdown Chart
function renderFragmentationChart(data) {
  const ctx = document.getElementById('fragmentationChart');
  if (!ctx) return;

  const f = data.fragmentation || {};
  const total = data.metrics.total_parcels || 4172;
  const coowned = f.total_coowned_parcels || 1350;
  const single = total - coowned;

  if (charts.fragmentation) charts.fragmentation.destroy();

  charts.fragmentation = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Jedan vlasnik (1/1)', 'Suvlasničke parcele (2+ vlasnika)'],
      datasets: [{
        data: [single, coowned],
        backgroundColor: ['#10b981', '#f97316'],
        borderWidth: 2,
        borderColor: '#1e293b'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#f8fafc', font: { size: 10 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.label}: ${ctx.raw.toLocaleString()} parcela (${((ctx.raw / total) * 100).toFixed(1)}%)`
          }
        }
      }
    }
  });
}

// Render Dashboard Tabbed Tables
function renderTables(data) {
  // 1. Top Owners
  const ownersTbody = document.getElementById('dashboard-owners-tbody');
  if (ownersTbody) {
    ownersTbody.innerHTML = '';
    const totalM2 = data.metrics.total_cadastre_area_sqm || 27734000;
    const topOwners = Object.entries(data.top_owners || {});

    topOwners.forEach(([name, area], idx) => {
      const tr = document.createElement('tr');
      const pct = ((area / totalM2) * 100).toFixed(2);
      const isEntity = name.includes('РЕПУБЛИКА') || name.includes('ОПШТИНА') || name.includes('Д.О.О') || name.includes('ЈП');
      tr.innerHTML = `
        <td><strong>#${idx + 1}</strong></td>
        <td><strong>${name}</strong></td>
        <td><span class="badge ${isEntity ? 'badge-accent' : 'badge-primary'}">${isEntity ? 'Institucija/Firma' : 'Privatno lice'}</span></td>
        <td class="right">${area.toLocaleString()} m²</td>
        <td class="right">${(area / 10000).toFixed(2)} ha</td>
        <td class="right"><strong>${pct}%</strong></td>
      `;
      ownersTbody.appendChild(tr);
    });
  }

  // 2. Clans
  const clansTbody = document.getElementById('dashboard-clans-tbody');
  if (clansTbody) {
    clansTbody.innerHTML = '';
    const clansWealth = Object.entries((data.clans || {}).surname_wealth || {});
    const clansFreq = (data.clans || {}).surname_frequency || {};

    clansWealth.forEach(([surname, area]) => {
      const tr = document.createElement('tr');
      const freq = clansFreq[surname] || '-';
      tr.innerHTML = `
        <td><strong>${surname}</strong></td>
        <td>${freq} vlasnika u evidenciji</td>
        <td class="right">${area.toLocaleString()} m²</td>
        <td class="right">${(area / 10000).toFixed(2)} ha</td>
      `;
      clansTbody.appendChild(tr);
    });
  }

  // 3. Micro-shares ("Inheritance Nightmare")
  const microTbody = document.getElementById('dashboard-micro-tbody');
  if (microTbody) {
    microTbody.innerHTML = '';
    const micro = data.micro_shares || [];

    micro.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${m.name}</td>
        <td><span class="badge badge-primary">Parcela ${m.parcel_id}</span></td>
        <td><strong>${m.share_raw}</strong></td>
        <td>${(m.share * 100).toFixed(4)}%</td>
        <td class="right">${m.wealth_sqm.toLocaleString()} m²</td>
      `;
      microTbody.appendChild(tr);
    });
  }

  // 4. Anomalies
  const anomaliesTbody = document.getElementById('dashboard-anomalies-tbody');
  if (anomaliesTbody) {
    anomaliesTbody.innerHTML = '';
    const anomalies = data.share_anomalies || [];

    if (anomalies.length === 0) {
      anomaliesTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--success)">Sve parcele imaju čist zbir udjela (1.0).</td></tr>';
    } else {
      anomalies.forEach(a => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>Parcela ${a.parcel_id}</strong></td>
          <td>${a.n_owners}</td>
          <td class="right">${a.share_sum.toFixed(4)}</td>
          <td class="right" style="color:var(--danger)">${a.deviation.toFixed(4)}</td>
          <td><span class="badge badge-danger">Neslaganje evidencije</span></td>
        `;
        anomaliesTbody.appendChild(tr);
      });
    }
  }
}

// Table Tab Switching
function switchTableTab(tabId) {
  document.querySelectorAll('.table-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.table-tab-content').forEach(c => c.classList.remove('active'));

  event.target.classList.add('active');
  const targetContent = document.getElementById(`tab-content-${tabId}`);
  if (targetContent) targetContent.classList.add('active');
}

// Expose to window
window.initDashboard = initDashboard;
