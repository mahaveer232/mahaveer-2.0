/**
 * app.js — Mahaveer 2.0 Frontend Logic
 * Handles: tab switching, video controls, polling (stats + violations),
 * video upload, vehicle DB / challan tables, modal, toasts.
 */

// ─── State ────────────────────────────────────────────────────────────────────
let isRunning       = false;
let pollInterval    = null;
let prevCounts      = { total: 0, helmet: 0, noHelmet: 0, challans: 0 };
let localViolations = [];   // client-side copy for modal access
let clearRequested  = false;

// ─── On load ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadVehicles();
  loadChallans();
  startPolling();
  // Keep stream alive (suppress browser 404-on-idle)
  document.getElementById('video-stream').src = '/video_feed?' + Date.now();
});

// ══════════════════════════════════════════════════════════════════════════════
// TAB SWITCHING
// ══════════════════════════════════════════════════════════════════════════════
function switchTab(tab) {
  // Hide all panels
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  document.getElementById('tab-' + tab).classList.add('active');
  document.getElementById('nav-' + tab).classList.add('active');

  if (tab === 'database') loadVehicles();
  if (tab === 'challans') loadChallans();
}

// ══════════════════════════════════════════════════════════════════════════════
// VIDEO CONTROLS
// ══════════════════════════════════════════════════════════════════════════════
async function startSample() {
  showToast('Loading sample video…', 'info');
  const res  = await fetch('/api/start_sample', { method: 'POST' });
  const data = await res.json();
  if (res.ok) {
    onStreamStart('sample', data);
    showToast('▶ Sample video detection started!', 'success');
  } else {
    showToast('❌ ' + (data.error || 'Could not load sample video.'), 'error');
  }
}

async function startCamera() {
  showToast('Connecting to camera…', 'info');
  const res  = await fetch('/api/start_camera', { method: 'POST' });
  const data = await res.json();
  if (res.ok) {
    onStreamStart('camera', data);
    showToast('📷 Live camera detection started!', 'success');
  } else {
    showToast('❌ ' + (data.error || 'No camera found.'), 'error');
  }
}

async function stopFeed() {
  await fetch('/api/stop', { method: 'POST' });
  onStreamStop();
  showToast('⏹ Detection stopped.', 'info');
}

function uploadVideo(input) {
  if (!input.files.length) return;
  const file     = input.files[0];
  const maxBytes = 500 * 1024 * 1024;   // 500 MB

  if (file.size > maxBytes) {
    showToast('❌ File too large (max 500 MB).', 'error');
    input.value = '';
    return;
  }

  const formData = new FormData();
  formData.append('video', file);

  const progress = document.getElementById('upload-progress');
  const fill     = document.getElementById('progress-fill');
  const label    = document.getElementById('progress-label');
  progress.style.display = 'flex';
  fill.style.width       = '0%';
  label.textContent      = 'Uploading…';

  // XHR for real upload progress
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/upload_video');

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      fill.style.width  = pct + '%';
      label.textContent = `Uploading… ${pct}%`;
    }
  };

  xhr.onload = () => {
    progress.style.display = 'none';
    input.value = '';
    if (xhr.status === 200) {
      const data = JSON.parse(xhr.responseText);
      onStreamStart('upload', data);
      showToast('📁 Video uploaded and detection started!', 'success');
    } else {
      try {
        const err = JSON.parse(xhr.responseText);
        showToast('❌ ' + (err.error || 'Upload failed.'), 'error');
      } catch { showToast('❌ Upload failed.', 'error'); }
    }
  };

  xhr.onerror = () => {
    progress.style.display = 'none';
    showToast('❌ Network error during upload.', 'error');
  };

  xhr.send(formData);
}

function onStreamStart(source, data) {
  isRunning = true;
  setButtonState(true);

  // Hide video overlay
  document.getElementById('video-overlay').classList.add('hidden');
  document.getElementById('stream-dot').classList.add('live');

  // Reset local violations
  localViolations = [];
  clearRequested  = false;
  document.getElementById('violation-list').innerHTML =
    '<div class="empty-state" id="violation-empty">' +
    '<div style="font-size:2rem;margin-bottom:8px">🛡️</div>' +
    '<p>Monitoring for violations…</p></div>';
}

function onStreamStop() {
  isRunning = false;
  setButtonState(false);
  document.getElementById('stream-dot').classList.remove('live');
  setStatusIndicator(false);
}

