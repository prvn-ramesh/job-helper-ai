/**
 * AutoJob AI — Dashboard Client Application
 */

const API_BASE = '/api/v1';

// State
let currentTab = 'overview';
let jobsPageOffset = 0;
const jobsPageLimit = 25;
let totalJobsCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupWorkerActions();
  setupProfileForm();
  setupJobsFilters();
  setupModal();

  // Initial Data Fetch
  loadStats();
  loadPendingReviews();
  loadJobs();
  loadProfile();

  // Refresh stats every 15s
  setInterval(loadStats, 15000);
});

/* ==========================================================================
   Navigation
   ========================================================================== */
function setupNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });
  document.querySelectorAll('.view-panel').forEach(p => {
    p.classList.toggle('active', p.id === `view-${tabId}`);
  });

  if (tabId === 'reviews') {
    loadPendingReviews();
  } else if (tabId === 'jobs') {
    loadJobs();
  } else if (tabId === 'settings') {
    loadProfile();
  } else if (tabId === 'overview') {
    loadStats();
  }
}

/* ==========================================================================
   API: Stats & Overview
   ========================================================================== */
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-discovered').innerText = data.discovered || 0;
    document.getElementById('stat-approved').innerText = data.approved || 0;
    document.getElementById('stat-filtered').innerText = data.filtered_out || 0;
    document.getElementById('stat-pending').innerText = data.pending_reviews || 0;
    document.getElementById('stat-applied').innerText = data.applied || 0;
    document.getElementById('stat-daily-limit').innerText = `Daily limit: ${data.daily_limit || 20}`;
    
    // Update badge count
    const badge = document.getElementById('review-badge-count');
    badge.innerText = data.pending_reviews || 0;
    badge.style.display = data.pending_reviews > 0 ? 'inline-block' : 'none';

    // Update Sheets Link if configured
    if (data.google_sheets_url) {
      document.getElementById('btn-open-sheets').href = data.google_sheets_url;
    }

    // App Mode
    document.getElementById('app-mode-indicator').innerText = 
      `Mode: ${data.application_mode === 'full-auto' ? 'Full-Auto (Autonomous)' : 'Semi-Auto (Review Gate Active)'}`;
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

/* ==========================================================================
   Worker Control Actions
   ========================================================================== */
