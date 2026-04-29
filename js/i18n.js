(function () {
    const STORAGE_KEY = 'app_language';
    const SUPPORTED_LANGUAGES = ['en', 'vi'];

    const translations = {
        en: {
            guide: {
                sidebar: {
                    title: 'Contents',
                    quickStart: 'Quick Start',
                    bulkMigration: 'Bulk Migration',
                    singleSync: 'Single Sync',
                    monitoring: 'Monitoring & Errors',
                    checkCredentials: 'Credential Checks',
                    gmailSetup: 'Gmail Setup',
                    office365Setup: 'Office 365 Setup',
                    security: 'Security',
                    faq: 'FAQ & Troubleshooting'
                },
                hero: {
                    kicker: 'Public Documentation',
                    title: 'Operational guidance for controlled IMAP migrations.',
                    subtitle: 'This guide prioritizes fast reading, easy sign-off, and practical troubleshooting for migration jobs that are already running in production.',
                    focusLabel: 'Focus',
                    focusValue: 'Execution checklists, IMAP setup, and common failure handling.',
                    audienceLabel: 'Audience',
                    audienceValue: 'Deployment admins, operations technicians, and clients who need visibility into results.'
                },
                signals: {
                    oneTitle: '1. Validate credentials first',
                    oneCopy: 'Confirm host, app password, and login capability before starting a bulk run.',
                    twoTitle: '2. Create a job with its own password',
                    twoCopy: 'Keep the admin console separate from the shareable progress viewer.',
                    threeTitle: '3. Monitor and sign off',
                    threeCopy: 'Use the job detail page to review logs, confirm status, and export the final report.'
                },
                quickStart: {
                    kicker: 'Quick Start',
                    title: '1. Quick Start',
                    note: 'The base rules that keep operators and viewers on the same flow without mixing admin access with the public viewer.',
                    body: `
                        <p class="mb-6">
                            IMAP Sync Pro moves email from one IMAP server to another. The interface now supports both
                            <strong>English and Vietnamese</strong>, while this document keeps the same operational flow in both languages.
                        </p>

                        <div class="guide-callout border-l-4 border-blue-500 rounded-r-xl">
                            <h4 class="text-blue-800 dark:text-blue-300 font-bold mb-2 flex items-center gap-2">
                                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Important
                            </h4>
                            <ul class="list-none space-y-2 text-blue-900 dark:text-blue-200 text-sm m-0 p-0">
                                <li class="flex items-start gap-2">
                                    <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0"></span>
                                    <span>Both source and target servers must support IMAP.</span>
                                </li>
                                <li class="flex items-start gap-2">
                                    <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0"></span>
                                    <span><strong>Job Password</strong> is required to protect each migration session.</span>
                                </li>
                            </ul>
                        </div>
                    `
                },
                bulk: {
                    kicker: 'Bulk Workflow',
                    title: '2. Bulk Migration',
                    note: 'Checklist for larger sync batches, with emphasis on host selection, CSV preparation, job password, and safe execution options.',
                    body: `
                        <p>This mode is designed for migrations involving dozens or hundreds of mailboxes at once.</p>

                        <ol class="space-y-6 list-decimal pl-5">
                            <li class="pl-2">
                                <strong>Open the flow:</strong> Click
                                <span class="inline-flex items-center px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-sm mx-1 shadow-sm font-medium">Create New Job</span>
                                from the dashboard.
                            </li>
                            <li class="pl-2">
                                <strong>Configure both servers:</strong>
                                <ul class="mt-2 space-y-2 list-disc pl-5 opacity-90">
                                    <li>Enter the source <code class="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-100 dark:border-blue-800/50">host</code> where the legacy mailboxes live.</li>
                                    <li>Enter the target <code class="bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border border-emerald-100 dark:border-emerald-800/50">host</code> where the migrated mailboxes should land.</li>
                                    <li>Typical ports are <code>993</code> for SSL/TLS or <code>143</code> for STARTTLS.</li>
                                </ul>
                            </li>
                            <li class="pl-2">
                                <strong>Prepare the CSV file:</strong>
                                <div class="bg-slate-900 rounded-xl mt-3 overflow-hidden shadow-sm">
                                    <div class="px-4 py-2 bg-slate-800 text-slate-400 text-xs font-mono uppercase tracking-wider border-b border-slate-700">CSV layout</div>
                                    <pre class="m-0 p-4 text-sm text-green-400 font-mono bg-transparent">source_user_1@example.com,source_pass_1,target_user_1@example.com,target_pass_1
source_user_2@example.com,source_pass_2,target_user_2@example.com,target_pass_2</pre>
                                </div>
                                <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">
                                    <em>If a password contains commas or special characters, wrap it in quotes or normalize the password before migration.</em>
                                </p>
                            </li>
                            <li class="pl-2">
                                <strong>Set a Job Password:</strong> Anyone opening the shareable viewer or downloading logs and reports will need this password.
                            </li>
                            <li class="pl-2">
                                <strong>Review Advanced Settings:</strong>
                                <ul class="list-disc pl-5 mt-2 space-y-1">
                                    <li><strong>Sync Internal Dates:</strong> preserve message dates.</li>
                                    <li><strong>Skip Trash:</strong> reduce unnecessary data transfer.</li>
                                    <li><strong>Dry Run:</strong> simulate the operation without copying live mail.</li>
                                </ul>
                            </li>
                            <li class="pl-2">
                                Upload the CSV and click <strong>Start Bulk Migration</strong>.
                            </li>
                        </ol>
                    `
                },
                single: {
                    kicker: 'Single Mailbox',
                    title: '3. Single Sync',
                    note: 'More appropriate for tests, mailbox recovery, or one-by-one migration tasks that need tighter manual control.',
                    body: `
                        <p>Use this mode when you only need to move <strong>one mailbox</strong>.</p>
                        <ol class="space-y-4 list-decimal pl-5">
                            <li class="pl-2">In the Create Job page, switch to the <strong>Single Sync</strong> tab.</li>
                            <li class="pl-2">Configure the source and target servers just like the bulk workflow.</li>
                            <li class="pl-2">Enter the source mailbox username and password directly in the form.</li>
                            <li class="pl-2">Enter the target mailbox username and password.</li>
                            <li class="pl-2">Set a <strong>Job Password</strong> for the protected viewer.</li>
                            <li class="pl-2">Click <strong>Start Single Migration</strong>.</li>
                        </ol>
                    `
                },
                monitoring: {
                    kicker: 'Monitoring',
                    title: '4. Monitoring & Reporting',
                    note: 'Track the dashboard, inspect live logs, and export the final report once every mailbox is complete.',
                    body: `
                        <p>The worker runs in the background. You can close the browser and return later without losing job progress.</p>

                        <div>
                            <h3 class="text-xl font-semibold mb-3">4.1 Dashboard</h3>
                            <ul class="list-disc pl-5 space-y-2">
                                <li>You can see every running job in the dashboard list.</li>
                                <li>The <strong>Progress</strong> column shows how many mailboxes are finished.</li>
                                <li>Click the job viewer link to open details. The page will request the <strong>Job Password</strong>.</li>
                            </ul>
                        </div>

                        <div>
                            <h3 class="text-xl font-semibold mb-3">4.2 Job Detail</h3>
                            <ul class="list-disc pl-5 space-y-2">
                                <li>The progress bar updates without a full page refresh.</li>
                                <li>Mailbox rows show statuses such as <code>Running</code>, <code>Completed</code>, and <code>Failed</code>.</li>
                                <li>Use <strong>Log</strong> to inspect individual mailbox activity and underlying <code>imapsync</code> output.</li>
                                <li><strong>Stop All</strong> is only visible to authenticated admins and sends cancel commands to active tasks.</li>
                            </ul>
                        </div>

                        <div>
                            <h3 class="text-xl font-semibold mb-3">4.3 Final report</h3>
                            <div class="bg-blue-50/60 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-xl">
                                <p class="m-0 text-sm">Once progress reaches 100%, click <strong class="text-blue-700 dark:text-blue-400">Export Report</strong> in the top-right corner of the job detail page.</p>
                                <p class="m-0 text-sm mt-2">The exported CSV is intended for operational sign-off and client delivery.</p>
                            </div>
                        </div>
                    `
                },
                credentials: {
                    kicker: 'Credential QA',
                    title: '5. Bulk Credential Verification',
                    note: 'Validate host selection, app passwords, and login capability before errors appear halfway through a migration run.',
                    body: `
                        <p>Before launching a large batch, <strong>Check Credentials</strong> lets you test passwords and app passwords in advance.</p>

                        <ol class="space-y-4 list-decimal pl-5">
                            <li class="pl-2">Open <strong>Check Credentials</strong> from the top navigation.</li>
                            <li class="pl-2">
                                Use <strong>Bulk Check</strong> and upload a CSV in the format <code>email,password</code>.
                                <p class="text-sm mt-1 opacity-80"><em>Unlike bulk migration, this CSV only needs 2 columns.</em></p>
                            </li>
                            <li class="pl-2">Choose auto-detection per email domain or force a specific server for the whole file.</li>
                            <li class="pl-2">After the scan, export only failed accounts and send that list back for corrected credentials.</li>
                        </ol>
                    `
                },
                gmail: {
                    kicker: 'Gmail Setup',
                    title: '6. Gmail and Google Workspace App Password',
                    note: 'Use this section to resolve common Gmail login failures, especially for users with 2-step verification enabled.',
                    body: `
                        <div class="bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 p-4 mb-6 rounded-r-xl">
                            <p class="m-0 text-amber-900 dark:text-amber-200 text-sm font-medium">Google no longer allows standard account passwords for IMAP in this flow. You must generate a <strong>16-character App Password</strong>.</p>
                        </div>

                        <ol class="space-y-4 list-decimal pl-5">
                            <li class="pl-2">Enable IMAP in Gmail settings.</li>
                            <li class="pl-2">Open <a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">myaccount.google.com/security</a>.</li>
                            <li class="pl-2">Confirm that <strong>2-Step Verification</strong> is enabled.</li>
                            <li class="pl-2">Open <strong>App passwords</strong> or go directly to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">this link</a>.</li>
                            <li class="pl-2">Create a new app password, for example with the label <code>imapsync</code>.</li>
                            <li class="pl-2">Copy the generated 16-character password and remove spaces before adding it to your CSV or form input.</li>
                        </ol>
                    `
                },
                office: {
                    kicker: 'Office 365',
                    title: '7. Office 365 Guidance',
                    note: 'The tenant-admin and user-level steps needed to make Microsoft 365 authentication behave consistently for IMAP migrations.',
                    body: `
                        <div class="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-6 rounded-r-xl">
                            <p class="m-0 text-red-900 dark:text-red-200 text-sm font-medium">Microsoft has continued tightening legacy auth. Validate IMAP basic authentication policy before you start a large migration.</p>
                        </div>

                        <ol class="space-y-4 list-decimal pl-5">
                            <li class="pl-2">A tenant admin should open the <a href="https://admin.microsoft.com/" class="text-blue-600 dark:text-blue-400">Microsoft 365 admin center</a>.</li>
                            <li class="pl-2">Review the organization settings for modern authentication and verify whether IMAP basic authentication is still allowed in your tenant.</li>
                            <li class="pl-2">Users should enable MFA and create <strong>App Passwords</strong> if the tenant policy still permits this method.</li>
                            <li class="pl-2">If repeated <code>AUTHENTICATIONFAILED</code> errors continue, review Entra ID security defaults and mailbox auth policy assignments.</li>
                        </ol>
                    `
                },
                security: {
                    kicker: 'Security Model',
                    title: '8. Built-in Security Model',
                    note: 'A short summary of the controls around CSV handling, job passwords, and session access so viewers understand the real sharing boundary.',
                    body: `
                        <div class="grid md:grid-cols-2 gap-4">
                            <div class="bg-slate-50 dark:bg-slate-800/50 p-5 rounded-xl border border-slate-200 dark:border-slate-700">
                                <h4 class="font-semibold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                                    CSV handling
                                </h4>
                                <p class="text-sm text-slate-600 dark:text-slate-400 m-0">
                                    Uploaded CSV files are processed for mailbox import and should not be treated as public artifacts. Protect the server and rotate any exposed credentials immediately.
                                </p>
                            </div>
                            <div class="bg-slate-50 dark:bg-slate-800/50 p-5 rounded-xl border border-slate-200 dark:border-slate-700">
                                <h4 class="font-semibold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                                    <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                                    Viewer protection
                                </h4>
                                <p class="text-sm text-slate-600 dark:text-slate-400 m-0">
                                    <strong>Job Password</strong> protects each public viewer link separately from the admin session. Share the viewer link only with the password intended for that specific job.
                                </p>
                            </div>
                        </div>
                    `
                },
                faq: {
                    kicker: 'Troubleshooting',
                    title: '9. FAQ & Troubleshooting',
                    note: 'Common failures are grouped here so operators and clients can look up the right explanation while the migration is still in progress.',
                    body: `
                        <div class="space-y-4">
                            <details class="group bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 open:ring-2 open:ring-blue-500/20 transition-all duration-200">
                                <summary class="flex items-center justify-between p-4 cursor-pointer font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-xl transition-colors">
                                    <span class="flex items-center gap-3">
                                        <span class="w-2 h-2 rounded-full bg-red-500"></span>
                                        AUTHENTICATIONFAILED
                                    </span>
                                    <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </summary>
                                <div class="px-4 pb-4 pt-2 text-slate-600 dark:text-slate-400 text-sm border-t border-slate-100 dark:border-slate-700/50 mt-2">
                                    <ol class="list-decimal pl-5 space-y-1">
                                        <li>Re-check the mailbox username and password for leading or trailing spaces.</li>
                                        <li>For Gmail or Outlook, verify that the account is using an app password instead of the normal web password.</li>
                                        <li>Confirm that IMAP access is enabled on the mailbox.</li>
                                    </ol>
                                </div>
                            </details>

                            <details class="group bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 open:ring-2 open:ring-blue-500/20 transition-all duration-200">
                                <summary class="flex items-center justify-between p-4 cursor-pointer font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-xl transition-colors">
                                    <span class="flex items-center gap-3">
                                        <span class="w-2 h-2 rounded-full bg-orange-500"></span>
                                        Connection timed out / No route to host
                                    </span>
                                    <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </summary>
                                <div class="px-4 pb-4 pt-2 text-slate-600 dark:text-slate-400 text-sm border-t border-slate-100 dark:border-slate-700/50 mt-2">
                                    The host or port is wrong, or the target service is not reachable from the server running IMAP Sync Pro.
                                </div>
                            </details>

                            <details class="group bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 open:ring-2 open:ring-blue-500/20 transition-all duration-200">
                                <summary class="flex items-center justify-between p-4 cursor-pointer font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-xl transition-colors">
                                    <span class="flex items-center gap-3">
                                        <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
                                        Too many simultaneous connections
                                    </span>
                                    <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </summary>
                                <div class="px-4 pb-4 pt-2 text-slate-600 dark:text-slate-400 text-sm border-t border-slate-100 dark:border-slate-700/50 mt-2">
                                    The source provider is throttling concurrent sessions from one IP. Reduce concurrency or split the batch.
                                </div>
                            </details>

                            <details class="group bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 open:ring-2 open:ring-blue-500/20 transition-all duration-200">
                                <summary class="flex items-center justify-between p-4 cursor-pointer font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-xl transition-colors">
                                    <span class="flex items-center gap-3">
                                        <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                                        Quota exceeded
                                    </span>
                                    <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </summary>
                                <div class="px-4 pb-4 pt-2 text-slate-600 dark:text-slate-400 text-sm border-t border-slate-100 dark:border-slate-700/50 mt-2">
                                    The destination mailbox is out of storage and cannot accept more messages until capacity is increased.
                                </div>
                            </details>

                            <details class="group bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 open:ring-2 open:ring-blue-500/20 transition-all duration-200">
                                <summary class="flex items-center justify-between p-4 cursor-pointer font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-xl transition-colors">
                                    <span class="flex items-center gap-3">
                                        <span class="w-2 h-2 rounded-full bg-gray-500"></span>
                                        Message too large
                                    </span>
                                    <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </summary>
                                <div class="px-4 pb-4 pt-2 text-slate-600 dark:text-slate-400 text-sm border-t border-slate-100 dark:border-slate-700/50 mt-2">
                                    The destination provider rejects oversized messages. These items usually need manual handling.
                                </div>
                            </details>

                            <details class="group bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 open:ring-2 open:ring-blue-500/20 transition-all duration-200">
                                <summary class="flex items-center justify-between p-4 cursor-pointer font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-xl transition-colors">
                                    <span class="flex items-center gap-3">
                                        <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                                        Why is sync speed slow?
                                    </span>
                                    <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </summary>
                                <div class="px-4 pb-4 pt-2 text-slate-600 dark:text-slate-400 text-sm border-t border-slate-100 dark:border-slate-700/50 mt-2">
                                    Provider throttling, oversized mailboxes, and storage latency are the usual causes. Review mailbox size and provider limits before scaling up.
                                </div>
                            </details>
                        </div>
                    `
                }
            }
        },
        vi: {
            common: {
                language: {
                    en: 'EN',
                    vi: 'VN'
                }
            },
            header: {
                subtitle: {
                    admin: 'Bảng Điều Khiển Vận Hành',
                    public: 'Tài Liệu Viewer Bảo Mật'
                },
                adminLocked: 'Đã khóa quản trị',
                adminLogin: 'Đăng Nhập Admin',
                logout: 'Đăng xuất',
                themeToggleTitle: 'Đổi giao diện sáng/tối (T)',
                themeToggleAria: 'Đổi giao diện',
                commandPaletteTitle: 'Mở bảng lệnh',
                guide: 'Hướng dẫn',
                checkCredentials: 'Kiểm tra credential',
                manageUsers: 'Quản lý user',
                createJob: 'Tạo job mới',
                dashboard: 'Dashboard',
                languageSwitcherAria: 'Chuyển ngôn ngữ',
                adminStatus: 'Quản trị: {username}'
            },
            footer: {
                copyright: '© 2026 IMAP Sync Pro. Phát triển bởi PhongDH.',
                guide: 'Hướng dẫn',
                newJob: 'Job mới'
            },
            adminGate: {
                kicker: 'Yêu cầu quyền admin',
                login: 'Đăng nhập admin',
                guide: 'Mở hướng dẫn công khai',
                reviewFlow: 'Xem lại quy trình trước',
                reviewChecks: 'Đọc hướng dẫn kiểm tra',
                dashboardTitle: 'Đăng nhập để mở dashboard vận hành.',
                dashboardBody: 'Job Password chỉ bảo vệ viewer của từng job. Dashboard, thống kê hàng đợi và các thao tác quản trị vẫn nằm sau phiên admin.',
                dashboardHint: 'Sau khi xác thực, bạn có thể xem sức khỏe job, xóa lịch sử và mở các phiên migration đã được bảo vệ từ một console.',
                createTitle: 'Đăng nhập để tạo job migration.',
                createBody: 'Job Password chỉ có tác dụng sau khi job đã được tạo. Việc tạo job, tải CSV và nạp credential vẫn thuộc khu vực admin.',
                createHint: 'Sau khi đăng nhập, bạn có thể cấu hình server nguồn và đích, tải batch CSV hoặc chuyển sang chế độ mailbox đơn lẻ.',
                checkTitle: 'Đăng nhập để chạy kiểm tra credential.',
                checkBody: 'Công cụ này thao tác với credential thật và cấu hình server override, nên nó dùng cùng lớp bảo vệ admin như tạo job và quản lý queue.',
                checkHint: 'Nếu chỉ cần quy trình thao tác, hãy xem phần hướng dẫn kiểm tra credential thay vì mở tool admin.'
            },
            modal: {
                confirm: {
                    title: 'Xác nhận',
                    message: 'Bạn có chắc không?',
                    cancel: 'Hủy',
                    confirm: 'Xác nhận'
                },
                admin: {
                    title: 'Đăng nhập Admin',
                    subtitle: 'Đăng nhập để quản lý job và chạy kiểm tra credential.',
                    closeAria: 'Đóng cửa sổ đăng nhập admin',
                    username: 'Tên đăng nhập',
                    password: 'Mật khẩu',
                    passwordPlaceholder: 'Nhập mật khẩu admin',
                    cancel: 'Hủy',
                    submit: 'Đăng nhập'
                }
            },
            dashboard: {
                title: 'Bảng điều khiển admin',
                subtitle: 'Tổng quan các job migration đang chạy và thống kê hệ thống.',
                hero: {
                    kicker: 'Bảng Điều Khiển Admin',
                    title: 'Trung tâm điều phối migration.',
                    subtitle: 'Đăng nhập để tạo job, kiểm tra credential và theo dõi tiến độ IMAP.',
                    signalTrustTitle: 'Phân lớp truy cập rõ',
                    signalTrustCopy: 'Admin ở sau phiên đăng nhập, còn link viewer vẫn tách riêng bằng Job Password.',
                    signalLiveTitle: 'Theo dõi đúng phần cần xem',
                    signalLiveCopy: 'Sức khỏe hàng đợi, trạng thái và lịch sử job được gom lại thành một khu vực dễ quét sau khi đăng nhập.',
                    signalFlowTitle: 'Quy trình ít nhiễu',
                    signalFlowCopy: 'Đi từ kiểm tra credential đến migration và nghiệm thu theo một flow ngắn, rõ.',
                    focusLabel: 'Trọng tâm',
                    focusValue: 'Vận hành migration chắc tay với giao diện ít nhiễu.',
                    flowLabel: 'Luồng khuyến nghị',
                    flowValue: 'Kiểm tra credential, tạo job, theo dõi tiến độ, xuất report.'
                },
                workspace: {
                    kicker: 'Không gian làm việc',
                    title: 'Truy cập admin',
                    body: 'Trang chủ mới đóng vai trò điểm bắt đầu gọn gàng. Các control vận hành và hành động nhạy cảm chỉ hiện sau khi xác thực admin.',
                    guide: 'Mở hướng dẫn',
                    reviewChecks: 'Xem flow kiểm tra credential',
                    createJob: 'Tạo job migration',
                    openChecks: 'Mở kiểm tra credential'
                },
                process: {
                    kicker: 'Luồng đề xuất',
                    title: 'Luồng vận hành đơn giản hơn',
                    note: 'Phần lớn công việc hằng ngày chỉ cần 3 bước này, nên trang chủ không cần nhồi toàn bộ thông tin.',
                    prepareTitle: '1. Kiểm tra credential',
                    prepareBody: 'Xác nhận host, app password và khả năng đăng nhập trước khi tạo batch.',
                    launchTitle: '2. Tạo job đúng phạm vi',
                    launchBody: 'Khai báo nguồn, đích và đặt Job Password để tách viewer khỏi khu vực admin.',
                    monitorTitle: '3. Theo dõi và nghiệm thu',
                    monitorBody: 'Mở job detail để xem tiến độ, log và xuất report khi toàn bộ mailbox hoàn tất.'
                },
                authenticated: {
                    kicker: 'Hàng đợi trực tiếp',
                    title: 'Số liệu và job đang chạy',
                    note: 'Sau khi đăng nhập, phần bên dưới tập trung vào thống kê hệ thống và danh sách job đang vận hành.'
                },
                stats: {
                    allJobs: 'Tổng Job Migration',
                    activeBadge: 'Đang chạy',
                    idleBadge: 'Nhàn rỗi',
                    activeJobs: 'Đang hoạt động',
                    mailboxesSynced: 'Mailbox đã sync',
                    dataTransferred: 'Dữ liệu đã chuyển'
                },
                jobsList: {
                    kicker: 'Hàng đợi job',
                    title: 'Danh sách Job',
                    note: 'Tìm, lọc và mở đúng job cần xử lý mà không bị lẫn bởi các khối thông tin phụ.',
                    clearAll: 'Xóa toàn bộ',
                    refresh: 'Làm mới',
                    searchPlaceholder: 'Tìm job theo tên, server...',
                    filterAll: 'Tất cả',
                    filterRunning: 'Đang chạy',
                    filterCompleted: 'Hoàn tất',
                    filterFailed: 'Lỗi',
                    table: {
                        jobName: 'Tên Job',
                        status: 'Trạng thái',
                        progress: 'Tiến độ',
                        sourceTarget: 'Nguồn → Đích',
                        actions: 'Thao tác'
                    }
                },
                empty: {
                    title: 'Chưa có job nào',
                    description: 'Bắt đầu một phiên migration mới bằng CSV hoặc đồng bộ đơn lẻ.',
                    action: 'Tạo job mới'
                }
            },
            createJob: {
                title: 'Tạo job migration',
                subtitle: 'Cấu hình máy chủ nguồn và đích cho một phiên migration mới.',
                hero: {
                    kicker: 'Quy Trình Admin',
                    title: 'Tạo một phiên migration có kiểm soát.',
                    subtitle: 'Khai báo máy chủ nguồn và đích, nạp dữ liệu credential, rồi khóa viewer của job bằng mật khẩu riêng trước khi chạy.',
                    bestForLabel: 'Phù hợp cho',
                    bestForValue: 'Di chuyển hàng loạt, cutover theo giai đoạn, và các ca recovery đơn lẻ.',
                    securityLabel: 'Ghi chú bảo mật',
                    securityValue: 'Job Password bảo vệ link viewer chia sẻ riêng biệt với phiên admin.'
                },
                sourceServer: {
                    title: 'Máy chủ nguồn'
                },
                targetServer: {
                    title: 'Máy chủ đích'
                },
                fields: {
                    imapHost: 'IMAP Host',
                    port: 'Cổng',
                    security: 'Bảo mật'
                },
                placeholders: {
                    sourceHost: 'imap.gmail.com',
                    targetHost: 'mail.tenmiencuaban.com'
                },
                validation: {
                    imapHostRequired: 'Vui lòng nhập IMAP host',
                    jobPasswordRequired: 'Bắt buộc nhập Job Password'
                },
                security: {
                    none: 'Không mã hóa'
                },
                migrateLabel: 'DI CHUYỂN',
                tabs: {
                    bulk: 'Di chuyển hàng loạt (CSV)',
                    single: 'Đồng bộ đơn lẻ'
                },
                options: {
                    title: 'Tùy chọn migration',
                    jobPassword: 'Job Password',
                    jobPasswordTooltip: 'Đặt mật khẩu để bảo vệ job này. Bất kỳ ai muốn xem chi tiết hoặc tải log đều cần mật khẩu này.',
                    jobPasswordPlaceholder: 'Nhập mật khẩu bảo vệ',
                    advanced: 'Cài đặt nâng cao',
                    syncDates: 'Giữ ngày nội bộ',
                    skipTrash: 'Bỏ qua Trash',
                    dryRun: 'Chạy thử (không copy thật)'
                },
                csv: {
                    title: 'Tải CSV',
                    formatLabel: 'Định dạng:',
                    clickUpload: 'Nhấn để tải lên',
                    orDragDrop: 'hoặc kéo thả',
                    downloadLabel: 'Tải',
                    sampleTemplate: 'mẫu CSV',
                    error: 'Vui lòng tải lên file CSV hợp lệ'
                },
                submit: {
                    bulk: 'Bắt đầu migration hàng loạt',
                    single: 'Bắt đầu migration đơn lẻ'
                },
                single: {
                    title: 'Credential mailbox',
                    sourceAccount: 'Tài khoản nguồn',
                    targetAccount: 'Tài khoản đích',
                    emailLabel: 'Email / Username',
                    passwordLabel: 'Mật khẩu',
                    sourcePlaceholder: 'user@source.com',
                    targetPlaceholder: 'user@target.com',
                    passwordPlaceholder: 'App Password'
                }
            },
            check: {
                title: 'Kiểm tra credential',
                subtitle: 'Xác minh tổ hợp IMAP và thiết lập server override một cách an toàn.',
                hero: {
                    kicker: 'Kiểm Tra Trước Khi Chạy',
                    title: 'Xác minh credential trước khi đụng vào mailbox production.',
                    subtitle: 'Chạy kiểm tra IMAP login cho từng tài khoản hoặc hàng loạt trong khu vực admin để phát hiện sai mật khẩu, thiếu app password hoặc sai cấu hình server trước khi batch migration bắt đầu.',
                    bestUseLabel: 'Dùng tốt nhất cho',
                    bestUseValue: 'Vệ sinh credential, QA onboarding, và xác minh server override.',
                    safetyLabel: 'An toàn',
                    safetyValue: 'Công cụ này chỉ dành cho admin và dùng cùng lớp bảo vệ session + CSRF như console chính.'
                },
                tabs: {
                    single: 'Kiểm tra đơn lẻ',
                    bulk: 'Kiểm tra hàng loạt (CSV)'
                },
                single: {
                    title: 'Kiểm tra credential đơn lẻ',
                    emailLabel: 'Email',
                    emailPlaceholder: 'user@gmail.com',
                    passwordLabel: 'Mật khẩu / App Password',
                    passwordPlaceholder: 'App Password (16 ký tự với Gmail)',
                    serverLabel: 'Máy chủ IMAP',
                    providerLabel: 'Nhà cung cấp',
                    customHostPlaceholder: 'ví dụ: mail.example.com',
                    portLabel: 'Cổng',
                    submit: 'Xác minh credential'
                },
                providers: {
                    autoDetect: '🔍 Tự nhận diện từ email',
                    office365: '📘 Outlook / Office 365',
                    custom: '🔧 Tùy chỉnh...'
                },
                bulk: {
                    title: 'Kiểm tra credential hàng loạt',
                    formatLabel: 'Tải CSV:',
                    perLine: 'mỗi dòng',
                    clickUpload: 'Nhấn để tải lên',
                    orDragDrop: 'hoặc kéo thả',
                    helper: 'File CSV chứa credential email cần xác minh',
                    formatShort: 'Định dạng: email,password',
                    overrideToggle: 'Ép cấu hình server (tùy chọn)',
                    overrideHelp: 'Mặc định hệ thống tự nhận diện server theo domain email. Dùng mục này nếu bạn muốn ép một server cố định cho toàn bộ tài khoản.',
                    autoPerEmail: '🔍 Tự nhận diện theo từng email',
                    customHostPlaceholder: 'mail.custom.com',
                    submit: 'Bắt đầu xác minh hàng loạt'
                },
                results: {
                    title: 'Kết quả xác minh',
                    filterAll: 'Tất cả',
                    filterPassed: 'Đạt',
                    filterFailed: 'Lỗi',
                    exportFailed: 'Xuất danh sách lỗi',
                    table: {
                        email: 'Email',
                        status: 'Trạng thái',
                        server: 'Server',
                        details: 'Chi tiết'
                    }
                }
            },
            users: {
                title: 'Quản lý user',
                subtitle: 'Tạo và quản lý tài khoản admin cho khu vực vận hành.',
                authRequiredTitle: 'Đăng nhập để quản lý user admin.',
                authRequiredBody: 'Các thao tác vòng đời user chỉ dành cho phiên root admin.',
                rootOnlyKicker: 'Chỉ root admin',
                rootOnlyTitle: 'Chỉ root admin được quyền quản lý user.',
                rootOnlyBody: 'Bạn đã đăng nhập, nhưng tài khoản này không có quyền tạo, đổi mật khẩu hoặc xóa user.',
                create: {
                    title: 'Tạo user mới',
                    subtitle: 'Tạo thêm tài khoản để truy cập dashboard vận hành.',
                    submit: 'Tạo user',
                    creating: 'Đang tạo...'
                },
                fields: {
                    username: 'Tên đăng nhập',
                    password: 'Mật khẩu',
                    confirmPassword: 'Nhập lại mật khẩu'
                },
                placeholders: {
                    username: 'new_operator',
                    password: 'Tối thiểu 8 ký tự',
                    confirmPassword: 'Nhập lại đúng mật khẩu'
                },
                list: {
                    title: 'Danh sách user admin',
                    subtitle: 'Mọi user đều vào dashboard được, chỉ root admin được quản lý user.',
                    refresh: 'Làm mới',
                    loading: 'Đang tải danh sách user...',
                    empty: 'Chưa có user nào.',
                    error: 'Lỗi tải danh sách user: {message}',
                    table: {
                        username: 'Tên đăng nhập',
                        role: 'Vai trò',
                        actions: 'Thao tác'
                    }
                },
                roles: {
                    rootAdmin: 'Root Admin',
                    operator: 'Operator'
                },
                actions: {
                    resetPassword: 'Đổi mật khẩu',
                    delete: 'Xóa user'
                }
            },
            jobDetail: {
                hero: {
                    kicker: 'Viewer Bảo Mật',
                    title: 'Theo dõi job trực tiếp mà không lộ thao tác quản trị.',
                    subtitle: 'Trang công khai này dùng để xem tiến độ an toàn, tải report, và theo dõi vận hành sau khi nhập đúng Job Password.',
                    scopeLabel: 'Phạm vi viewer',
                    scopeValue: 'Theo dõi tiến độ, xem log mailbox và xuất dữ liệu cho một job migration.',
                    adminLabel: 'Thao tác admin',
                    adminValue: 'Nút dừng và retry chỉ hiện khi có phiên admin đã xác thực.'
                },
                actions: {
                    downloadLogs: 'Tải log',
                    exportReport: 'Xuất report',
                    stopAll: 'Dừng tất cả'
                },
                progress: {
                    title: 'Tiến độ tổng',
                    totalMailboxes: 'Tổng mailbox',
                    completed: 'Hoàn tất',
                    failed: 'Lỗi',
                    dataTransferred: 'Dữ liệu đã chuyển'
                },
                mailboxes: {
                    title: 'Danh sách mailbox',
                    searchPlaceholder: 'Tìm mailbox...',
                    table: {
                        sourceUser: 'User nguồn',
                        targetUser: 'User đích',
                        status: 'Trạng thái',
                        message: 'Thông điệp',
                        actions: 'Thao tác'
                    },
                    emptyTitle: 'Không tìm thấy mailbox',
                    emptyDescription: 'Bạn đã tải CSV lên chưa?'
                },
                logs: {
                    title: 'Log mailbox',
                    autoScroll: 'Tự cuộn',
                    loading: 'Đang tải log...'
                }
            },
            guide: {
                sidebar: {
                    title: 'Mục Lục',
                    quickStart: 'Bắt Đầu Nhanh',
                    bulkMigration: 'Di Chuyển Hàng Loạt',
                    singleSync: 'Đồng Bộ Đơn Lẻ',
                    monitoring: 'Theo Dõi & Xử Lý Lỗi',
                    checkCredentials: 'Kiểm Tra Mật Khẩu',
                    gmailSetup: 'Cấu Hình Gmail',
                    office365Setup: 'Cấu Hình Office 365',
                    security: 'Bảo Mật',
                    faq: 'FAQ & Xử Lý Sự Cố'
                },
                hero: {
                    kicker: 'Tài Liệu Công Khai',
                    title: 'Tài liệu vận hành rõ ràng cho các phiên di chuyển email.',
                    subtitle: 'Hướng dẫn này ưu tiên khả năng đọc nhanh, nghiệm thu dễ, và xử lý sự cố thực tế cho các job migration đang chạy trên hệ thống.',
                    focusLabel: 'Tập trung',
                    focusValue: 'Checklist thao tác, cấu hình IMAP, và xử lý lỗi phổ biến.',
                    audienceLabel: 'Đối tượng',
                    audienceValue: 'Admin triển khai, kỹ thuật viên vận hành, và khách hàng cần theo dõi kết quả.'
                },
                signals: {
                    oneTitle: '1. Kiểm tra credential',
                    oneCopy: 'Xác nhận host, app password và khả năng đăng nhập trước khi sync hàng loạt.',
                    twoTitle: '2. Tạo job có password riêng',
                    twoCopy: 'Giữ dashboard admin tách biệt khỏi link xem tiến độ chia sẻ cho khách.',
                    threeTitle: '3. Theo dõi và nghiệm thu',
                    threeCopy: 'Dùng job detail để xem log, xác nhận trạng thái và tải report cuối cùng.'
                },
                quickStart: {
                    kicker: 'Bắt Đầu Nhanh',
                    title: '1. Bắt Đầu Nhanh',
                    note: 'Những nguyên tắc cơ bản để người vận hành và người xem job cùng theo một flow rõ ràng, không lẫn giữa admin console và viewer.'
                },
                bulk: {
                    kicker: 'Di Chuyển Hàng Loạt',
                    title: '2. Di Chuyển Hàng Loạt (Bulk Migration)',
                    note: 'Checklist thao tác cho các đợt sync số lượng lớn, ưu tiên rõ host, CSV, job password và các tùy chọn an toàn trước khi chạy.'
                },
                single: {
                    kicker: 'Đồng Bộ Đơn Lẻ',
                    title: '3. Đồng Bộ Đơn Lẻ (Single Sync)',
                    note: 'Gọn hơn cho các ca test, recovery hoặc các đợt chuyển từng mailbox cần kiểm soát thủ công cao hơn.'
                },
                monitoring: {
                    kicker: 'Theo Dõi',
                    title: '4. Theo Dõi & Xuất Báo Cáo',
                    note: 'Theo dõi dashboard, xem log thời gian thực và tải báo cáo nghiệm thu sau khi toàn bộ mailbox hoàn tất.'
                },
                credentials: {
                    kicker: 'Kiểm Tra Credential',
                    title: '5. Kiểm Tra Mật Khẩu Hàng Loạt',
                    note: 'Rà soát trước host, app password và khả năng đăng nhập để giảm lỗi phát sinh ở giữa phiên migration.'
                },
                gmail: {
                    kicker: 'Cấu Hình Gmail',
                    title: '6. Khởi tạo App Password Gmail & Workspace',
                    note: 'Phần này dùng để xử lý nhanh nhóm lỗi đăng nhập Gmail và Google Workspace, đặc biệt khi người dùng đã bật xác thực hai lớp.'
                },
                office: {
                    kicker: 'Office 365',
                    title: '7. Hướng dẫn Office 365 (O365)',
                    note: 'Tập hợp các bước tenant-admin và user-level để xử lý xác thực Microsoft 365 theo một luồng dễ đối chiếu.'
                },
                security: {
                    kicker: 'Mô Hình Bảo Mật',
                    title: '8. Cơ Chế Bảo Mật Tích Hợp',
                    note: 'Tóm tắt ngắn các lớp bảo vệ áp vào file CSV, job password và session truy cập để người xem hiểu đúng phạm vi chia sẻ.'
                },
                faq: {
                    kicker: 'Xử Lý Sự Cố',
                    title: '9. Trả Lời Câu Hỏi & Xử Lý Sự Cố',
                    note: 'Các lỗi thường gặp được gom thành accordion để kỹ thuật viên và khách dễ tra cứu ngay trong lúc job đang chạy.'
                }
            },
            status: {
                running: 'Đang chạy',
                completed: 'Hoàn tất',
                success: 'Thành công',
                failed: 'Lỗi',
                pending: 'Chờ xử lý',
                warning: 'Cảnh báo'
            },
            runtime: {
                common: {
                    errorPrefix: 'Lỗi',
                    loading: 'Đang tải...',
                    auto: 'tự động'
                },
                actions: {
                    view: 'Xem',
                    log: 'Log',
                    stop: 'Dừng',
                    retry: 'Chạy lại',
                    back: 'Quay lại',
                    confirm: 'Xác nhận'
                },
                auth: {
                    enterBothCredentials: 'Vui lòng nhập cả username và password.',
                    loginFailed: 'Đăng nhập thất bại',
                    adminRequired: 'Cần đăng nhập admin',
                    jobProtectedTitle: 'Job đã được bảo vệ',
                    jobProtectedSubtitle: 'Nhập mật khẩu để xem job này',
                    wrongPassword: 'Sai mật khẩu. Vui lòng thử lại.',
                    passwordPlaceholder: 'Nhập mật khẩu...',
                    passwordRequired: 'Vui lòng nhập mật khẩu',
                    unauthorized: 'Không được phép'
                },
                dashboard: {
                    loadJobsFailed: 'Không thể tải danh sách job',
                    unexpectedJobsResponse: 'Phản hồi danh sách job từ server không đúng định dạng',
                    errorLoadingJobs: 'Lỗi khi tải job: {message}',
                    deleteAllConfirm: 'Bạn có chắc muốn xóa TOÀN BỘ job và log không? Thao tác này không thể hoàn tác.',
                    allHistoryCleared: 'Đã xóa toàn bộ lịch sử',
                    deleteJobConfirm: 'Bạn có chắc muốn xóa "{jobName}" không? Log của job này sẽ bị xóa vĩnh viễn.',
                    failedDeleteJobs: 'Không thể xóa danh sách job',
                    failedDeleteJob: 'Không thể xóa job',
                    jobDeleted: 'Đã xóa job và log',
                    deleteThisJobTitle: 'Xóa job này'
                },
                createJob: {
                    fillIn: 'Vui lòng nhập: {fields}',
                    fieldSourceHost: 'Host nguồn',
                    fieldTargetHost: 'Host đích',
                    fieldJobPassword: 'Job Password',
                    fieldCsvFile: 'File CSV',
                    fieldSourceEmail: 'Email nguồn',
                    fieldSourcePassword: 'Mật khẩu nguồn',
                    fieldTargetEmail: 'Email đích',
                    fieldTargetPassword: 'Mật khẩu đích',
                    creating: 'Đang tạo...',
                    startMigration: 'Bắt đầu migration',
                    failedCreateJob: 'Không thể tạo job',
                    csvUploadFailed: 'Tải CSV thất bại',
                    selectCsvFile: 'Vui lòng chọn file CSV',
                    enterSourceAndTargetEmail: 'Vui lòng nhập cả email nguồn và email đích',
                    enterBothPasswords: 'Vui lòng nhập đủ hai mật khẩu',
                    failedAddMailbox: 'Không thể thêm mailbox',
                    csvPreviewTitle: 'Xem trước CSV',
                    mailboxesCount: '{count} mailbox',
                    sourceUser: 'User nguồn',
                    targetUser: 'User đích',
                    password: 'Mật khẩu',
                    passwordPresent: 'Có',
                    passwordMissing: 'Thiếu',
                    showingFirst: 'Đang hiển thị 5 dòng đầu trên tổng {count} mailbox',
                    presetApplied: 'Đã áp dụng preset {provider}',
                    jobName: 'Migration {date} {time}'
                },
                jobDetail: {
                    jobNotFound: 'Không tìm thấy job',
                    errorLoadingJob: 'Lỗi khi tải job',
                    starting: 'Đang khởi động...',
                    partial: 'Phần nào đó hoàn tất',
                    failedCancel: 'Không thể hủy job',
                    failedStop: 'Không thể dừng mailbox',
                    failedRetry: 'Không thể chạy lại mailbox',
                    stopAllConfirm: 'Bạn có chắc muốn dừng TOÀN BỘ mailbox đang chạy không?',
                    stopAllSent: 'Đã gửi lệnh dừng cho toàn bộ mailbox',
                    stopConfirm: 'Bạn có chắc muốn dừng phiên sync này không?',
                    stopSent: 'Đã gửi lệnh dừng',
                    retryConfirm: 'Chạy lại mailbox này?',
                    retrying: 'Đang chạy lại...',
                    loadingLogs: 'Đang tải log...',
                    failedFetchLogs: 'Không thể lấy log',
                    jobIdNotFound: 'Không tìm thấy Job ID',
                    downloadingLogs: 'Đang tải gói log...',
                    zeroBytes: '0 B'
                },
                check: {
                    enterEmailPassword: 'Vui lòng nhập email và mật khẩu',
                    checking: 'Đang kiểm tra...',
                    serverError: 'Lỗi server ({status})',
                    success: 'THÀNH CÔNG',
                    failed: 'THẤT BẠI',
                    verifyCredentials: 'Xác minh credential',
                    uploadCsv: 'Vui lòng tải lên file CSV',
                    processing: 'Đang xử lý...',
                    bulkCheckFailed: 'Kiểm tra hàng loạt thất bại trên server',
                    checkedAccounts: 'Đã kiểm tra {count} tài khoản',
                    startBulkVerification: 'Bắt đầu xác minh hàng loạt',
                    passedCount: '{count} đạt',
                    failedCount: '{count} lỗi',
                    exportFilePrefix: 'credential_loi'
                },
                users: {
                    loadFailed: 'Không thể tải danh sách user',
                    rootOnly: 'Chỉ root admin mới được quản lý user',
                    usernameExists: 'Tên đăng nhập đã tồn tại',
                    passwordTooShort: 'Mật khẩu phải có ít nhất 8 ký tự',
                    invalidUsername: 'Username phải dài 3-32 ký tự và chỉ gồm chữ, số, dấu chấm, gạch dưới hoặc gạch ngang',
                    cannotDeleteRoot: 'Không thể xóa tài khoản root admin',
                    cannotDeleteSelf: 'Không thể xóa chính tài khoản đang đăng nhập',
                    userNotFound: 'Không tìm thấy user',
                    fillAllFields: 'Vui lòng nhập đầy đủ thông tin',
                    passwordMismatch: 'Mật khẩu xác nhận không khớp',
                    createInProgress: 'Đang tạo user, vui lòng chờ...',
                    createFailed: 'Không thể tạo user',
                    userCreated: 'Đã tạo user: {username}',
                    promptNewPassword: 'Nhập mật khẩu mới cho {username}:',
                    passwordRequired: 'Mật khẩu không được để trống',
                    passwordUpdateFailed: 'Không thể đổi mật khẩu',
                    passwordUpdated: 'Đã cập nhật mật khẩu cho {username}',
                    confirmDelete: 'Bạn có chắc muốn xóa user "{username}"?',
                    deleteFailed: 'Không thể xóa user',
                    userDeleted: 'Đã xóa user: {username}'
                },
                commandPalette: {
                    newJobTitle: 'Tạo job mới',
                    newJobSubtitle: 'Tạo một phiên migration mới',
                    dashboardTitle: 'Dashboard',
                    dashboardSubtitle: 'Xem tổng quan job',
                    manageUsersTitle: 'Quản lý user',
                    manageUsersSubtitle: 'Tạo và quản lý tài khoản admin',
                    guideTitle: 'Hướng dẫn sử dụng',
                    guideSubtitle: 'Xem tài liệu chi tiết',
                    refreshTitle: 'Làm mới trang',
                    refreshSubtitle: 'Tải lại dữ liệu hiện tại',
                    themeTitle: 'Đổi giao diện',
                    themeSubtitle: 'Sáng / tối',
                    searchPlaceholder: 'Tìm lệnh...',
                    noMatches: 'Không có lệnh phù hợp'
                },
                estimated: {
                    almostDone: 'Gần xong',
                    minutes: '~{minutes} phút',
                    hoursMinutes: '~{hours}h {minutes}m'
                },
                emptyState: {
                    title: 'Chưa có dữ liệu',
                    description: 'Bắt đầu bằng cách tạo một mục mới',
                    actionText: 'Tạo mới'
                }
            }
        }
    };

    const pageMeta = {
        en: {
            dashboard: {
                title: 'IMAP Sync Dashboard - Professional Email Migration Tool',
                description: 'IMAP Sync Pro - Bulk email migration tool between IMAP servers. Supports Gmail, Office 365, and other IMAP servers.'
            },
            createJob: {
                title: 'Create New Migration Job - IMAP Sync Pro',
                description: 'Create a new email migration job. Supports bulk migration via CSV or single sync.'
            },
            checkCredentials: {
                title: 'Check Credentials - IMAP Sync Pro',
                description: 'Verify email App Passwords and IMAP credentials before migration. Supports Gmail, Yandex, Office 365, and more.'
            },
            users: {
                title: 'User Management - IMAP Sync Pro',
                description: 'Create and manage admin users for IMAP Sync Pro.'
            },
            jobDetail: {
                title: 'Job Details - IMAP Sync Pro',
                description: 'Track email migration progress in detail with real-time logs.'
            },
            guide: {
                title: 'User Guide - IMAP Sync Pro',
                description: 'Detailed documentation for using IMAP Sync Pro to migrate emails between IMAP servers securely and efficiently.'
            },
            default: {
                title: 'IMAP Sync Pro',
                description: 'IMAP Sync Pro'
            }
        },
        vi: {
            dashboard: {
                title: 'Bảng Điều Khiển IMAP Sync - Công Cụ Di Chuyển Email Chuyên Nghiệp',
                description: 'IMAP Sync Pro - Công cụ di chuyển email hàng loạt giữa các máy chủ IMAP. Hỗ trợ Gmail, Office 365 và nhiều máy chủ IMAP khác.'
            },
            createJob: {
                title: 'Tạo Job Di Chuyển Mới - IMAP Sync Pro',
                description: 'Tạo một job di chuyển email mới. Hỗ trợ di chuyển hàng loạt bằng CSV hoặc đồng bộ đơn lẻ.'
            },
            checkCredentials: {
                title: 'Kiểm Tra Credential - IMAP Sync Pro',
                description: 'Xác minh App Password và credential IMAP trước khi di chuyển. Hỗ trợ Gmail, Yandex, Office 365 và nhiều dịch vụ khác.'
            },
            users: {
                title: 'Quản Lý User - IMAP Sync Pro',
                description: 'Tạo và quản lý tài khoản admin cho IMAP Sync Pro.'
            },
            jobDetail: {
                title: 'Chi Tiết Job - IMAP Sync Pro',
                description: 'Theo dõi chi tiết tiến trình di chuyển email với log thời gian thực.'
            },
            guide: {
                title: 'Hướng Dẫn Sử Dụng - IMAP Sync Pro',
                description: 'Hướng dẫn chi tiết cách sử dụng IMAP Sync Pro để di chuyển email giữa các máy chủ IMAP một cách an toàn và hiệu quả.'
            },
            default: {
                title: 'IMAP Sync Pro',
                description: 'IMAP Sync Pro'
            }
        }
    };

    const resolveTranslation = (lang, key) => {
        const parts = String(key || '').split('.');
        let value = translations[lang];
        for (const part of parts) {
            if (!value || typeof value !== 'object' || !(part in value)) {
                return undefined;
            }
            value = value[part];
        }
        return value;
    };

    const interpolate = (template, params = {}) =>
        String(template).replace(/\{(\w+)\}/g, (_, token) => (
            Object.prototype.hasOwnProperty.call(params, token) ? params[token] : `{${token}}`
        ));

    const normalizeLanguage = (value) => {
        if (!value) return null;
        const short = String(value).toLowerCase().split('-')[0];
        return SUPPORTED_LANGUAGES.includes(short) ? short : null;
    };

    const getInitialLanguage = () => {
        const saved = normalizeLanguage(localStorage.getItem(STORAGE_KEY));
        if (saved) return saved;
        return normalizeLanguage(navigator.language) || 'en';
    };

    const getCurrentLanguage = () => normalizeLanguage(localStorage.getItem(STORAGE_KEY)) || getInitialLanguage();

    const setLanguage = (lang, options = {}) => {
        const normalized = normalizeLanguage(lang) || 'en';
        localStorage.setItem(STORAGE_KEY, normalized);
        if (options.reload === false) {
            applyTranslations();
            return;
        }
        window.location.reload();
    };

    const t = (key, params = {}, fallback = '') => {
        const translated = resolveTranslation(getCurrentLanguage(), key);
        if (typeof translated === 'string') {
            return interpolate(translated, params);
        }
        return interpolate(fallback || key, params);
    };

    const captureOriginal = (element, datasetKey, getter) => {
        if (!element.dataset[datasetKey]) {
            element.dataset[datasetKey] = getter(element);
        }
    };

    const applyTextTranslation = (element) => {
        captureOriginal(element, 'i18nOriginalText', (node) => node.textContent);
        const translated = resolveTranslation(getCurrentLanguage(), element.dataset.i18n);
        element.textContent = typeof translated === 'string' ? translated : element.dataset.i18nOriginalText;
    };

    const applyHtmlTranslation = (element) => {
        captureOriginal(element, 'i18nOriginalHtml', (node) => node.innerHTML);
        const translated = resolveTranslation(getCurrentLanguage(), element.dataset.i18nHtml);
        element.innerHTML = typeof translated === 'string' ? translated : element.dataset.i18nOriginalHtml;
    };

    const applyAttrTranslation = (element, attrName, datasetKey, originalKey) => {
        captureOriginal(element, originalKey, (node) => node.getAttribute(attrName) || '');
        const translated = resolveTranslation(getCurrentLanguage(), element.dataset[datasetKey]);
        element.setAttribute(attrName, typeof translated === 'string' ? translated : element.dataset[originalKey]);
    };

    const updateLanguageSwitcher = () => {
        const current = getCurrentLanguage();
        document.querySelectorAll('[data-lang-option]').forEach((button) => {
            const active = button.dataset.langOption === current;
            button.classList.toggle('active', active);
            button.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    };

    const bindLanguageSwitcher = () => {
        document.querySelectorAll('[data-lang-option]').forEach((button) => {
            if (button.dataset.i18nBound === 'true') return;
            button.dataset.i18nBound = 'true';
            button.addEventListener('click', (event) => {
                event.preventDefault();
                setLanguage(button.dataset.langOption);
            });
        });
    };

    const updateMeta = () => {
        const lang = getCurrentLanguage();
        const pageId = document.body?.dataset?.page || 'default';
        const meta = (pageMeta[lang] && (pageMeta[lang][pageId] || pageMeta[lang].default)) || pageMeta.en.default;
        if (!meta) return;

        document.title = meta.title;

        const description = document.querySelector('meta[name="description"]');
        const ogTitle = document.querySelector('meta[property="og:title"]');
        const ogDescription = document.querySelector('meta[property="og:description"]');

        if (description) description.setAttribute('content', meta.description);
        if (ogTitle) ogTitle.setAttribute('content', meta.title);
        if (ogDescription) ogDescription.setAttribute('content', meta.description);
    };

    const applyTranslations = () => {
        const current = getCurrentLanguage();
        document.documentElement.lang = current;

        document.querySelectorAll('[data-i18n]').forEach(applyTextTranslation);
        document.querySelectorAll('[data-i18n-html]').forEach(applyHtmlTranslation);
        document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
            applyAttrTranslation(element, 'placeholder', 'i18nPlaceholder', 'i18nOriginalPlaceholder');
        });
        document.querySelectorAll('[data-i18n-title]').forEach((element) => {
            applyAttrTranslation(element, 'title', 'i18nTitle', 'i18nOriginalTitle');
        });
        document.querySelectorAll('[data-i18n-aria-label]').forEach((element) => {
            applyAttrTranslation(element, 'aria-label', 'i18nAriaLabel', 'i18nOriginalAriaLabel');
        });

        updateMeta();
        updateLanguageSwitcher();
    };

    window.t = t;
    window.getCurrentLanguage = getCurrentLanguage;
    window.setLanguage = setLanguage;
    window.getCurrentLocale = () => (getCurrentLanguage() === 'vi' ? 'vi-VN' : 'en-US');

    document.addEventListener('DOMContentLoaded', () => {
        bindLanguageSwitcher();
        applyTranslations();
    });
})();