function setButtonState(running) {
  document.getElementById('btn-sample').disabled = running;
  document.getElementById('btn-camera').disabled = running;
  document.getElementById('btn-upload-label').style.pointerEvents = running ? 'none' : '';
  document.getElementById('btn-upload-label').style.opacity       = running ? '.38' : '';
  document.getElementById('btn-stop').disabled   = !running;
}

// ══════════════════════════════════════════════════════════════════════════════
// POLLING — Stats + Violations
// ══════════════════════════════════════════════════════════════════════════════
function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(poll, 2000);
  poll();   // immediate first call
}

async function poll() {
  await Promise.all([fetchStats(), fetchViolations()]);
}

async function fetchStats() {
  try {
    const res  = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();

    setStatValue('stat-total',    data.total_detected);
    setStatValue('stat-helmet',   data.helmet_count);
    setStatValue('stat-nohelmet', data.no_helmet_count);
    setStatValue('stat-challans', data.challans_sent);

    // Challan badge on sidebar
    document.getElementById('challan-badge').textContent = data.challans_sent || 0;

    // Status indicator
    setStatusIndicator(data.is_running);
    document.getElementById('status-fps').textContent =
      data.is_running ? `${data.fps} FPS · ${data.source_label || ''}` : '—';

    // Sync button state if backend says stopped
    if (!data.is_running && isRunning) {
      isRunning = false;
      setButtonState(false);
      document.getElementById('stream-dot').classList.remove('live');
    }
  } catch (e) { /* server might not be ready yet */ }
}

async function fetchViolations() {
  try {
    const res  = await fetch('/api/violations');
    if (!res.ok) return;
    const data = await res.json();

    if (!data.length) return;

    // Find new violations not yet shown
    const displayed = clearRequested ? 0 : localViolations.length;
    const incoming  = data.slice(0, data.length);

    // Determine new ones by comparing count
    const newOnes = incoming.slice(0, Math.max(0, data.length - localViolations.length + (clearRequested ? localViolations.length : 0)));
    if (clearRequested) {
      localViolations = [];
      clearRequested  = false;
    }

    newOnes.forEach(v => {
      localViolations.unshift(v);
      renderViolation(v);
    });

    localViolations = data;   // sync with server
    renderAllViolations(data);

  } catch (e) { }
}

// ══════════════════════════════════════════════════════════════════════════════
// VIOLATION RENDERING
// ══════════════════════════════════════════════════════════════════════════════
function renderAllViolations(violations) {
  const list = document.getElementById('violation-list');

  if (!violations.length) {
    list.innerHTML =
      '<div class="empty-state" id="violation-empty">' +
      '<div style="font-size:2rem;margin-bottom:8px">🛡️</div>' +
      '<p>No violations detected yet.</p></div>';
    return;
  }

  // Only re-render if count changed
  const existing = list.querySelectorAll('.violation-card').length;
  if (existing === violations.length) return;

  list.innerHTML = '';
  violations.forEach((v, idx) => {
    list.appendChild(buildViolationCard(v, idx));
  });
}

function renderViolation(v) {
  const list  = document.getElementById('violation-list');
  const empty = document.getElementById('violation-empty');
  if (empty) empty.remove();
  list.insertBefore(buildViolationCard(v, 0), list.firstChild);
}

function buildViolationCard(v, idx) {
  const card = document.createElement('div');
  card.className = 'violation-card';
  card.setAttribute('data-idx', idx);
  card.onclick   = () => openModal(v);

  const emailTag = v.email_sent
    ? '<span class="vc-tag sent">📧 Challan Sent</span>'
    : (v.owner !== 'Unknown'
        ? '<span class="vc-tag unknown">Owner Found</span>'
        : '<span class="vc-tag unknown">Unknown</span>');

  card.innerHTML = `
    <div class="vc-top">
      <span class="vc-plate">${escHtml(v.plate)}</span>
      <span class="vc-time">${escHtml(v.timestamp)}</span>
    </div>
    <div class="vc-owner">${escHtml(v.owner)}</div>
    <div class="vc-meta">
      <span class="vc-vehicle">${escHtml(v.vehicle || '—')}</span>
      ${emailTag}
      <span class="vc-conf">${escHtml(v.confidence)}</span>
    </div>`;
  return card;
}

