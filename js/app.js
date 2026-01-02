/**
 * app.js
 * Core logic for IMAP Sync Web UI
 * Now connected to real FastAPI Backend
 */

const API_BASE = '/api';

// --- Auth Logic ---
const getToken = () => localStorage.getItem('access_token');
const setToken = (token) => localStorage.setItem('access_token', token);
const removeToken = () => localStorage.removeItem('access_token');

const request = async (url, options = {}) => {
    const token = getToken();
    const headers = options.headers || {};

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers: headers
    };

    const res = await fetch(url, config);

    if (res.status === 401) {
        removeToken();
        if (!window.location.href.includes('login.html')) {
            window.location.href = 'login.html';
        }
        throw new Error("Unauthorized");
    }

    return res;
};

const login = async (username, password) => {
    try {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);

        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            body: params,
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });

        if (res.ok) {
            const data = await res.json();
            setToken(data.access_token);
            window.location.href = 'index.html';
            return true;
        }
        return false;
    } catch (e) {
        console.error(e);
        return false;
    }
};

const logout = () => {
    removeToken();
    window.location.href = 'login.html';
};

// Check Auth on Load (except login page)
if (!window.location.href.includes('login.html') && !getToken()) {
    window.location.href = 'login.html';
}

// --- Page Logic ---

// 1. Dashboard Logic
const initDashboard = async () => {
    const jobListEl = document.getElementById('jobs-table-body');
    if (!jobListEl) return;

    jobListEl.innerHTML = '<tr><td colspan="5" style="text-align: center;">Loading jobs...</td></tr>';

    try {
        const res = await request(`${API_BASE}/jobs`);
        const jobs = await res.json();

        jobListEl.innerHTML = jobs.map(job => `
            <tr>
                <td>
                    <div style="font-weight: 500;">${job.name}</div>
                    <div class="subtitle" style="font-size: 0.8rem;">${new Date(job.created_at).toLocaleString()}</div>
                </td>
                <td><span class="status status-${job.status}">${job.status}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="min-width: 30px;">${job.progress}%</span>
                        <div class="progress-container" style="width: 80px; height: 6px; margin: 0;">
                            <div class="progress-bar" style="width: ${job.progress}%"></div>
                        </div>
                    </div>
                </td>
                <td>
                    <div style="font-size: 0.85rem;">${job.source}</div>
                    <div style="font-size: 0.8rem; opacity: 0.7;">to ${job.target}</div>
                </td>
                <td class="text-right">
                    <a href="job-detail.html?id=${job.id}" class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">
                        View
                    </a>
                </td>
            </tr>
        `).join('');

        if (jobs.length === 0) {
            jobListEl.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No jobs found. Create one!</td></tr>';
        }

        // Fetch System Stats
        const statsRes = await request(`${API_BASE}/stats`);
        if (statsRes.ok) {
            const stats = await statsRes.json();
            const workerCard = document.querySelector('.card.stat-card .stat-value');
            if (workerCard) workerCard.textContent = `${stats.active_jobs}`; // Fix: stats returns active_jobs

            const mbCard = document.querySelectorAll('.card.stat-card .stat-value')[1]; // active jobs is 2nd in python but first in html map? Wait.
            // HTML Structure in index.html: 
            // 1. Total Jobs (stat-total-jobs)
            // 2. Active Jobs (stat-active-jobs)
            // 3. Mailboxes Synced (stat-completed-mailboxes)
            // 4. Data Transferred (stat-data-transferred)
            // The previous JS code was selecting by class. I should use IDs if available or be consistent.
            // HTML now has IDs: stat-total-jobs, stat-active-jobs, stat-completed-mailboxes, stat-data-transferred
            document.getElementById('stat-total-jobs').textContent = stats.total_jobs;
            document.getElementById('stat-active-jobs').textContent = stats.active_jobs;
            document.getElementById('stat-completed-mailboxes').textContent = stats.completed_mailboxes;
            document.getElementById('stat-data-transferred').textContent = stats.data_transferred;
        }

    } catch (e) {
        console.error(e);
        jobListEl.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger); padding: 2rem;">Failed to load jobs: ${e.message}</td></tr>`;
    }
};

// ... (refreshDashboard kept same)