function setupWorkerActions() {
  const btnDiscover = document.getElementById('btn-trigger-discover');
  const btnTriage = document.getElementById('btn-trigger-triage');
  const btnApply = document.getElementById('btn-trigger-apply');

  btnDiscover.addEventListener('click', async () => {
    setLoading(btnDiscover, true);
    try {
      const res = await fetch(`${API_BASE}/actions/discover`, { method: 'POST' });
      const data = await res.json();
      showToast(`Discovery completed: ${data.new_jobs_discovered} new jobs discovered!`, 'success');
      loadStats();
      loadJobs();
    } catch (err) {
      showToast('Discovery execution failed', 'error');
    } finally {
      setLoading(btnDiscover, false);
    }
  });

  btnTriage.addEventListener('click', async () => {
    setLoading(btnTriage, true);
    try {
      const res = await fetch(`${API_BASE}/actions/triage`, { method: 'POST' });
      const data = await res.json();
      showToast(`Triage completed: ${data.results.approved || 0} approved, ${data.results.filtered_out || 0} filtered`, 'success');
      loadStats();
      loadJobs();
    } catch (err) {
      showToast('Triage execution failed', 'error');
    } finally {
      setLoading(btnTriage, false);
    }
  });

  btnApply.addEventListener('click', async () => {
    setLoading(btnApply, true);
    try {
      const res = await fetch(`${API_BASE}/actions/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 5 })
      });
      const data = await res.json();
      showToast(`Apply batch completed: ${data.pending_review || 0} pending review, ${data.applied || 0} applied`, 'success');
      loadStats();
      loadPendingReviews();
      loadJobs();
    } catch (err) {
      showToast('Apply execution failed', 'error');
    } finally {
      setLoading(btnApply, false);
    }
  });
}

function setLoading(btn, isLoading) {
  const text = btn.querySelector('.btn-text');
  const spinner = btn.querySelector('.spinner');
  btn.disabled = isLoading;
  if (spinner) spinner.classList.toggle('hidden', !isLoading);
}

/* ==========================================================================
   Review Gate
   ========================================================================== */
async function loadPendingReviews() {
  try {
    const res = await fetch(`${API_BASE}/reviews/pending`);
    if (!res.ok) return;
    const items = await res.json();

    const container = document.getElementById('review-list-container');
    const emptyState = document.getElementById('empty-reviews-state');

    // Remove existing cards
    const existingCards = container.querySelectorAll('.review-item-card');
    existingCards.forEach(c => c.remove());

    if (!items || items.length === 0) {
      emptyState.style.display = 'block';
      return;
    }

    emptyState.style.display = 'none';

    items.forEach(item => {
      const card = createReviewCard(item);
      container.appendChild(card);
    });
  } catch (err) {
    console.error('Failed to load pending reviews:', err);
  }
}

function createReviewCard(item) {
  const div = document.createElement('div');
  div.className = 'review-item-card';
  div.id = `review-card-${item.job_uid}`;

  let fieldsHtml = '';
  if (item.filled_fields) {
    for (const [key, val] of Object.entries(item.filled_fields)) {
      fieldsHtml += `
        <div class="field-pair">
          <span class="label">${escapeHtml(key)}</span>
          <span class="value">${escapeHtml(String(val))}</span>
        </div>
      `;
    }
  }

  // Convert screenshot path to accessible URL
  const shotUrl = item.screenshot_path ? `/${item.screenshot_path}` : '';

  div.innerHTML = `
    <div class="review-item-header">
      <div>
        <h3>${escapeHtml(item.title)}</h3>
        <div class="review-meta">
          <span>🏢 ${escapeHtml(item.company)}</span>
          <span>⚡ Platform: ${escapeHtml(item.platform.toUpperCase())}</span>
          <span><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener" style="color: var(--primary);">View Posting ↗</a></span>
        </div>
      </div>
      <span class="badge badge-pending_review">Awaiting Approval</span>
    </div>

    <div class="review-body">
      <div class="review-fields-col">
        <h4>11+ Pre-filled Application Fields</h4>
        <div class="fields-grid">
          ${fieldsHtml || '<p style="color: var(--text-dim);">No pre-filled fields recorded</p>'}
        </div>
      </div>

      <div class="review-screenshot-col">
        <h4>Form Verification Screenshot</h4>
        ${shotUrl ? `
          <div class="screenshot-preview-wrapper" onclick="openScreenshotModal('${shotUrl}', '${escapeHtml(item.title)}')">
            <img src="${shotUrl}" alt="Application Screenshot" loading="lazy">
            <div class="zoom-overlay">🔍 Click to inspect full screenshot</div>
          </div>
        ` : '<p style="color: var(--text-dim);">No screenshot available</p>'}
      </div>
    </div>

    <div class="review-footer">
      <span style="font-size: 12px; color: var(--text-muted);">${escapeHtml(item.notes || 'Awaiting candidate review in semi-auto mode')}</span>
      <div class="review-actions">
        <button class="btn btn-danger btn-sm" onclick="rejectReview('${item.job_uid}')">Reject</button>
        <button class="btn btn-accent btn-sm" onclick="approveReview('${item.job_uid}')">Approve & Submit Application</button>
      </div>
    </div>
  `;

  return div;
}

async function approveReview(jobUid) {
  if (!confirm('Are you sure you want to approve and submit this application?')) return;
  try {
    const res = await fetch(`${API_BASE}/reviews/${jobUid}/approve`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Application submitted successfully!', 'success');
    } else {
      showToast(`Submission finished: ${data.confirmation || 'Check job status'}`, 'info');
    }
    loadStats();
    loadPendingReviews();
    loadJobs();
  } catch (err) {
    showToast('Failed to approve application', 'error');
  }
}

async function rejectReview(jobUid) {
  const reason = prompt('Reason for rejection:', 'Not interested in this specific role');
  if (reason === null) return;
  try {
    await fetch(`${API_BASE}/reviews/${jobUid}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    });
    showToast('Application rejected and archived', 'info');
    loadStats();
    loadPendingReviews();
    loadJobs();
  } catch (err) {
    showToast('Failed to reject application', 'error');
  }
}

/* ==========================================================================
   Jobs Pipeline Table
   ========================================================================== */
function setupJobsFilters() {
  const searchInput = document.getElementById('job-search-input');
  const statusSelect = document.getElementById('filter-status');
  const platformSelect = document.getElementById('filter-platform');
  const workModeSelect = document.getElementById('filter-work-mode');

  let debounceTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      jobsPageOffset = 0;
      loadJobs();
    }, 300);
  });

  statusSelect.addEventListener('change', () => { jobsPageOffset = 0; loadJobs(); });
  platformSelect.addEventListener('change', () => { jobsPageOffset = 0; loadJobs(); });
  workModeSelect.addEventListener('change', () => { jobsPageOffset = 0; loadJobs(); });

  document.getElementById('btn-prev-page').addEventListener('click', () => {
    if (jobsPageOffset > 0) {
      jobsPageOffset -= jobsPageLimit;
      loadJobs();
    }
  });

  document.getElementById('btn-next-page').addEventListener('click', () => {
    if (jobsPageOffset + jobsPageLimit < totalJobsCount) {
      jobsPageOffset += jobsPageLimit;
      loadJobs();
    }
  });
}

