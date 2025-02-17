// Global variables and state
let originalUsers = [];
let currentSort = { field: null, direction: 'asc' };
let currentPage = 1;
const itemsPerPage = 10;
let authWindow;

const usersTable = document.getElementById('users-table').getElementsByTagName('tbody')[0];
const adminPanel = document.getElementById('admin-panel');
const loginButtonContainer = document.getElementById('login-button-container');
const loginButton = document.getElementById('login-button');

// Core API functions
async function fetchData(url, options = {}) {
    const token = localStorage.getItem('adminOAuthToken');
    if (!token) {
        updateVisibility(false);
        return;
    }

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };

    const response = await fetch(url, { ...options, headers });
    const data = await response.json();
        
    if (!response.ok) {
        throw new Error(data.detail || '操作失败');
    }

    return data;
}

// UI State Management
function showLoading() {
    const existingOverlay = document.querySelector('.loading-overlay');
    if (existingOverlay) return;

    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay active';
    loadingOverlay.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">加载中...</div>
    `;
    
    const tableContainer = document.querySelector('.table-container');
    if (tableContainer) {
        tableContainer.appendChild(loadingOverlay);
    }
}

function hideLoading() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

function showToast(message, type = 'info') {
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    const delay = 3000;
    setTimeout(() => {
        toast.classList.add('fadeOut');
        setTimeout(() => toast.remove(), 300);
    }, delay);
}

// Data Management
async function displayUsers() {
    try {
        showLoading();
        
        // Build query parameters
        const params = new URLSearchParams();
        
        // Add search parameter
        const searchInput = document.getElementById('userSearch');
        if (searchInput && searchInput.value) {
            params.append('search', searchInput.value);
        }

        // Add status filter
        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter && statusFilter.value && statusFilter.value !== 'all') {
            params.append('status', statusFilter.value);
        }

        // Add admin filter
        const adminFilter = document.getElementById('adminFilter');
        if (adminFilter && adminFilter.value && adminFilter.value !== 'all') {
            params.append('admin_filter', adminFilter.value);
        }

        // Add sorting parameters
        if (currentSort.field) {
            params.append('sort_by', currentSort.field);
            params.append('sort_dir', currentSort.direction);
        }

        const data = await fetchData(`/api/users?${params.toString()}`);
        originalUsers = data.users;
        
        // Update sort indicators after getting new data
        document.querySelectorAll('th.sortable').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (header.dataset.sort === currentSort.field) {
                header.classList.add(`sort-${currentSort.direction}`);
            }
        });
        
        renderUsers(originalUsers);
        updatePagination(originalUsers.length);
    } catch (error) {
        console.error('获取用户失败:', error);
        showToast(error.message, 'error');
        
        if (error.message.includes('已被禁用') || error.message.includes('权限不足')) {
            showToast('您的账号已被禁用或权限不足，即将退出登录');
            setTimeout(() => {
                localStorage.clear();
                window.location.href = '/';
            }, 2000);
            return;
        }
    } finally {
        hideLoading();
    }
}

// User Actions
async function toggleAdmin(userId, isAdmin) {
    try {
        showLoading();
        const response = await fetchData(`/api/admin/toggle-admin/${userId}`, {
            method: 'POST',
            body: JSON.stringify({ is_admin: isAdmin })
        });
        showToast(response.message);
        await displayUsers();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function enableUser(userId) {
    try {
        showLoading();
        const response = await fetchData(`/api/admin/enable/${userId}`, {
            method: 'POST'
        });
        showToast(response.message);
        await displayUsers();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function resetApiKey(userId) {
    try {
        showLoading();
        const response = await fetchData(`/api/admin/reset-key/${userId}`, {
            method: 'POST'
        });
        showToast(response.message);
        await displayUsers();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function submitDisable() {
    const userId = document.getElementById('userToDisable').value;
    const commonReasons = document.getElementById('commonReasons');
    const disableReason = document.getElementById('disableReason');
    
    let reason = commonReasons.value === 'custom' ? disableReason.value : commonReasons.value;
    reason = reason.trim();
    
    if (!reason) {
        showToast('请输入或选择禁用原因', 'error');
        return;
    }

    try {
        showLoading();
        const response = await fetchData(`/api/admin/disable/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason: reason })
        });

        closeModal();
        showToast(response.message);
        await displayUsers(); // This will handle logout if user disabled themselves
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Authentication Functions
function updateVisibility(isLoggedIn) {
    adminPanel.style.display = isLoggedIn ? 'block' : 'none';
    loginButtonContainer.style.display = isLoggedIn ? 'none' : 'block';
}

