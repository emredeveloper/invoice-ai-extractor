// ===== Configuration =====
const API_BASE_URL = window.location.origin;
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// ===== DOM Elements =====
const elements = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    menuToggle: document.getElementById('menuToggle'),
    navItems: document.querySelectorAll('.nav-item'),

    // Pages
    pages: document.querySelectorAll('.page'),
    pageContent: document.getElementById('pageContent'),

    // Header
    themeToggle: document.getElementById('themeToggle'),
    authBtn: document.getElementById('authBtn'),
    searchInput: document.getElementById('searchInput'),

    // User info
    userName: document.getElementById('userName'),
    userEmail: document.getElementById('userEmail'),

    // Dashboard
    totalInvoices: document.getElementById('totalInvoices'),
    completedInvoices: document.getElementById('completedInvoices'),
    failedInvoices: document.getElementById('failedInvoices'),
    totalTax: document.getElementById('totalTax'),
    totalAmount: document.getElementById('totalAmount'),
    topSuppliers: document.getElementById('topSuppliers'),
    recentInvoicesTable: document.getElementById('recentInvoicesTable'),

    // Upload
    uploadZone: document.getElementById('uploadZone'),
    uploadSelectBtn: document.getElementById('uploadSelectBtn'),
    fileInput: document.getElementById('fileInput'),
    uploadProgress: document.getElementById('uploadProgress'),
    uploadFileName: document.getElementById('uploadFileName'),
    uploadStatus: document.getElementById('uploadStatus'),
    progressFill: document.getElementById('progressFill'),
    uploadResult: document.getElementById('uploadResult'),
    resultData: document.getElementById('resultData'),
    uploadAnother: document.getElementById('uploadAnother'),

    // Invoices
    invoicesTable: document.getElementById('invoicesTable'),
    filterStatus: document.getElementById('filterStatus'),
    filterSupplier: document.getElementById('filterSupplier'),
    filterDateFrom: document.getElementById('filterDateFrom'),
    filterDateTo: document.getElementById('filterDateTo'),
    applyFilters: document.getElementById('applyFilters'),
    exportCsv: document.getElementById('exportCsv'),
    exportExcel: document.getElementById('exportExcel'),
    pagination: document.getElementById('pagination'),

    // Batch
    batchUploadZone: document.getElementById('batchUploadZone'),
    batchSelectBtn: document.getElementById('batchSelectBtn'),
    batchFileInput: document.getElementById('batchFileInput'),
    batchQueue: document.getElementById('batchQueue'),
    queueList: document.getElementById('queueList'),
    queueCount: document.getElementById('queueCount'),
    clearQueue: document.getElementById('clearQueue'),
    startBatch: document.getElementById('startBatch'),
    batchJobsTable: document.getElementById('batchJobsTable'),

    // Webhooks
    webhooksTable: document.getElementById('webhooksTable'),
    addWebhook: document.getElementById('addWebhook'),

    // Settings
    settingsEmail: document.getElementById('settingsEmail'),
    settingsUsername: document.getElementById('settingsUsername'),
    generateApiKey: document.getElementById('generateApiKey'),
    logoutBtn: document.getElementById('logoutBtn'),

    // Auth Modal
    authModal: document.getElementById('authModal'),
    authForm: document.getElementById('authForm'),
    authModalTitle: document.getElementById('authModalTitle'),
    authEmail: document.getElementById('authEmail'),
    authPassword: document.getElementById('authPassword'),
    authUsername: document.getElementById('authUsername'),
    usernameGroup: document.getElementById('usernameGroup'),
    authSubmit: document.getElementById('authSubmit'),
    authSwitchText: document.getElementById('authSwitchText'),
    authSwitchLink: document.getElementById('authSwitchLink'),
    closeAuthModal: document.getElementById('closeAuthModal'),

    // Webhook Modal
    webhookModal: document.getElementById('webhookModal'),
    webhookForm: document.getElementById('webhookForm'),
    webhookUrl: document.getElementById('webhookUrl'),
    webhookSecret: document.getElementById('webhookSecret'),
    webhookOnSuccess: document.getElementById('webhookOnSuccess'),
    webhookOnFailure: document.getElementById('webhookOnFailure'),
    closeWebhookModal: document.getElementById('closeWebhookModal'),

    // Invoice Modal
    invoiceModal: document.getElementById('invoiceModal'),
    invoiceModalBody: document.getElementById('invoiceModalBody'),
    closeInvoiceModal: document.getElementById('closeInvoiceModal'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),

    // Performance chart meta
    perfRange: document.getElementById('perfRange'),
    perfTotal: document.getElementById('perfTotal'),
    perfCount: document.getElementById('perfCount'),
};