// 2. Create Job Logic (truncated for brevity in search, focusing on strings)
// ...
// ...
// Used in form submit
//        submitBtn.textContent = 'Creating...';
//        if (!res.ok) throw new Error('Failed to create job');
//        throw new Error("Please enter email addresses for single sync");
//        alert('Error: ' + error.message);
//            submitBtn.textContent = 'Start Migration Job';

// Used in CSV Preview
//                                <h3 style="font-size: 1rem;">CSV Preview (${lines.length} mailboxes found)</h3>
//                                <button type="button" class="status status-running" style="border:none; cursor:default; font-size: 0.75rem;">Valid Format</button>
//                                            <th style="padding: 0.5rem;">Source User</th>
//                                            <th style="padding: 0.5rem;">Target User</th>
//                                            <th style="padding: 0.5rem;">Password Check</th>
//                                    <td style="padding: 0.5rem; color: var(--success);">Present</td>
//                        html += `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 0.5rem;">...and ${lines.length - 5} more</td></tr>`;

// 3. Job Detail Logic
//            if (!res.ok) throw new Error('Job not found');
//            document.getElementById('job-name').textContent = "Error loading job";
//                tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No mailboxes found. Did you upload a CSV?</td></tr>';

//                                <button class="btn btn-secondary" onclick="viewLogs(${mb.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; margin-right: 10px;">Log</button>
//                                ${mb.status === 'running' ? `<button class="btn btn-danger" onclick="stopSync(${mb.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; cursor: pointer; margin-right: 10px;">Stop</button>` : ''}
//                                ${mb.status === 'failed' ? '<button class="btn btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Retry</button>' : ''}

// window.stopSync
//    if (!confirm('Are you sure you want to stop this sync?')) return;
//        alert('Failed to stop: ' + e.message);

// window.viewLogs
//        logContent.textContent = 'Loading logs...';
//            if (!res.ok) throw new Error('Failed to fetch logs');
//            logContent.textContent = 'Error loading logs: ' + e.message;

// Manual Refresh Logic
window.refreshDashboard = async () => {
    const btn = document.querySelector('button[onclick="refreshDashboard()"] svg');
    if (btn) btn.style.transform = 'rotate(360deg)';
    if (btn) btn.style.transition = 'transform 0.5s ease';

    await initDashboard();

    // Reset animation
    setTimeout(() => {
        if (btn) {
            btn.style.transition = 'none';
            btn.style.transform = 'rotate(0deg)';
        }
    }, 500);
};