function login() {
    const selfUrl = window.location.href;
    authWindow = window.open('/auth/linuxdo?self=' + encodeURIComponent(selfUrl), 'OAuth', 'width=600,height=400');
    checkAuthWindow();
}

function checkAuthWindow() {
    if (authWindow && !authWindow.closed) {
        setTimeout(() => {
            if (authWindow && !authWindow.closed) {
                authWindow.close();
                showToast("登录超时 - 请重试");
            }
        }, 120000);
    }
}

// Immediately check if we're on the login page and initialize the login button
if (document.querySelector('.login-page')) {
    document.getElementById('login-button').addEventListener('click', function() {
        const width = 600;
        const height = 700;
        const left = (window.innerWidth - width) / 2;
        const top = (window.innerHeight - height) / 2;
        const loginWindow = window.open(
            '/auth/linuxdo',
            'Login',
            `width=${width},height=${height},left=${left},top=${top}`
        );

        window.addEventListener('message', function(event) {
            if (event.origin !== window.location.origin) return;
            
            if (event.data.error) {
                alert('登录失败：' + event.data.error);
                return;
            }

            if (event.data.oauth_token) {
                localStorage.setItem('oauth_token', event.data.oauth_token);
                window.location.href = '/admin';
            }
        }, false);
    });
}

// Initialization
window.onload = () => {
    const adminToken = localStorage.getItem('adminOAuthToken');
    if (!adminToken) {
        updateVisibility(false);
        loginButton.addEventListener('click', login);
        return;
    }

    updateVisibility(true);
    displayUsers().catch(error => {
        console.error("Failed to load data:", error);
        localStorage.removeItem('adminOAuthToken');
        updateVisibility(false);
    });

    initializeTable();
    loginButton.addEventListener('click', login);
};

// Event Listeners
window.addEventListener('message', function(event) {
    if (event.origin !== window.location.origin || event.source !== authWindow) {
        return;
    }
    
    if (typeof event.data !== 'object' || (!event.data.apiKey && !event.data.oauth_token && !event.data.error)) {
        return;
    }

    if (event.data.oauth_token) {
        localStorage.setItem('adminOAuthToken', event.data.oauth_token);
        updateVisibility(true);
        displayUsers();
        if (authWindow && !authWindow.closed) {
            authWindow.close();
        }
        showToast('登录成功');
    } else if (event.data.error) {
        const errorMsg = event.data.error.includes('权限不足') 
            ? '登录失败：此账号没有管理员权限' 
            : event.data.error;
        showToast(errorMsg, 'error');
        if (authWindow && !authWindow.closed) {
            authWindow.close();
        }
    }
});