async function loadJobs() {
  try {
    const status = document.getElementById('filter-status').value;
    const platform = document.getElementById('filter-platform').value;
    const workMode = document.getElementById('filter-work-mode').value;
    const search = document.getElementById('job-search-input').value;

    const params = new URLSearchParams({
      limit: jobsPageLimit,
      offset: jobsPageOffset
    });
    if (status && status !== 'all') params.append('status', status);
    if (platform) params.append('platform', platform);
    if (workMode) params.append('work_mode', workMode);
    if (search) params.append('search', search);

    const res = await fetch(`${API_BASE}/jobs?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();

    totalJobsCount = data.total;
    renderJobsTable(data.jobs);
    updatePagination(data.total);
  } catch (err) {
    console.error('Failed to load jobs:', err);
  }
}

function renderJobsTable(jobs) {
  const tbody = document.getElementById('jobs-table-body');
  tbody.innerHTML = '';

  if (!jobs || jobs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-dim);">No jobs found matching the selected filters</td></tr>`;
    return;
  }

  jobs.forEach(j => {
    const tr = document.createElement('tr');

    // Score badge
    let scoreClass = 'score-low';
    if (j.score >= 7.5) scoreClass = 'score-high';
    else if (j.score >= 6.0) scoreClass = 'score-mid';

    // Status badge
    const statusClass = `badge-${j.status}`;

    tr.innerHTML = `
      <td>
        <div style="font-weight:600; color:var(--text-main);">${escapeHtml(j.title)}</div>
        <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(j.company)}</div>
      </td>
      <td><span style="font-size:12px; text-transform:capitalize;">${escapeHtml(j.platform)}</span></td>
      <td>
        <div>${escapeHtml(j.city || j.location || 'Unknown')}</div>
        <span class="badge" style="font-size:10px; background:rgba(255,255,255,0.06);">${escapeHtml(j.work_mode)}</span>
      </td>
      <td>${j.min_experience_years ? j.min_experience_years + ' yrs' : '--'}</td>
      <td><span class="score-badge ${scoreClass}">${j.score ? j.score.toFixed(1) : '--'}</span></td>
      <td><span class="badge ${statusClass}">${escapeHtml(j.status)}</span></td>
      <td style="max-width:240px; font-size:12px; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(j.filter_reason || j.notes || '')}">
        ${escapeHtml(j.filter_reason || j.notes || '--')}
      </td>
      <td>
        <a href="${escapeHtml(j.apply_url)}" target="_blank" rel="noopener" class="btn btn-secondary btn-sm" style="padding: 2px 8px;">Apply ↗</a>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function updatePagination(total) {
  const start = total === 0 ? 0 : jobsPageOffset + 1;
  const end = Math.min(jobsPageOffset + jobsPageLimit, total);
  document.getElementById('pagination-info').innerText = `Showing ${start}-${end} of ${total}`;

  document.getElementById('btn-prev-page').disabled = jobsPageOffset === 0;
  document.getElementById('btn-next-page').disabled = jobsPageOffset + jobsPageLimit >= total;
}

/* ==========================================================================
   Profile & Candidate Settings
   ========================================================================== */
async function loadProfile() {
  try {
    const res = await fetch(`${API_BASE}/profile`);
    if (!res.ok) return;
    const p = await res.json();

    document.getElementById('inp-current-ctc').value = p.current_ctc_inr || 400000;
    document.getElementById('inp-expected-ctc').value = p.expected_ctc_inr || 800000;
    document.getElementById('inp-experience-years').value = p.years_of_experience || 2;
    document.getElementById('inp-location').value = p.location || 'Bengaluru, India';
    document.getElementById('inp-notice-period').value = p.notice_period || 'Immediate';

    const visaCheck = document.getElementById('toggle-visa-sponsorship');
    visaCheck.checked = p.requires_visa_sponsorship === true;
    updateVisaLabel(visaCheck.checked);

    // Resume Strategy Radio
    const radios = document.getElementsByName('resume_strategy');
    radios.forEach(r => {
      r.checked = r.value === (p.resume_strategy || 'uploaded_pdf');
    });

    // Fact elements
    document.getElementById('fact-name').innerText = p.name || '';
    document.getElementById('fact-email').innerText = p.email || '';
    document.getElementById('fact-phone').innerText = p.phone || '';
    document.getElementById('fact-title').innerText = `${p.current_title} (${p.years_of_experience} yrs)`;
    document.getElementById('fact-education').innerText = `${p.degree}, ${p.institution} (${p.graduation_year})`;
  } catch (err) {
    console.error('Failed to load profile:', err);
  }
}

function setupProfileForm() {
  const form = document.getElementById('profile-form');
  const visaCheck = document.getElementById('toggle-visa-sponsorship');

  visaCheck.addEventListener('change', () => {
    updateVisaLabel(visaCheck.checked);
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-save-profile');
    btn.disabled = true;
    btn.innerText = 'Saving...';

    const selectedStrategy = document.querySelector('input[name="resume_strategy"]:checked').value;

    const payload = {
      current_ctc_inr: parseInt(document.getElementById('inp-current-ctc').value),
      expected_ctc_inr: parseInt(document.getElementById('inp-expected-ctc').value),
      years_of_experience: parseFloat(document.getElementById('inp-experience-years').value),
      location: document.getElementById('inp-location').value,
      notice_period: document.getElementById('inp-notice-period').value,
      requires_visa_sponsorship: visaCheck.checked,
      resume_strategy: selectedStrategy
    };

    try {
      const res = await fetch(`${API_BASE}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showToast('Candidate preferences & CTC successfully saved!', 'success');
        loadProfile();
      } else {
        showToast('Error saving preferences', 'error');
      }
    } catch (err) {
      showToast('Error connecting to API', 'error');
    } finally {
      btn.disabled = false;
      btn.innerText = 'Save Candidate Preferences';
    }
  });
}

function updateVisaLabel(isChecked) {
  const label = document.getElementById('label-visa-sponsorship');
  label.innerText = isChecked 
    ? 'Visa Sponsorship Required (Apply only with sponsorship)' 
    : 'No Foreign Visa Needed (Filter out onsite abroad; Remote eligible)';
}

/* ==========================================================================
   Modal Viewer & Toast Utilities
   ========================================================================== */
function setupModal() {
  const modal = document.getElementById('screenshot-modal');
  const closeBtn = document.getElementById('modal-close-btn');
  const overlay = document.getElementById('modal-overlay');

  const closeModal = () => modal.classList.add('hidden');
  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', closeModal);
}

function openScreenshotModal(imgSrc, title) {
  const modal = document.getElementById('screenshot-modal');
  const modalImg = document.getElementById('modal-img');
  const modalTitle = document.getElementById('modal-title');

  modalImg.src = imgSrc;
  modalTitle.innerText = `Verification Screenshot: ${title}`;
  modal.classList.remove('hidden');
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = msg;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