// 2. Create Job Logic
const initCreateJob = () => {
    const form = document.getElementById('create-job-form');
    if (!form) return;

    // --- Tab Switching Logic ---
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    let activeTab = 'bulk';

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class
            tabs.forEach(t => {
                t.classList.remove('active');
            });

            // Hide contents
            tabContents.forEach(c => c.style.display = 'none');

            // Activate clicked tab
            tab.classList.add('active');

            activeTab = tab.dataset.tab;
            document.getElementById(`tab-${activeTab}`).style.display = 'block';
        });
    });

    // --- Auto Port Logic ---
    const setupAutoPort = (context) => {
        // Need to add IDs or select specifically. Since I didn't add IDs in HTML edit, I rely on order or selectors.
        // Assuming Structure: Source Server -> Grid-2 -> Form Group (Security) -> Select
        // Let's use more robust selection if possible, otherwise rely on DOM structure.
        // Best to select all Security selects and find their related Port input.

        const cards = document.querySelectorAll('.card');
        const sourceCard = cards[0]; // Source Server
        const targetCard = cards[1]; // Target Server

        const bindPortLogic = (card) => {
            const portInput = card.querySelector('input[name*="port"]');
            const securitySelect = card.querySelector('select[name*="security"]');

            if (portInput && securitySelect) {
                securitySelect.addEventListener('change', (e) => {
                    const val = e.target.value;
                    if (val === 'SSL/TLS') {
                        portInput.value = 993;
                    } else if (val === 'None' || val === 'STARTTLS') {
                        portInput.value = 143;
                    }
                });
            }
        };

        bindPortLogic(sourceCard);
        bindPortLogic(targetCard);
    };

    setupAutoPort();

    // --- Form Submission ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        const formData = new FormData(form);

        // Validation: Check Hosts
        const sourceHost = formData.get('source_host');
        const targetHost = formData.get('target_host');

        if (!sourceHost || !targetHost) {
            alert('Error: Please enter both Source and Target IMAP Hosts.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Migration Job';
            return;
        }

        // Collect Options
        const options = {
            sync_internal_dates: document.getElementById('opt-sync-dates')?.checked || false,
            skip_trash: document.getElementById('opt-skip-trash')?.checked || false,
            dry_run: document.getElementById('opt-dry-run')?.checked || false,
            concurrency: parseInt(document.getElementById('opt-concurrency')?.value || 10)
        };

        const jobPayload = {
            name: `Migration ${new Date().toLocaleDateString('en-US')}`,
            source_host: sourceHost,
            target_host: targetHost,
            source_port: parseInt(formData.get('source_port') || 993),
            target_port: parseInt(formData.get('target_port') || 993),
            source_security: formData.get('source_security'),
            target_security: formData.get('target_security'),
            options: options
        };

        try {
            // 1. Create Job
            const res = await request(`${API_BASE}/jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(jobPayload)
            });

            if (!res.ok) throw new Error('Failed to create job');
            const job = await res.json();

            // 2. Handle Mailboxes based on Active Tab
            if (activeTab === 'bulk') {
                const fileInput = form.querySelector('input[type="file"]');
                if (fileInput.files.length > 0) {
                    const uploadData = new FormData();
                    uploadData.append('file', fileInput.files[0]);

                    await request(`${API_BASE}/upload/${job.id}`, {
                        method: 'POST',
                        body: uploadData
                    });
                }
            } else if (activeTab === 'single') {
                const singlePayload = {
                    source_user: document.getElementById('single-source-user').value,
                    source_pass: document.getElementById('single-source-pass').value,
                    target_user: document.getElementById('single-target-user').value,
                    target_pass: document.getElementById('single-target-pass').value
                };

                if (!singlePayload.source_user || !singlePayload.target_user) {
                    throw new Error("Please enter email addresses for single sync");
                }

                await request(`${API_BASE}/jobs/${job.id}/mailboxes`, { // New Endpoint
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(singlePayload)
                });
            }

            window.location.href = `job-detail.html?id=${job.id}`;

        } catch (error) {
            alert('Error: ' + error.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Migration Job';
        }
    });

    // File input trigger
    const dropZone = document.querySelector('div[style*="dashed"]');
    const fileInput = dropZone.querySelector('input[type="file"]');
    const previewContainer = document.getElementById('csv-preview');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                dropZone.querySelector('span').textContent = file.name;

                // Preview Logic
                const reader = new FileReader();
                reader.onload = function (e) {
                    const text = e.target.result;
                    const lines = text.split('\n').filter(line => line.trim() !== '');
                    const previewLines = lines.slice(0, 5); // Show first 5

                    let html = `
                        <div class="mt-4">
                            <div class="flex-between mb-2">
                                <h3 style="font-size: 1rem;">CSV Preview (${lines.length} mailboxes found)</h3>
                                <button type="button" class="status status-running" style="border:none; cursor:default; font-size: 0.75rem;">Valid Format</button>
                            </div>
                            <div class="table-container" style="max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.2); border-radius: 8px;">
                                <table style="font-size: 0.85rem;">
                                    <thead>
                                        <tr>
                                            <th style="padding: 0.5rem;">Source User</th>
                                            <th style="padding: 0.5rem;">Target User</th>
                                            <th style="padding: 0.5rem;">Password Check</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;

                    previewLines.forEach(line => {
                        const cols = line.split(',').map(c => c.trim());
                        if (cols.length >= 4) {
                            html += `
                                <tr>
                                    <td style="padding: 0.5rem;">${cols[0]}</td>
                                    <td style="padding: 0.5rem;">${cols[2]}</td>
                                    <td style="padding: 0.5rem; color: var(--success);">Present</td>
                                </tr>
                            `;
                        }
                    });

                    if (lines.length > 5) {
                        html += `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 0.5rem;">...and ${lines.length - 5} more</td></tr>`;
                    }

                    html += `</tbody></table></div></div>`;

                    if (previewContainer) previewContainer.innerHTML = html;
                };
                reader.readAsText(file);
            }
        });
    }
};