// ===== State =====
let isLoginMode = true;
let batchFiles = [];
let currentPage = 1;
let totalPages = 1;
const dialogLocks = { upload: false, batch: false };
let charts = {
    performance: null,
    category: null
};

// ===== Utility Functions =====
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastIn 0.25s ease reverse';
        setTimeout(() => toast.remove(), 250);
    }, 3000);
}

function normalizeCurrency(code) {
    if (!code) return 'TRY';
    const upper = String(code).toUpperCase();
    if (upper === 'TL' || upper === 'TRY') return 'TRY';
    return upper;
}

function isTryCurrency(code) {
    return normalizeCurrency(code) === 'TRY';
}

function formatCurrency(amount, currency = 'TRY') {
    if (amount === null || amount === undefined) return '-';
    const symbols = { TRY: '₺', USD: '$', EUR: '€' };
    const cleanCurrency = normalizeCurrency(currency);
    const symbol = symbols[cleanCurrency] || cleanCurrency;
    return `${symbol}${Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US');
}

function getStatusBadge(status) {
    const badges = {
        completed: '<span class="badge badge-success">Successful</span>',
        pending: '<span class="badge badge-warning">Pending</span>',
        processing: '<span class="badge badge-info">Processing</span>',
        failed: '<span class="badge badge-danger">Failed</span>',
    };
    return badges[status] || `<span class="badge">${status}</span>`;
}

function openFileDialog(input, lockKey) {
    if (dialogLocks[lockKey]) return;
    dialogLocks[lockKey] = true;
    input.value = '';
    input.click();
}

// ===== API Functions =====
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            logout();
            throw new Error('Session expired');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }

        if (response.status === 204) return null;
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const headers = {};
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        headers,
        body: formData,
    });

    if (response.status === 401) {
        logout();
            throw new Error('Your session has expired or you are not authorized. Please sign in again.');
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'File upload failed');
    }

    return await response.json();
}

async function pollTaskStatus(taskId, onProgress) {
    let attempts = 0;
    const maxAttempts = 120; // 2 minutes max

    while (attempts < maxAttempts) {
        const result = await apiRequest(`/status/${taskId}`);

        if (result.status === 'SUCCESS') {
            return result.result;
        } else if (result.status === 'FAILED') {
            throw new Error(result.result?.error || 'Processing failed');
        }

        onProgress && onProgress(result.status);
        await new Promise(r => setTimeout(r, 1000));
        attempts++;
    }

    throw new Error('Processing timeout');
}

// ===== Auth Functions =====
async function login(email, password) {
    const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    });

    authToken = data.access_token;
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('refreshToken', data.refresh_token);

    await loadCurrentUser();
    showToast('Signed in successfully!', 'success');
}

async function register(email, username, password) {
    await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, username, password }),
    });

    showToast('Registration successful! You can sign in now.', 'success');
    toggleAuthMode();
}

async function loadCurrentUser() {
    if (!authToken) return;

    try {
        currentUser = await apiRequest('/auth/me');
        updateUserUI();
    } catch (error) {
        logout();
    }
}

function updateUserUI() {
    if (currentUser) {
        elements.userName.textContent = currentUser.username;
        elements.userEmail.textContent = currentUser.email;
        elements.authBtn.textContent = 'Sign Out';
        elements.authBtn.onclick = logout;

        elements.settingsEmail.value = currentUser.email;
        elements.settingsUsername.value = currentUser.username;
    } else {
        elements.userName.textContent = 'Sign In';
        elements.userEmail.textContent = '';
        elements.authBtn.textContent = 'Sign In';
        elements.authBtn.onclick = () => openModal(elements.authModal);
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    updateUserUI();
    showToast('Signed out', 'info');
    navigateTo('dashboard');
}

function toggleAuthMode() {
    isLoginMode = !isLoginMode;

    if (isLoginMode) {
        elements.authModalTitle.textContent = 'Sign In';
        elements.usernameGroup.classList.add('hidden');
        elements.authSubmit.textContent = 'Sign In';
        elements.authSwitchText.textContent = "Don't have an account?";
        elements.authSwitchLink.textContent = 'Sign Up';
    } else {
        elements.authModalTitle.textContent = 'Sign Up';
        elements.usernameGroup.classList.remove('hidden');
        elements.authSubmit.textContent = 'Sign Up';
        elements.authSwitchText.textContent = 'Already have an account?';
        elements.authSwitchLink.textContent = 'Sign In';
    }
}

// ===== Modal Functions =====
function openModal(modal) {
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// ===== Navigation =====
function navigateTo(page) {
    elements.pages.forEach(p => p.classList.remove('active'));
    elements.navItems.forEach(n => n.classList.remove('active'));

    const targetPage = document.getElementById(`page-${page}`);
    const targetNav = document.querySelector(`[data-page="${page}"]`);

    if (targetPage) targetPage.classList.add('active');
    if (targetNav) targetNav.classList.add('active');

    // Load page data
    switch (page) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'invoices':
            loadInvoices();
            break;
        case 'batch':
            loadBatchJobs();
            break;
        case 'webhooks':
            loadWebhooks();
            break;
    }

    // Close sidebar on mobile
    elements.sidebar.classList.remove('open');
}

// ===== Dashboard =====
async function loadDashboard() {
    if (!authToken) {
        elements.totalInvoices.textContent = '0';
        elements.completedInvoices.textContent = '0';
        elements.failedInvoices.textContent = '0';
        elements.totalAmount.textContent = '₺0';
        return;
    }

    try {
        const stats = await apiRequest('/invoices/stats');

        elements.totalInvoices.textContent = stats.total_invoices;
        elements.completedInvoices.textContent = stats.completed_invoices;
        elements.failedInvoices.textContent = stats.failed_invoices;
        elements.totalTax.textContent = formatCurrency(stats.total_tax);
        elements.totalAmount.textContent = formatCurrency(stats.total_amount);

        // Recent invoices
        if (stats.recent_invoices && stats.recent_invoices.length > 0) {
            elements.recentInvoicesTable.innerHTML = stats.recent_invoices.map(inv => `
                <tr>
                    <td>${inv.invoice_number || '-'}</td>
                    <td>${inv.supplier_name || '-'}</td>
                    <td>${formatCurrency(inv.total_amount, inv.currency)}</td>
                    <td>${getStatusBadge(inv.status)}</td>
                    <td>${formatDate(inv.created_at)}</td>
                </tr>
            `).join('');
        }

        const trend = stats.spending_trend || [];
        const trendTotals = trend.map(d => d.total || 0);
        const trendCounts = trend.map(d => d.count || 0);
        const totalAmount = trendTotals.reduce((sum, v) => sum + v, 0);
        const totalCount = trendCounts.reduce((sum, v) => sum + v, 0);

        if (elements.perfRange) elements.perfRange.textContent = 'Last 7 days';
        if (elements.perfTotal) elements.perfTotal.textContent = formatCurrency(totalAmount, 'TRY');
        if (elements.perfCount) elements.perfCount.textContent = `${totalCount} fatura`;

        // --- Performance Chart (Spending Trend) ---
        const perfCtx = document.getElementById('performanceChart').getContext('2d');
        if (charts.performance) charts.performance.destroy();

        charts.performance = new Chart(perfCtx, {
            type: 'line',
            data: {
                labels: trend.map(d => formatDate(d.date)),
                datasets: [{
                    label: 'Daily total (TRY)',
                    data: trendTotals,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#6366f1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const idx = context.dataIndex;
                                const amount = formatCurrency(trendTotals[idx], 'TRY');
                                const count = trendCounts[idx] || 0;
                                return [`Toplam: ${amount}`, `Adet: ${count}`];
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });

        // --- Category/Supplier Distribution Chart ---
        const catCtx = document.getElementById('categoryChart').getContext('2d');
        if (charts.category) charts.category.destroy();

        charts.category = new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: stats.category_stats.map(s => s.name || 'Bilinmeyen'),
                datasets: [{
                    data: stats.category_stats.map(s => s.value),
                    backgroundColor: [
                        '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'
                    ],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8', font: { size: 11 }, usePointStyle: true }
                    }
                },
                cutout: '70%'
            }
        });

    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

// ===== Upload =====
async function handleFileUpload(file) {
    elements.uploadZone.classList.add('hidden');
    elements.uploadProgress.classList.remove('hidden');
    elements.uploadResult.classList.add('hidden');

    elements.uploadFileName.textContent = file.name;
    elements.uploadStatus.textContent = 'Uploading...';
    elements.progressFill.style.width = '30%';

    try {
        const { task_id } = await uploadFile(file);

        elements.uploadStatus.textContent = 'Processing...';
        elements.progressFill.style.width = '60%';

        const result = await pollTaskStatus(task_id, (status) => {
            elements.uploadStatus.textContent = status === 'STARTED' ? 'Analyzing...' : 'Pending...';
        });

        elements.progressFill.style.width = '100%';
        elements.uploadStatus.textContent = 'Completed!';

        setTimeout(() => {
            elements.uploadProgress.classList.add('hidden');
            elements.uploadResult.classList.remove('hidden');
            displayUploadResult(result);
        }, 500);

        showToast('Invoice processed successfully!', 'success');
    } catch (error) {
        elements.uploadStatus.textContent = 'Hata!';
        elements.progressFill.style.background = 'var(--danger)';
        showToast(error.message, 'error');
    }
}

function displayUploadResult(result) {
    const currency = normalizeCurrency(result.currency || 'TRY');

    // Check if result has general_fields or is flattened
    const data = result.general_fields || result;
    const date = data.date || data.invoice_date || '-';

    elements.resultData.innerHTML = `
        <div class="invoice-summary">
            <div class="summary-grid">
                <div class="summary-item">
                    <label>Invoice No</label>
                    <span class="value">${data.invoice_number || '-'}</span>
                </div>
                <div class="summary-item">
                    <label>Supplier</label>
                    <span class="value">${data.supplier_name || '-'}</span>
                </div>
                <div class="summary-item">
                    <label>Tarih</label>
                    <span class="value">${date}</span>
                </div>
                <div class="summary-item">
                    <label>Toplam Tutar</label>
                    <span class="value highlighted">${formatCurrency(data.total_amount, currency)}</span>
                </div>
            </div>

            ${result.items && result.items.length > 0 ? `
                <div class="summary-items-title">Invoice Line Items</div>
                <div class="summary-items-list">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Product / Service</th>
                                <th>Adet</th>
                                <th>Toplam</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${result.items.slice(0, 5).map(item => `
                                <tr>
                                    <td>${item.product_name || '-'}</td>
                                    <td>${item.quantity || '-'}</td>
                    <td>${formatCurrency(item.total_price, currency)}</td>
                                </tr>
                            `).join('')}
                            ${result.items.length > 5 ? `<tr><td colspan="3" style="text-align:center; padding: 10px; font-style: italic; color: var(--text-muted);">...ve ${result.items.length - 5} kalem daha</td></tr>` : ''}
                        </tbody>
                    </table>
                </div>
            ` : ''}

            <div class="summary-meta">
                <span>Processing Time: ${(result.processing_time_ms / 1000).toFixed(2)}sn</span>
                <span>•</span>
                <span>Confidence Score: %${Math.round((result.confidence || 0.95) * 100)}</span>
            </div>
        </div>
    `;
}

// ===== Invoices =====
async function loadInvoices(page = 1) {
    if (!authToken) {
        elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty-state">You need to sign in</td></tr>';
        return;
    }

    try {
        const params = new URLSearchParams({
            page,
            page_size: 10,
        });

        if (elements.filterStatus.value) params.append('status', elements.filterStatus.value);
        if (elements.filterSupplier.value) params.append('supplier_name', elements.filterSupplier.value);
        if (elements.filterDateFrom.value) params.append('date_from', elements.filterDateFrom.value);
        if (elements.filterDateTo.value) params.append('date_to', elements.filterDateTo.value);

        const data = await apiRequest(`/invoices?${params}`);
        currentPage = data.page;
        totalPages = data.total_pages;

        if (data.items.length === 0) {
            elements.invoicesTable.innerHTML = '<tr><td colspan="7" class="empty-state">No invoices found</td></tr>';
        } else {
            elements.invoicesTable.innerHTML = data.items.map(inv => `
                <tr>
                    <td>${inv.invoice_number || '-'}</td>
                    <td>${inv.supplier_name || '-'}</td>
                    <td>${inv.invoice_date || '-'}</td>
                    <td>${formatCurrency(inv.total_amount, inv.currency)}</td>
                    <td>${formatCurrency(inv.tax_amount, inv.currency)}</td>
                    <td>${getStatusBadge(inv.status)}</td>
                    <td>
                        <button class="btn btn-ghost" onclick="viewInvoice('${inv.id}')">👁️</button>
                        <button class="btn btn-ghost" onclick="deleteInvoice('${inv.id}')">🗑️</button>
                    </td>
                </tr>
            `).join('');
        }

        renderPagination();
    } catch (error) {
        showToast('Failed to load invoices', 'error');
    }
}

function renderPagination() {
    if (totalPages <= 1) {
        elements.pagination.innerHTML = '';
        return;
    }

    let html = `
        <button ${currentPage === 1 ? 'disabled' : ''} onclick="loadInvoices(${currentPage - 1})">←</button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<button class="${i === currentPage ? 'active' : ''}" onclick="loadInvoices(${i})">${i}</button>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += `<button disabled>...</button>`;
        }
    }

    html += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="loadInvoices(${currentPage + 1})">→</button>`;

    elements.pagination.innerHTML = html;
}

async function viewInvoice(id) {
    try {
        const invoice = await apiRequest(`/invoices/${id}`);
        openModal(elements.invoiceModal);

        const isImage = ['.jpg', '.jpeg', '.png'].includes(invoice.file_type.toLowerCase());
        const fileUrl = `${API_BASE_URL}/files/${id}?token=${authToken}`; // Token for preview

        elements.invoiceModalBody.innerHTML = `
            <div class="verification-container">
                <div class="preview-pane">
                    ${isImage
                ? `<img src="${fileUrl}" alt="Invoice Preview">`
                : `<iframe src="${fileUrl}" frameborder="0"></iframe>`
            }
                </div>
                <div class="editor-pane">
                    ${invoice.ai_review ? `
                        <div class="ai-review-section">
                            <div class="ai-header">
                                <span>🤖 AI Reviewer</span>
                                <span class="ai-risk-badge risk-${invoice.ai_review.risk_level?.toLowerCase() || 'low'}">
                                    ${invoice.ai_review.risk_level || 'Low'} Risk
                                </span>
                            </div>
                            <p class="ai-summary">${invoice.ai_review.summary || ''}</p>
                            <div class="ai-action-box">
                                <strong>💡 Suggestion:</strong> ${invoice.ai_review.suggested_action || 'Approve'}
                            </div>
                        </div>
                    ` : ''}

                    <form id="editInvoiceForm">
                        <div class="form-grid">
                            <div class="form-group">
                                <label>Invoice No</label>
                                <input type="text" name="invoice_number" class="form-input" value="${invoice.invoice_number || ''}">
                            </div>
                            <div class="form-group">
                                <label>Tarih</label>
                                <input type="text" name="invoice_date" class="form-input" value="${invoice.invoice_date || ''}">
                            </div>
                            <div class="form-group">
                                <label>Supplier</label>
                                <input type="text" name="supplier_name" class="form-input" value="${invoice.supplier_name || ''}">
                            </div>
                            <div class="form-group">
                                <label>Kategori</label>
                                <select name="category" class="form-input">
                                    <option value="General" ${invoice.category === 'General' ? 'selected' : ''}>General</option>
                                    <option value="Fuel" ${invoice.category === 'Fuel' ? 'selected' : ''}>Fuel</option>
                                    <option value="Food" ${invoice.category === 'Food' ? 'selected' : ''}>Food</option>
                                    <option value="Technology" ${invoice.category === 'Technology' ? 'selected' : ''}>Technology</option>
                                    <option value="Logistics" ${invoice.category === 'Logistics' ? 'selected' : ''}>Logistics</option>
                                    <option value="Services" ${invoice.category === 'Services' ? 'selected' : ''}>Services</option>
                                    <option value="Stationery" ${invoice.category === 'Stationery' ? 'selected' : ''}>Stationery</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Toplam Tutar</label>
                                <input type="number" step="0.01" name="total_amount" class="form-input" value="${invoice.total_amount || ''}">
                                ${invoice.conversion && !isTryCurrency(invoice.currency) ? `
                                    <div class="conversion-info">
                                        <span>≈ ${formatCurrency(invoice.conversion.amount_try, 'TRY')}</span>
                                        <span class="conversion-rate">(1 ${normalizeCurrency(invoice.currency)} = ${invoice.conversion.rate} TRY)</span>
                                    </div>
                                ` : ''}
                            </div>
                            <div class="form-group">
                                <label>Para Birimi</label>
                                <input type="text" name="currency" class="form-input" value="${invoice.currency || ''}">
                            </div>
                            <div class="form-group">
                                <label>Tax Amount</label>
                                <input type="number" step="0.01" name="tax_amount" class="form-input" value="${invoice.tax_amount || ''}">
                            </div>
                            <div class="form-group">
                                <label>Tax Rate (%)</label>
                                <input type="number" name="tax_rate" class="form-input" value="${invoice.tax_rate || ''}">
                            </div>
                        </div>

                        <div class="mt-4">
                            <h4>Invoice Line Items</h4>
                            <div class="items-editor">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th>Item</th>
                                            <th>Adet</th>
                                            <th>Fiyat</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${invoice.items.map(item => `
                                            <tr>
                                                <td>${item.product_name || '-'}</td>
                                                <td>${item.quantity || '-'}</td>
                                                <td>${formatCurrency(item.total_price, invoice.currency)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td colspan="3" style="text-align: center;">
                                                <button type="button" class="btn btn-sm btn-secondary">Kalem Ekle</button>
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        </div>

                        <div class="form-actions mt-4">
                            <button type="button" class="btn btn-primary" onclick="saveInvoice('${id}')">Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    } catch (error) {
        showToast('Failed to load invoice details', 'error');
    }
}

async function saveInvoice(id) {
    const form = document.getElementById('editInvoiceForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convert numeric fields
    ['total_amount', 'tax_amount', 'tax_rate'].forEach(key => {
        if (data[key]) data[key] = parseFloat(data[key]);
        else delete data[key];
    });

    try {
        await apiRequest(`/invoices/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });

        showToast('Invoice updated!', 'success');
        closeModal(elements.invoiceModal); // Close modal after saving
        loadInvoices(currentPage);
        loadDashboard();
    } catch (error) {
        showToast('Update failed', 'error');
    }
}

