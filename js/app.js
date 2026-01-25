/**
 * app.js
 * Core logic for IMAP Sync Web UI
 * Now connected to real FastAPI Backend
 */

const API_BASE = '/api';

// --- Simple Request Helper (No Auth) ---
const request = async (url, options = {}) => {
    const res = await fetch(url, options);
    return res;
};

// --- Page Logic ---

// 1. Dashboard Logic
const initDashboard = async () => {
    const jobListEl = document.getElementById('jobs-table-body');
    if (!jobListEl) return;

    jobListEl.innerHTML = '<tr><td colspan="5" style="text-align: center;">Loading jobs...</td></tr>';

    try {
        const res = await request(`${API_BASE}/jobs`);
        const jobs = await res.json();

        const getStatusClasses = (status) => {
            const statusMap = {
                'running': 'bg-blue-100 text-blue-700 border border-blue-200',
                'completed': 'bg-emerald-100 text-emerald-700 border border-emerald-200',
                'success': 'bg-emerald-100 text-emerald-700 border border-emerald-200',
                'failed': 'bg-red-100 text-red-700 border border-red-200',
                'pending': 'bg-amber-100 text-amber-700 border border-amber-200'
            };
            return statusMap[status] || 'bg-gray-100 text-gray-700 border border-gray-200';
        };

        jobListEl.innerHTML = jobs.map(job => `
            <tr class="hover:bg-blue-50/50 transition-colors">
                <td class="px-6 py-4">
                    <div class="font-medium text-gray-900">${job.name}</div>
                    <div class="text-sm text-gray-500">${new Date(job.created_at).toLocaleString()}</div>
                </td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusClasses(job.status)}">
                        ${job.status}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-medium text-gray-700 min-w-[35px]">${job.progress}%</span>
                        <div class="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div class="h-full progress-gradient rounded-full transition-all duration-300" style="width: ${job.progress}%"></div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900">${job.source}</div>
                    <div class="text-sm text-gray-500">→ ${job.target}</div>
                </td>
                <td class="px-6 py-4 text-right">
                    <a href="job-detail.html?id=${job.id}" class="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors">
                        Xem
                    </a>
                </td>
            </tr>
        `).join('');

        if (jobs.length === 0) {
            jobListEl.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-gray-500">Chưa có job nào. Tạo mới ngay!</td></tr>';
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
        jobListEl.innerHTML = `<tr><td colspan="5" class="px-6 py-12 text-center text-red-500">Lỗi tải jobs: ${e.message}</td></tr>`;
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

window.deleteAllJobs = async () => {
    window.showConfirm("Are you sure you want to delete ALL jobs and logs? This cannot be undone.", async () => {
        try {
            const res = await request(`${API_BASE}/jobs`, { method: 'DELETE' });
            if (!res.ok) throw new Error("Failed to delete jobs");

            window.showToast("All history deleted", "success");

            // Refresh dashboard
            await initDashboard();

        } catch (e) {
            window.showToast("Error: " + e.message, "error");
        }
    });
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
        const sourceCard = document.getElementById('source-server-card');
        const targetCard = document.getElementById('target-server-card');

        const bindPortLogic = (card) => {
            if (!card) return;
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

                    const uploadRes = await request(`${API_BASE}/upload/${job.id}`, {
                        method: 'POST',
                        body: uploadData
                    });

                    if (!uploadRes.ok) {
                        const err = await uploadRes.json().catch(() => ({}));
                        throw new Error(err.detail || 'CSV Upload failed');
                    }
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
    const dropZone = document.getElementById('drop-zone');
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

// --- UI Helpers ---
window.showToast = (message, type = 'info') => {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const typeStyles = {
        'success': 'border-l-emerald-500 bg-emerald-50',
        'error': 'border-l-red-500 bg-red-50',
        'info': 'border-l-blue-500 bg-blue-50',
        'warning': 'border-l-amber-500 bg-amber-50'
    };

    const toast = document.createElement('div');
    toast.className = `min-w-[300px] p-4 rounded-xl shadow-lg border border-gray-200 border-l-4 ${typeStyles[type] || typeStyles.info} animate-slide-in-right cursor-pointer flex items-center gap-3`;
    toast.innerHTML = `
        <span class="text-gray-800 text-sm font-medium">${message}</span>
    `;

    // Click to dismiss
    toast.onclick = () => {
        toast.classList.remove('animate-slide-in-right');
        toast.classList.add('animate-fade-out-right');
        setTimeout(() => toast.remove(), 300);
    };

    container.appendChild(toast);

    // Auto dismiss
    setTimeout(() => {
        if (toast.isConnected) {
            toast.classList.remove('animate-slide-in-right');
            toast.classList.add('animate-fade-out-right');
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
};

window.showConfirm = (message, callback) => {
    const modal = document.getElementById('confirm-modal');
    const msgEl = document.getElementById('confirm-message');
    if (!modal) {
        if (confirm(message)) callback();
        return;
    }

    msgEl.textContent = message;
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    // Cleanup old listeners
    window.closeConfirm = (result) => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        if (result) callback();
    };
};

// 3. Job Detail Logic
let isJobPolling = false;
let forcePollRestart = false;

const initJobDetail = async () => {
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get('id');

    if (!jobId) {
        window.location.href = 'index.html';
        return;
    }

    // Prevent multiple polling loops
    if (isJobPolling && !forcePollRestart) return;
    isJobPolling = true;
    forcePollRestart = false;

    const updateUI = async () => {
        try {
            const res = await request(`${API_BASE}/jobs/${jobId}`);
            if (!res.ok) throw new Error('Job not found');
            const job = await res.json();

            // Status badge classes helper
            const getStatusBadge = (status) => {
                const statusMap = {
                    'running': 'bg-blue-100 text-blue-700',
                    'completed': 'bg-emerald-100 text-emerald-700',
                    'success': 'bg-emerald-100 text-emerald-700',
                    'failed': 'bg-red-100 text-red-700',
                    'pending': 'bg-amber-100 text-amber-700'
                };
                return statusMap[status] || 'bg-gray-100 text-gray-700';
            };

            // Setup Header
            document.getElementById('job-name').textContent = job.name;
            const statusEl = document.getElementById('job-status');
            statusEl.textContent = job.status;
            statusEl.className = `inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold ${getStatusBadge(job.status)}`;
            document.getElementById('source-host').textContent = job.source;
            document.getElementById('target-host').textContent = job.target;

            // Stats
            document.getElementById('stat-total').textContent = job.total;
            document.getElementById('stat-completed').textContent = job.completed;
            document.getElementById('stat-failed').textContent = job.failed;
            document.getElementById('stat-data').textContent = job.data_transferred;
            document.getElementById('main-progress-bar').style.width = `${job.progress}%`;
            document.getElementById('progress-percent').textContent = `${job.progress}%`;

            // Mailbox Table
            const tableBody = document.getElementById('mailbox-list');
            if (job.mailboxes && job.mailboxes.length > 0) {
                tableBody.innerHTML = job.mailboxes.map(mb => `
                    <tr class="hover:bg-blue-50/50 transition-colors">
                        <td class="px-6 py-4 font-mono text-sm text-gray-900">${mb.user}</td>
                        <td class="px-6 py-4 font-mono text-sm text-gray-900">${mb.target_user}</td>
                        <td class="px-6 py-4">
                            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusBadge(mb.status === 'success' ? 'completed' : mb.status)}">
                                ${mb.status}
                            </span>
                        </td>
                        <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">${mb.msg || '-'}</td>
                        <td class="px-6 py-4 text-right">
                            <div class="flex justify-end items-center gap-2">
                                <button onclick="viewLogs(${mb.id})" class="px-2.5 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">Log</button>
                                ${mb.status === 'running' ? `<button onclick="stopSync(${mb.id})" class="px-2.5 py-1.5 text-xs font-medium bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors">Stop</button>` : ''}
                                ${mb.status === 'failed' ? `<button onclick="retrySync(${mb.id})" class="px-2.5 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Retry</button>` : ''}
                            </div>
                        </td>
                    </tr>
                `).join('');
            } else {
                tableBody.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-gray-500">Chưa có mailbox. Đã upload CSV chưa?</td></tr>';
            }

            // Continue polling if running OR if we forced a restart (e.g. from Retry)
            // But we only want to loop if the job is actually active.
            // If the job is 'completed' but we just retried a mailbox, the job status should update to 'running' on backend.
            // If backend is slow, we might miss it. So we rely on the loop.
            // Using a simple interval is safer than recursive timeout for control?
            // Let's keep recursive but check a global flag or the job status.

            if (job.status === 'running' || job.status === 'pending' || forcePollRestart) {
                // If forced restart, we consume the flag so we don't loop forever if it becomes completed again
                if (forcePollRestart) forcePollRestart = false;
                setTimeout(updateUI, 2000);
            } else {
                isJobPolling = false; // Stopped polling
            }

        } catch (e) {
            console.error(e);
            document.getElementById('job-name').textContent = "Error loading job";
            isJobPolling = false;
        }
    };

    updateUI();
};

window.stopSync = async (mailboxId) => {
    window.showConfirm('Are you sure you want to stop this sync?', async () => {
        try {
            await request(`${API_BASE}/mailboxes/${mailboxId}/stop`, { method: 'POST' });
            window.showToast('Stop signal sent', 'info');
        } catch (e) {
            window.showToast('Failed to stop: ' + e.message, 'error');
        }
    });
};

window.retrySync = async (mailboxId) => {
    window.showConfirm('Retry this mailbox sync?', async () => {
        try {
            const res = await request(`${API_BASE}/mailboxes/${mailboxId}/retry`, { method: 'POST' });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to retry');
            }
            window.showToast('Retry started successfully', 'success');

            // Force restart polling if it stopped
            if (!isJobPolling) {
                forcePollRestart = true;
                initJobDetail(); // Restart the loop
            } else {
                // If already running, it will pick up the change
                forcePollRestart = true; // Ensure it keeps going if it was about to stop
            }

        } catch (e) {
            window.showToast('Failed to retry: ' + e.message, 'error');
        }
    });
};

// --- Log Modal Logic ---
let logPollInterval = null;

window.viewLogs = async (mailboxId) => {
    const modal = document.getElementById('log-modal');
    const logContent = document.getElementById('log-content');

    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        logContent.textContent = 'Đang tải logs...';

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
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
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