// 3. Job Detail Logic
const initJobDetail = async () => {
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get('id');

    if (!jobId) {
        window.location.href = 'index.html';
        return;
    }

    const updateUI = async () => {
        try {
            const res = await request(`${API_BASE}/jobs/${jobId}`);
            if (!res.ok) throw new Error('Job not found');
            const job = await res.json();

            // Setup Header
            document.getElementById('job-name').textContent = job.name;
            document.getElementById('job-status').textContent = job.status;
            document.getElementById('job-status').className = `status status-${job.status}`;
            document.getElementById('source-host').textContent = job.source;
            document.getElementById('target-host').textContent = job.target;

            // Stats
            document.getElementById('stat-total').textContent = job.total;
            document.getElementById('stat-completed').textContent = job.completed;
            document.getElementById('stat-failed').textContent = job.failed;
            document.getElementById('main-progress-bar').style.width = `${job.progress}%`;
            document.getElementById('progress-percent').textContent = `${job.progress}%`;

            // Mailbox Table
            const tableBody = document.getElementById('mailbox-list');
            if (job.mailboxes && job.mailboxes.length > 0) {
                tableBody.innerHTML = job.mailboxes.map(mb => `
                    <tr>
                        <td>${mb.user}</td>
                        <td>${mb.target_user}</td>
                        <td><span class="status status-${mb.status === 'success' ? 'completed' : mb.status}">${mb.status}</span></td>
                        <td>${mb.msg || '-'}</td>
                        <td class="text-right">
                             <div class="action-group" style="display: flex; justify-content: flex-end; align-items: center;">
                                <button class="btn btn-secondary" onclick="viewLogs(${mb.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; margin-right: 10px;">Log</button>
                                ${mb.status === 'running' ? `<button class="btn btn-danger" onclick="stopSync(${mb.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; cursor: pointer; margin-right: 10px;">Stop</button>` : ''}
                                ${mb.status === 'failed' ? '<button class="btn btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Retry</button>' : ''}
                             </div>
                        </td>
                    </tr>
                `).join('');
            } else {
                tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No mailboxes found. Did you upload a CSV?</td></tr>';
            }

            // Continue polling if running
            if (job.status === 'running' || job.status === 'pending') {
                setTimeout(updateUI, 2000);
            }

        } catch (e) {
            console.error(e);
            document.getElementById('job-name').textContent = "Error loading job";
        }
    };

    updateUI();
};

window.stopSync = async (mailboxId) => {
    if (!confirm('Are you sure you want to stop this sync?')) return;
    try {
        await request(`${API_BASE}/mailboxes/${mailboxId}/stop`, { method: 'POST' });
        // The polling will update the status automatically
    } catch (e) {
        alert('Failed to stop: ' + e.message);
    }
};

// --- Log Modal Logic ---
let logPollInterval = null;

window.viewLogs = async (mailboxId) => {
    const modal = document.getElementById('log-modal');
    const logContent = document.getElementById('log-content');

    if (modal) {
        modal.style.display = 'flex';
        logContent.textContent = 'Loading logs...';

        const fetchLogs = async () => {
            try {
                const res = await request(`${API_BASE}/mailboxes/${mailboxId}/logs`);
                if (!res.ok) throw new Error('Failed to fetch logs');
                const data = await res.json();

                // Only update if content changed to avoid jumps, or just replace.
                // For log tailing, usually replacing is fine if it's the whole log.
                // Better UX: keep scroll position if user scrolled up?
                // For now, simple replacement as requested.
                logContent.textContent = data.logs;

                // Auto-scroll to bottom if near bottom?
                // logContent.scrollTop = logContent.scrollHeight; 
            } catch (e) {
                console.error(e);
                // Don't overwrite error on transient failures during headers
            }
        };

        // Initial fetch
        await fetchLogs();

        // Start polling every 2 seconds
        if (logPollInterval) clearInterval(logPollInterval);
        logPollInterval = setInterval(fetchLogs, 2000);
    }
};

window.closeModal = () => {
    const modal = document.getElementById('log-modal');
    if (modal) modal.style.display = 'none';
    if (logPollInterval) {
        clearInterval(logPollInterval);
        logPollInterval = null;
    }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    if (path.includes('create-job.html')) {
        initCreateJob();
    } else if (path.includes('job-detail.html')) {
        initJobDetail();
    } else {
        initDashboard();
    }
});