async function deleteInvoice(id) {
    if (!confirm('Are you sure you want to delete this invoice?')) return;

    try {
        await apiRequest(`/invoices/${id}`, { method: 'DELETE' });
        showToast('Invoice deleted', 'success');
        loadInvoices(currentPage);
    } catch (error) {
        showToast('Failed to delete invoice', 'error');
    }
}

async function exportInvoices(format) {
    if (!authToken) {
        showToast('You need to sign in', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/invoices/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({ format }),
        });

        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `invoices.${format === 'csv' ? 'csv' : 'xlsx'}`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('Export successful!', 'success');
    } catch (error) {
        showToast('Export failed', 'error');
    }
}

// ===== Batch Processing =====
function handleBatchFiles(files) {
    batchFiles = Array.from(files).slice(0, 50);

    if (batchFiles.length > 0) {
        elements.batchQueue.classList.remove('hidden');
        elements.queueCount.textContent = `${batchFiles.length} files`;

        elements.queueList.innerHTML = batchFiles.map((file, i) => `
            <li class="queue-item">
                <span>${file.name}</span>
                <button class="btn btn-ghost" onclick="removeBatchFile(${i})">×</button>
            </li>
        `).join('');
    }
}

function removeBatchFile(index) {
    batchFiles.splice(index, 1);
    handleBatchFiles(batchFiles);

    if (batchFiles.length === 0) {
        elements.batchQueue.classList.add('hidden');
    }
}

