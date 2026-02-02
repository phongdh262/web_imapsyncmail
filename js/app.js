/**
 * app.js
 * Core logic for IMAP Sync Web UI
 * Now connected to real FastAPI Backend
 * Version 4.0 - Enhanced with validation, drag & drop, loading states
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
    const emptyState = document.getElementById('empty-state');
    const jobsTable = document.getElementById('jobs-table');

    if (!jobListEl) return;

    jobListEl.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-gray-500"><div class="flex items-center justify-center gap-2"><svg class="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Đang tải...</div></td></tr>';

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

        if (jobs.length === 0) {
            // Show empty state
            jobsTable?.classList.add('hidden');
            emptyState?.classList.remove('hidden');
        } else {
            jobsTable?.classList.remove('hidden');
            emptyState?.classList.add('hidden');

            jobListEl.innerHTML = jobs.map(job => `
                <tr class="hover:bg-blue-50/50 transition-colors">
                    <td class="px-6 py-4">
                        <div class="font-medium text-gray-900">${job.name}</div>
                        <div class="text-sm text-gray-500">${new Date(job.created_at).toLocaleString()}</div>
                    </td>
                    <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusClasses(job.status)}">
                            ${job.status === 'running' ? '<span class="w-2 h-2 bg-blue-500 rounded-full mr-1.5 animate-pulse"></span>' : ''}
                            ${job.status}
                        </span>
                    </td>
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-2">
                            <span class="text-sm font-medium text-gray-700 min-w-[35px]">${job.progress}%</span>
                            <div class="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div class="h-full progress-gradient rounded-full transition-all duration-500" style="width: ${job.progress}%"></div>
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
        }

        // Fetch System Stats
        const statsRes = await request(`${API_BASE}/stats`);
        if (statsRes.ok) {
            const stats = await statsRes.json();
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

// Manual Refresh Logic
window.refreshDashboard = async () => {
    const btn = document.getElementById('refresh-btn');
    const icon = btn?.querySelector('.refresh-icon');

    if (btn) btn.disabled = true;
    if (icon) {
        icon.style.transition = 'transform 0.5s ease';
        icon.style.transform = 'rotate(360deg)';
    }

    await initDashboard();

    setTimeout(() => {
        if (btn) btn.disabled = false;
        if (icon) {
            icon.style.transition = 'none';
            icon.style.transform = 'rotate(0deg)';
        }
    }, 500);
};

window.deleteAllJobs = async () => {
    window.showConfirm("Bạn có chắc muốn xóa TẤT CẢ jobs và logs? Hành động này không thể hoàn tác.", async () => {
        try {
            const res = await request(`${API_BASE}/jobs`, { method: 'DELETE' });
            if (!res.ok) throw new Error("Failed to delete jobs");

            window.showToast("Đã xóa toàn bộ lịch sử", "success");

            // Refresh dashboard
            await initDashboard();

        } catch (e) {
            window.showToast("Lỗi: " + e.message, "error");
        }
    });
};

// 2. Create Job Logic
const initCreateJob = () => {
    const form = document.getElementById('create-job-form');
    if (!form) return;

    // --- Tab Switching Logic with Animation ---
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    let activeTab = 'bulk';

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class
            tabs.forEach(t => {
                t.classList.remove('active');
            });

            // Add fade-out then hide
            tabContents.forEach(c => {
                c.style.opacity = '0';
                c.style.transform = 'translateY(10px)';
                setTimeout(() => {
                    c.style.display = 'none';
                }, 150);
            });

            // Activate clicked tab
            tab.classList.add('active');

            activeTab = tab.dataset.tab;
            const activeContent = document.getElementById(`tab-${activeTab}`);

            setTimeout(() => {
                activeContent.style.display = 'block';
                setTimeout(() => {
                    activeContent.style.opacity = '1';
                    activeContent.style.transform = 'translateY(0)';
                }, 10);
            }, 150);
        });
    });

    // Initialize tab content transitions
    tabContents.forEach(c => {
        c.style.transition = 'opacity 0.15s ease, transform 0.15s ease';
        if (!c.classList.contains('hidden')) {
            c.style.opacity = '1';
            c.style.transform = 'translateY(0)';
        }
    });

    // --- Auto Port Logic ---
    const setupAutoPort = () => {
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

    // --- Form Validation ---
    const validateField = (input) => {
        const errorEl = input.parentElement.querySelector('.error-message');

        if (input.required && !input.value.trim()) {
            input.classList.add('border-red-500', 'focus:ring-red-500');
            input.classList.remove('border-gray-200', 'focus:ring-blue-500');
            errorEl?.classList.remove('hidden');
            return false;
        } else {
            input.classList.remove('border-red-500', 'focus:ring-red-500');
            input.classList.add('border-gray-200', 'focus:ring-blue-500');
            errorEl?.classList.add('hidden');
            return true;
        }
    };

    // Add blur validation
    form.querySelectorAll('input[required]').forEach(input => {
        input.addEventListener('blur', () => validateField(input));
        input.addEventListener('input', () => {
            if (input.classList.contains('border-red-500')) {
                validateField(input);
            }
        });
    });

    // --- Form Submission ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById('submit-btn');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnIcon = submitBtn.querySelector('.btn-icon');

        // Validate required fields
        const sourceHost = form.querySelector('[name="source_host"]');
        const targetHost = form.querySelector('[name="target_host"]');

        let isValid = true;
        isValid = validateField(sourceHost) && isValid;
        isValid = validateField(targetHost) && isValid;

        if (!isValid) {
            window.showToast('Vui lòng điền đầy đủ thông tin bắt buộc', 'error');
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        btnText.textContent = 'Đang tạo...';
        btnIcon.classList.add('animate-spin-slow');

        const formData = new FormData(form);

        // Collect Options
        const options = {
            sync_internal_dates: document.getElementById('opt-sync-dates')?.checked || false,
            skip_trash: document.getElementById('opt-skip-trash')?.checked || false,
            dry_run: document.getElementById('opt-dry-run')?.checked || false,
            concurrency: parseInt(document.getElementById('opt-concurrency')?.value || 10)
        };

        // Better job name with time
        const now = new Date();
        const jobName = `Migration ${now.toLocaleDateString('vi-VN')} ${now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;

        const jobPayload = {
            name: jobName,
            source_host: sourceHost.value,
            target_host: targetHost.value,
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
                const fileInput = document.getElementById('csv-file-input');
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
                } else {
                    window.showToast('Vui lòng chọn file CSV', 'warning');
                    submitBtn.disabled = false;
                    btnText.textContent = 'Start Migration';
                    btnIcon.classList.remove('animate-spin-slow');
                    return;
                }
            } else if (activeTab === 'single') {
                const singlePayload = {
                    source_user: document.getElementById('single-source-user').value,
                    source_pass: document.getElementById('single-source-pass').value,
                    target_user: document.getElementById('single-target-user').value,
                    target_pass: document.getElementById('single-target-pass').value
                };

                if (!singlePayload.source_user || !singlePayload.target_user) {
                    throw new Error("Vui lòng nhập đầy đủ email source và target");
                }

                if (!singlePayload.source_pass || !singlePayload.target_pass) {
                    throw new Error("Vui lòng nhập đầy đủ password");
                }

                await request(`${API_BASE}/jobs/${job.id}/mailboxes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(singlePayload)
                });
            }

            window.location.href = `job-detail.html?id=${job.id}`;

        } catch (error) {
            window.showToast('Lỗi: ' + error.message, 'error');
            submitBtn.disabled = false;
            btnText.textContent = 'Start Migration';
            btnIcon.classList.remove('animate-spin-slow');
        }
    });

    // --- Drag & Drop with Visual Feedback ---
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('csv-file-input');
    const previewContainer = document.getElementById('csv-preview');
    const dropzoneIcon = document.getElementById('dropzone-icon');
    const dropzoneText = document.getElementById('dropzone-text');

    if (dropZone && fileInput) {
        // Click to open file dialog
        dropZone.addEventListener('click', () => fileInput.click());

        // Drag events
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dropzone-active', 'border-blue-500', 'bg-blue-50');
                dropzoneIcon?.classList.add('scale-110');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dropzone-active', 'border-blue-500', 'bg-blue-50');
                dropzoneIcon?.classList.remove('scale-110');
            });
        });

        // Handle drop
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.name.endsWith('.csv')) {
                    fileInput.files = files;
                    handleFileSelect(file);
                } else {
                    window.showToast('Vui lòng chọn file CSV', 'error');
                }
            }
        });

        // Handle file input change
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleFileSelect(fileInput.files[0]);
            }
        });

        function handleFileSelect(file) {
            // Update dropzone appearance
            dropzoneText.innerHTML = `<span class="text-emerald-600 font-medium">${file.name}</span> (${(file.size / 1024).toFixed(1)} KB)`;
            dropzoneIcon.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
            `;
            dropzoneIcon.classList.remove('bg-gray-100');
            dropzoneIcon.classList.add('bg-emerald-100');

            // Preview Logic
            const reader = new FileReader();
            reader.onload = function (e) {
                const text = e.target.result;
                const lines = text.split('\n').filter(line => line.trim() !== '');
                const previewLines = lines.slice(0, 5);

                let html = `
                    <div class="mt-4 bg-gray-50 rounded-xl p-4 border border-gray-200">
                        <div class="flex items-center justify-between mb-3">
                            <h3 class="font-medium text-gray-900">CSV Preview</h3>
                            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
                                ${lines.length} mailboxes
                            </span>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm">
                                <thead>
                                    <tr class="border-b border-gray-200">
                                        <th class="text-left py-2 px-3 font-medium text-gray-500">Source User</th>
                                        <th class="text-left py-2 px-3 font-medium text-gray-500">Target User</th>
                                        <th class="text-left py-2 px-3 font-medium text-gray-500">Password</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;

                previewLines.forEach(line => {
                    const cols = line.split(',').map(c => c.trim());
                    if (cols.length >= 4) {
                        html += `
                            <tr class="border-b border-gray-100">
                                <td class="py-2 px-3 font-mono text-gray-900">${cols[0]}</td>
                                <td class="py-2 px-3 font-mono text-gray-900">${cols[2]}</td>
                                <td class="py-2 px-3 text-emerald-600">✓ Present</td>
                            </tr>
                        `;
                    }
                });

                if (lines.length > 5) {
                    html += `<tr><td colspan="3" class="text-center py-2 text-gray-400 text-sm">...và ${lines.length - 5} mailbox khác</td></tr>`;
                }

                html += `</tbody></table></div></div>`;

                if (previewContainer) previewContainer.innerHTML = html;
            };
            reader.readAsText(file);
        }
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

    const icons = {
        'success': '<svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
        'error': '<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
        'info': '<svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        'warning': '<svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>'
    };

    const toast = document.createElement('div');
    toast.className = `min-w-[300px] p-4 rounded-xl shadow-lg border border-gray-200 border-l-4 ${typeStyles[type] || typeStyles.info} animate-slide-in-right cursor-pointer flex items-center gap-3`;
    toast.innerHTML = `
        ${icons[type] || icons.info}
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
let currentMailboxes = [];

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

    // Setup search functionality
    const searchInput = document.getElementById('mailbox-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterMailboxes(e.target.value);
        });
    }

    const updateUI = async () => {
        try {
            const res = await request(`${API_BASE}/jobs/${jobId}`);
            if (!res.ok) throw new Error('Job not found');
            const job = await res.json();

            // Store mailboxes for filtering
            currentMailboxes = job.mailboxes || [];

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

            // Show/hide Cancel All button
            const cancelAllBtn = document.getElementById('cancel-all-btn');
            if (cancelAllBtn) {
                if (job.status === 'running') {
                    cancelAllBtn.classList.remove('hidden');
                    cancelAllBtn.classList.add('inline-flex');
                } else {
                    cancelAllBtn.classList.add('hidden');
                    cancelAllBtn.classList.remove('inline-flex');
                }
            }

            // Stats
            document.getElementById('stat-total').textContent = job.total;
            document.getElementById('stat-completed').textContent = job.completed;
            document.getElementById('stat-failed').textContent = job.failed;

            // Format data transferred
            const dataEl = document.getElementById('stat-data');
            if (dataEl) {
                dataEl.textContent = job.data_transferred || '0 B';
            }

            document.getElementById('main-progress-bar').style.width = `${job.progress}%`;
            document.getElementById('progress-percent').textContent = `${job.progress}%`;

            // Render mailboxes
            renderMailboxes(currentMailboxes, getStatusBadge);

            if (job.status === 'running' || job.status === 'pending' || forcePollRestart) {
                if (forcePollRestart) forcePollRestart = false;
                setTimeout(updateUI, 2000);
            } else {
                isJobPolling = false;
            }

        } catch (e) {
            console.error(e);
            document.getElementById('job-name').textContent = "Error loading job";
            isJobPolling = false;
        }
    };

    updateUI();
};

function renderMailboxes(mailboxes, getStatusBadge) {
    const tableBody = document.getElementById('mailbox-list');
    const emptyState = document.getElementById('mailbox-empty-state');

    if (mailboxes && mailboxes.length > 0) {
        emptyState?.classList.add('hidden');
        tableBody.innerHTML = mailboxes.map(mb => `
            <tr class="hover:bg-blue-50/50 transition-colors" data-user="${mb.user?.toLowerCase()}" data-target="${mb.target_user?.toLowerCase()}">
                <td class="px-6 py-4 font-mono text-sm text-gray-900">${mb.user}</td>
                <td class="px-6 py-4 font-mono text-sm text-gray-900">${mb.target_user}</td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusBadge(mb.status === 'success' ? 'completed' : mb.status)}">
                        ${mb.status === 'running' ? '<span class="w-2 h-2 bg-blue-500 rounded-full mr-1.5 animate-pulse"></span>' : ''}
                        ${mb.status}
                    </span>
                </td>
                <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title="${mb.msg || ''}">${mb.msg || '-'}</td>
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
        emptyState?.classList.remove('hidden');
        tableBody.innerHTML = '';
    }
}

function filterMailboxes(query) {
    const rows = document.querySelectorAll('#mailbox-list tr');
    const lowerQuery = query.toLowerCase();

    rows.forEach(row => {
        const user = row.dataset.user || '';
        const target = row.dataset.target || '';

        if (user.includes(lowerQuery) || target.includes(lowerQuery)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

window.cancelAllMailboxes = async () => {
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get('id');

    window.showConfirm('Bạn có chắc muốn dừng TẤT CẢ mailbox đang chạy?', async () => {
        try {
            const res = await request(`${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to cancel');
            }
            window.showToast('Đã gửi lệnh dừng tất cả', 'info');
        } catch (e) {
            window.showToast('Lỗi: ' + e.message, 'error');
        }
    });
};

window.stopSync = async (mailboxId) => {
    window.showConfirm('Bạn có chắc muốn dừng sync này?', async () => {
        try {
            await request(`${API_BASE}/mailboxes/${mailboxId}/stop`, { method: 'POST' });
            window.showToast('Đã gửi lệnh dừng', 'info');
        } catch (e) {
            window.showToast('Lỗi: ' + e.message, 'error');
        }
    });
};

window.retrySync = async (mailboxId) => {
    window.showConfirm('Thử lại sync mailbox này?', async () => {
        try {
            const res = await request(`${API_BASE}/mailboxes/${mailboxId}/retry`, { method: 'POST' });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to retry');
            }
            window.showToast('Đang retry...', 'success');

            // Force restart polling if it stopped
            if (!isJobPolling) {
                forcePollRestart = true;
                initJobDetail();
            } else {
                forcePollRestart = true;
            }

        } catch (e) {
            window.showToast('Lỗi: ' + e.message, 'error');
        }
    });
};

// --- Log Modal Logic ---
let logPollInterval = null;

window.viewLogs = async (mailboxId) => {
    const modal = document.getElementById('log-modal');
    const logContent = document.getElementById('log-content');
    const autoScrollCheckbox = document.getElementById('log-autoscroll');

    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        logContent.textContent = 'Đang tải logs...';

        const fetchLogs = async () => {
            try {
                const res = await request(`${API_BASE}/mailboxes/${mailboxId}/logs`);
                if (!res.ok) throw new Error('Failed to fetch logs');
                const data = await res.json();

                const previousScrollTop = logContent.scrollTop;
                const wasAtBottom = logContent.scrollHeight - logContent.clientHeight <= previousScrollTop + 50;

                logContent.textContent = data.logs;

                // Auto-scroll to bottom if enabled and was at bottom
                if (autoScrollCheckbox?.checked && wasAtBottom) {
                    logContent.scrollTop = logContent.scrollHeight;
                }
            } catch (e) {
                console.error(e);
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