function clearViolations() {
  clearRequested = true;
  localViolations = [];
  const list = document.getElementById('violation-list');
  list.innerHTML =
    '<div class="empty-state" id="violation-empty">' +
    '<div style="font-size:2rem;margin-bottom:8px">🛡️</div>' +
    '<p>No violations detected yet.</p></div>';
}

// ══════════════════════════════════════════════════════════════════════════════
// VEHICLE DATABASE TABLE
// ══════════════════════════════════════════════════════════════════════════════
async function loadVehicles() {
  const tbody = document.getElementById('vehicle-tbody');
  tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Loading…</td></tr>';

  try {
    const res  = await fetch('/api/vehicles');
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="loading-cell">' +
        'No records found. Run <code>python setup_db.py</code> first.' +
        '</td></tr>';
      return;
    }

    tbody.innerHTML = data.map((v, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><span class="tag-plate">${escHtml(v.plate_number || v.plate || '')}</span></td>
        <td style="color:var(--text-primary);font-weight:500">${escHtml(v.owner_name || '')}</td>
        <td>${escHtml(v.email || '')}</td>
        <td>${escHtml(v.phone || '')}</td>
        <td>${escHtml(v.vehicle_model || '')}</td>
        <td style="white-space:normal;max-width:200px">${escHtml(v.address || '')}</td>
      </tr>`).join('');
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Error loading data.</td></tr>';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// CHALLANS TABLE
// ══════════════════════════════════════════════════════════════════════════════
async function loadChallans() {
  const tbody = document.getElementById('challan-tbody');
  tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Loading…</td></tr>';

  try {
    const res  = await fetch('/api/challans');
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="loading-cell">No challans issued yet.</td></tr>';
      return;
    }

    tbody.innerHTML = data.map((c, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><span class="tag-plate">${escHtml(c.plate_number || c.plate || '')}</span></td>
        <td style="color:var(--text-primary);font-weight:500">${escHtml(c.owner_name || c.owner || 'Unknown')}</td>
        <td>${escHtml(c.email || 'N/A')}</td>
        <td>${escHtml(c.timestamp || '')}</td>
        <td style="color:var(--red)">${escHtml(c.violation_type || c.violation || 'No Helmet')}</td>
        <td>${c.email_sent
              ? '<span class="tag-sent">✅ Sent</span>'
              : '<span class="tag-no">—</span>'}</td>
      </tr>`).join('');
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Error loading data.</td></tr>';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL
// ══════════════════════════════════════════════════════════════════════════════
function openModal(v) {
  const body = document.getElementById('modal-body');
  body.innerHTML = [
    row('🚗 Plate Number',  `<span class="tag-plate">${escHtml(v.plate)}</span>`),
    row('🕐 Detected At',   escHtml(v.timestamp)),
    row('👤 Owner',         escHtml(v.owner)),
    row('🏍️ Vehicle',       escHtml(v.vehicle || '—')),
    row('📧 Email',         escHtml(v.email)),
    row('📊 Confidence',    escHtml(v.confidence)),
    row('📬 Challan Email', v.email_sent
          ? '<span style="color:#4ade80;font-weight:600">✅ Sent</span>'
          : '<span style="color:var(--text-muted)">Not sent</span>'),
  ].join('');

  document.getElementById('modal-backdrop').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-backdrop').classList.remove('open');
}

function row(label, value) {
  return `<div class="modal-row">
    <span class="modal-label">${label}</span>
    <span class="modal-value">${value}</span>
  </div>`;
}

// Close modal on Escape
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ══════════════════════════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════════════════════════
let toastTimer = null;
function showToast(message, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent  = message;
  t.className    = `toast ${type} show`;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
}

// ══════════════════════════════════════════════════════════════════════════════
// STATUS INDICATOR
// ══════════════════════════════════════════════════════════════════════════════
function setStatusIndicator(running) {
  const dot   = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  if (running) {
    dot.className   = 'status-dot running';
    label.textContent = 'Processing';
  } else {
    dot.className   = 'status-dot idle';
    label.textContent = 'Idle';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// STAT ANIMATION
// ══════════════════════════════════════════════════════════════════════════════
function setStatValue(elId, newVal) {
  const el   = document.getElementById(elId);
  const prev = parseInt(el.textContent) || 0;
  if (prev === newVal) return;

  el.textContent = newVal;
  el.style.transform = 'scale(1.15)';
  setTimeout(() => el.style.transform = '', 200);
}

// ══════════════════════════════════════════════════════════════════════════════
// UTILITY
// ══════════════════════════════════════════════════════════════════════════════
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