async function startBatchUpload() {
    if (!authToken) {
        showToast('You need to sign in', 'warning');
        return;
    }

    if (batchFiles.length === 0) return;

    const formData = new FormData();
    batchFiles.forEach(file => formData.append('files', file));

    try {
        const response = await fetch(`${API_BASE_URL}/batch/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
            body: formData,
        });

        if (!response.ok) throw new Error('Batch upload failed');

        const result = await response.json();
        showToast(`Batch started: ${result.total_files} files`, 'success');

        batchFiles = [];
        elements.batchQueue.classList.add('hidden');
        loadBatchJobs();
    } catch (error) {
        showToast('Batch upload failed', 'error');
    }
}

async function loadBatchJobs() {
    if (!authToken) return;

    try {
        const jobs = await apiRequest('/batch');
        let hasProcessing = false;

        if (jobs.length === 0) {
            elements.batchJobsTable.innerHTML = '<tr><td colspan="6" class="empty-state">No batch jobs found</td></tr>';
        } else {
            elements.batchJobsTable.innerHTML = jobs.map(job => {
                if (job.status === 'processing' || job.status === 'pending') hasProcessing = true;

                return `
                    <tr>
                        <td>${job.id.slice(0, 8)}...</td>
                        <td>${job.total_files}</td>
                        <td>${job.successful_files}</td>
                        <td>${job.failed_files}</td>
                        <td>${getStatusBadge(job.status)}</td>
                        <td>${formatDate(job.created_at)}</td>
                    </tr>
                `;
            }).join('');
        }

        // Auto poll if any job is processing
        if (hasProcessing) {
            if (window.batchTimer) clearTimeout(window.batchTimer);
            window.batchTimer = setTimeout(loadBatchJobs, 5000);
        }
    } catch (error) {
        console.error('Failed to load batch jobs:', error);
    }
}

// ===== Webhooks =====
async function loadWebhooks() {
    if (!authToken) {
        elements.webhooksTable.innerHTML = '<tr><td colspan="5" class="empty-state">You need to sign in</td></tr>';
        return;
    }

    try {
        const webhooks = await apiRequest('/webhooks');

        if (webhooks.length === 0) {
            elements.webhooksTable.innerHTML = '<tr><td colspan="5" class="empty-state">No webhooks found</td></tr>';
        } else {
            elements.webhooksTable.innerHTML = webhooks.map(wh => `
                <tr>
                    <td>${wh.url}</td>
                    <td>${wh.is_active ? '<span class="badge badge-success">Aktif</span>' : '<span class="badge badge-danger">Pasif</span>'}</td>
                    <td>${wh.successful_calls}/${wh.total_calls}</td>
                    <td>${wh.last_called_at ? formatDate(wh.last_called_at) : '-'}</td>
                    <td>
                        <button class="btn btn-ghost" onclick="testWebhook('${wh.id}')">🧪</button>
                        <button class="btn btn-ghost" onclick="deleteWebhook('${wh.id}')">🗑️</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showToast('Failed to load webhooks', 'error');
    }
}

async function createWebhook() {
    const data = {
        url: elements.webhookUrl.value,
        secret: elements.webhookSecret.value || null,
        on_success: elements.webhookOnSuccess.checked,
        on_failure: elements.webhookOnFailure.checked,
    };

    try {
        await apiRequest('/webhooks', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        showToast('Webhook created!', 'success');
        closeModal(elements.webhookModal);
        elements.webhookForm.reset();
        loadWebhooks();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function testWebhook(id) {
    try {
        const result = await apiRequest(`/webhooks/${id}/test`, { method: 'POST' });

        if (result.success) {
            showToast(`Webhook test successful (${result.status_code})`, 'success');
        } else {
            showToast(`Webhook test failed: ${result.error || result.status_code}`, 'error');
        }
    } catch (error) {
        showToast('Test failed', 'error');
    }
}

async function deleteWebhook(id) {
    if (!confirm('Are you sure you want to delete this webhook?')) return;

    try {
        await apiRequest(`/webhooks/${id}`, { method: 'DELETE' });
        showToast('Webhook deleted', 'success');
        loadWebhooks();
    } catch (error) {
        showToast('Failed to delete webhook', 'error');
    }
}

// ===== API Key =====
async function generateNewApiKey() {
    if (!confirm('A new API key will be created. The old one will be invalid. Continue?')) return;

    try {
        const result = await apiRequest('/auth/api-key', { method: 'POST' });
        document.querySelector('#apiKeyDisplay code').textContent = result.api_key;
        showToast('New API key created!', 'success');
    } catch (error) {
        showToast('Failed to create API key', 'error');
    }
}

// ===== Theme =====
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    elements.themeToggle.textContent = newTheme === 'light' ? '🌙' : '☀️';
}

// ===== Event Listeners =====
function initEventListeners() {
    // Navigation
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(item.dataset.page);
        });
    });

    // Mobile menu
    elements.menuToggle.addEventListener('click', () => {
        elements.sidebar.classList.toggle('open');
    });

    // Theme
    elements.themeToggle.addEventListener('click', toggleTheme);

    // Auth
    elements.authBtn.addEventListener('click', () => {
        if (!authToken) openModal(elements.authModal);
        else logout();
    });

    elements.closeAuthModal.addEventListener('click', () => closeModal(elements.authModal));
    elements.authSwitchLink.addEventListener('click', (e) => {
        e.preventDefault();
        toggleAuthMode();
    });

    elements.authForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        try {
            if (isLoginMode) {
                await login(elements.authEmail.value, elements.authPassword.value);
            } else {
                await register(elements.authEmail.value, elements.authUsername.value, elements.authPassword.value);
            }
            closeModal(elements.authModal);
            elements.authForm.reset();
            navigateTo('dashboard');
        } catch (error) {
            showToast(error.message, 'error');
        }
    });

    // Upload
    elements.uploadZone.addEventListener('click', (e) => {
        if (e.target !== e.currentTarget) return;
        openFileDialog(elements.fileInput, 'upload');
    });
    elements.uploadSelectBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openFileDialog(elements.fileInput, 'upload');
    });
    elements.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.add('dragover');
    });
    elements.uploadZone.addEventListener('dragleave', () => {
        elements.uploadZone.classList.remove('dragover');
    });
    elements.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]);
    });
    elements.fileInput.addEventListener('change', (e) => {
        dialogLocks.upload = false;
        if (e.target.files[0]) handleFileUpload(e.target.files[0]);
    });
    elements.uploadAnother.addEventListener('click', () => {
        elements.uploadZone.classList.remove('hidden');
        elements.uploadResult.classList.add('hidden');
        elements.progressFill.style.width = '0%';
        elements.progressFill.style.background = '';
    });

    // Filters
    elements.applyFilters.addEventListener('click', () => loadInvoices(1));

    // Export
    elements.exportCsv.addEventListener('click', () => exportInvoices('csv'));
    elements.exportExcel.addEventListener('click', () => exportInvoices('excel'));

    // Batch
    elements.batchUploadZone.addEventListener('click', (e) => {
        if (e.target !== e.currentTarget) return;
        openFileDialog(elements.batchFileInput, 'batch');
    });
    elements.batchSelectBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openFileDialog(elements.batchFileInput, 'batch');
    });
    elements.batchFileInput.addEventListener('change', (e) => {
        dialogLocks.batch = false;
        handleBatchFiles(e.target.files);
    });
    elements.clearQueue.addEventListener('click', () => {
        batchFiles = [];
        elements.batchQueue.classList.add('hidden');
    });
    elements.startBatch.addEventListener('click', startBatchUpload);

    // Webhooks
    elements.addWebhook.addEventListener('click', () => openModal(elements.webhookModal));
    elements.closeWebhookModal.addEventListener('click', () => closeModal(elements.webhookModal));
    elements.webhookForm.addEventListener('submit', (e) => {
        e.preventDefault();
        createWebhook();
    });

    // Invoice Modal
    elements.closeInvoiceModal.addEventListener('click', () => closeModal(elements.invoiceModal));

    // Settings
    elements.generateApiKey.addEventListener('click', generateNewApiKey);
    elements.logoutBtn.addEventListener('click', logout);

    // Modal backdrops
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', () => {
            closeModal(backdrop.closest('.modal'));
        });
    });

    // Reset dialog locks when file picker closes without selection
    window.addEventListener('focus', () => {
        dialogLocks.upload = false;
        dialogLocks.batch = false;
    });
}

// ===== Initialize =====
async function init() {
    // Load theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    elements.themeToggle.textContent = savedTheme === 'light' ? '🌙' : '☀️';

    // Init event listeners
    initEventListeners();

    // Load user if token exists
    await loadCurrentUser();

    // Load dashboard
    navigateTo('dashboard');
}

// Start app
init();

// Make functions available globally for inline handlers
window.viewInvoice = viewInvoice;
window.deleteInvoice = deleteInvoice;
window.loadInvoices = loadInvoices;
window.removeBatchFile = removeBatchFile;
window.testWebhook = testWebhook;
window.deleteWebhook = deleteWebhook;