// Function to toggle user status
async function toggleUser(userId, currentStatus) {
    if (currentStatus) {
        // If user is enabled, show disable modal
        showDisableModal(userId);
    } else {
        // If user is disabled, enable directly
        try {
            const response = await fetch(`/api/admin/enable/${userId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('adminOAuthToken')}`
                }
            });
            if (response.ok) {
                showToast('用户已启用');
                displayUsers();
            } else {
                const data = await response.json();
                showToast(data.detail || '操作失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
}

function showDisableModal(userId) {
    const modal = document.getElementById('disableModal');
    const userToDisable = document.getElementById('userToDisable');
    const commonReasons = document.getElementById('commonReasons');
    const disableReason = document.getElementById('disableReason');
    
    modal.style.display = 'block';
    userToDisable.value = userId;
    commonReasons.value = '';
    disableReason.value = '';
    disableReason.style.display = 'none'; // Hide custom input initially
}

function updateReasonInput() {
    const commonReasons = document.getElementById('commonReasons');
    const disableReason = document.getElementById('disableReason');
    
    if (commonReasons.value === 'custom') {
        disableReason.style.display = 'block';
        disableReason.value = '';
        disableReason.focus();
    } else {
        disableReason.style.display = commonReasons.value ? 'none' : 'block';
        disableReason.value = commonReasons.value;
    }
}

// Add event listener to close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('disableModal');
    if (event.target === modal) {
        closeModal();
    }
}

function closeModal() {
    const modal = document.getElementById('disableModal');
    const disableReason = document.getElementById('disableReason');
    const commonReasons = document.getElementById('commonReasons');
    
    modal.style.display = 'none';
    disableReason.value = '';
    commonReasons.value = '';
}

async function renderUsers(users) {
    const tbody = document.querySelector('#users-table tbody');
    tbody.innerHTML = '';

    if (!users || users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="no-results">没有找到匹配的用户</td>
            </tr>
        `;
        return;
    }

    users.forEach(user => {
        const row = document.createElement('tr');
        if (!user.enabled) {
            row.classList.add('disabled-user');
            const tooltipText = user.disable_reason ? 
                              `禁用原因: ${user.disable_reason}` : 
                              '用户已被禁用';
            row.setAttribute('data-tooltip', tooltipText);
        }

        row.innerHTML = `
            <td>
                <span class="admin-star${user.is_admin ? ' active' : ''}" 
                      onclick="toggleAdmin(${user.user_id}, ${!user.is_admin})"
                      title="${user.is_admin ? '点击撤销管理员权限' : '点击赋予管理员权限'}">
                    ${user.is_admin ? '⭐' : '☆'}
                </span>
                ${user.username || '-'}
            </td>
            <td>${user.user_id}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>${user.last_used_at ? formatDate(user.last_used_at) : '-'}</td>
            <td class="dropdown">
                <button class="dropdown-btn">操作</button>
                <div class="dropdown-content">
                    <a href="#" onclick="resetApiKey(${user.user_id}); return false;">重置 API 密钥</a>
                    ${user.enabled ? 
                        `<a href="#" onclick="showDisableModal(${user.user_id}); return false;">禁用用户</a>` :
                        `<a href="#" onclick="enableUser(${user.user_id}); return false;">启用用户</a>`
                    }
                </div>
            </td>
        `;

        tbody.appendChild(row);
    });

    updatePagination(users.length);
}

async function toggleAdminStatus(userId, newStatus) {
    try {
        const response = await fetch(`/api/admin/toggle-admin/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getOAuthToken()}`
            },
            body: JSON.stringify({ is_admin: newStatus })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '操作失败');
        }

        // Refresh the user list to show updated status
        fetchUsers();
    } catch (error) {
        alert(error.message);
    }
}

function populateTable(users) {
    const tableBody = document.querySelector('#users-table tbody');
    tableBody.innerHTML = ''; // Clear existing rows

    users.forEach(user => {
        const row = tableBody.insertRow();

        // Add class and tooltip for disabled users
        if (!user.enabled) {
            row.classList.add('disabled-user');
            row.setAttribute('data-tooltip', user.disable_reason || '用户已被禁用');
        }

        row.insertCell().textContent = user.username;
        row.insertCell().textContent = user.user_id;
        row.insertCell().textContent = new Date(user.created_at).toLocaleString();
        row.insertCell().textContent = user.last_used_at ? new Date(user.last_used_at).toLocaleString() : 'N/A';

        // Create dropdown for actions
        const actionsCell = row.insertCell();
        actionsCell.className = 'dropdown';
        const dropdownBtn = document.createElement('button');
        dropdownBtn.className = 'dropdown-btn';
        dropdownBtn.textContent = '操作';
        actionsCell.appendChild(dropdownBtn);

        const dropdownContent = document.createElement('div');
        dropdownContent.className = 'dropdown-content';

        // Reset API Key action
        const resetKeyLink = document.createElement('a');
        resetKeyLink.href = '#';
        resetKeyLink.textContent = '重置 API 密钥';
        resetKeyLink.onclick = function() {
            resetApiKey(user.user_id);
            return false;
        };
        dropdownContent.appendChild(resetKeyLink);

        // Disable/Enable action
        const disableEnableLink = document.createElement('a');
        disableEnableLink.href = '#';
        disableEnableLink.textContent = user.enabled ? '禁用用户' : '启用用户';
        disableEnableLink.onclick = function() {
            if (user.enabled) {
                openDisableModal(user.user_id);
            } else {
                enableUser(user.user_id);
            }
            return false;
        };
        dropdownContent.appendChild(disableEnableLink);

        // Toggle Admin action
        const toggleAdminLink = document.createElement('a');
        toggleAdminLink.href = '#';
        toggleAdminLink.textContent = user.is_admin ? '撤销管理员权限' : '赋予管理员权限';
        toggleAdminLink.onclick = function() {
            toggleAdmin(user.user_id, !user.is_admin);
            return false;
        };
        dropdownContent.appendChild(toggleAdminLink);

        actionsCell.appendChild(dropdownContent);
    });
}

function sortData(field) {
    const headers = document.querySelectorAll('th.sortable');
    headers.forEach(header => {
        if (header.dataset.sort === field) {
            // If clicking same field, toggle direction
            if (currentSort.field === field) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                // If clicking new field, set to asc and remove other indicators
                currentSort.field = field;
                currentSort.direction = 'asc';
                headers.forEach(h => {
                    if (h !== header) {
                        h.classList.remove('sort-asc', 'sort-desc');
                    }
                });
            }
            
            // Update current header's indicator
            header.classList.remove('sort-asc', 'sort-desc');
            header.classList.add(`sort-${currentSort.direction}`);
        }
    });

    displayUsers();
}

function filterData() {
    displayUsers();
}

function updatePagination(totalItems) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    document.getElementById('currentPage').textContent = currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    document.getElementById('totalItems').textContent = totalItems;
    
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;
}

// Initialize sort and pagination events
document.addEventListener('DOMContentLoaded', () => {
    // Add click events for sorting
    document.querySelectorAll('th.sortable').forEach(header => {
        header.addEventListener('click', () => {
            sortData(header.dataset.sort);
        });
    });

    // Add pagination events
    const prevButton = document.getElementById('prevPage');
    const nextButton = document.getElementById('nextPage');

    if (prevButton) {
        prevButton.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                filterAndSortData();
            }
        });
    }

    if (nextButton) {
        nextButton.addEventListener('click', () => {
            const totalPages = Math.ceil(originalUsers.length / itemsPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                filterAndSortData();
            }
        });
    }
});

// Utility function to format dates
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function initializeTable() {
    // Add sort listeners
    document.querySelectorAll('th.sortable').forEach(header => {
        // Remove old click listeners first to prevent duplicates
        header.removeEventListener('click', () => sortData(header.dataset.sort));
        header.addEventListener('click', () => sortData(header.dataset.sort));
    });

    // Safely add filter listeners
    const searchInput = document.getElementById('userSearch');
    const statusFilter = document.getElementById('statusFilter');
    const adminFilter = document.getElementById('adminFilter');

    if (searchInput) {
        searchInput.addEventListener('input', filterData);
    }
    if (statusFilter) {
        statusFilter.addEventListener('change', filterData);
    }
    if (adminFilter) {
        adminFilter.addEventListener('change', filterData);
    }
}
