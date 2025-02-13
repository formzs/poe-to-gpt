async function fetchData(url, options = {}) {
    const token = localStorage.getItem('oauthToken');
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };

    const config = {
        ...options,
        headers: headers
    };

    const response = await fetch(url, config);
    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || '未知错误');
    }
    return await response.json();
}

async function toggleUserStatus(userId) {
    return fetchData(`/api/users/${userId}/toggle`, {
        method: 'POST'
    });
}

async function fetchUsers() {
    return fetchData('/api/users');
}

const usersTable = document.getElementById('users-table').getElementsByTagName('tbody')[0];
const adminPanel = document.getElementById('admin-panel');
const loginButtonContainer = document.getElementById('login-button-container');
const loginButton = document.getElementById('login-button');

let authWindow;

// Simplified toast function
function showToast(message) {
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fadeOut');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Function to fetch and display users
async function displayUsers() {
    const oauthToken = localStorage.getItem('oauthToken');
    try {
        const data = await fetchUsers();
        usersTable.innerHTML = ''; // Clear existing data
        data.users.forEach(user => {
            let row = usersTable.insertRow();
            row.classList.toggle('disabled-user', !user.enabled);

            let usernameCell = row.insertCell(0);
            let userIdCell = row.insertCell(1);
            let createdAtCell = row.insertCell(2);
            let lastUsedAtCell = row.insertCell(3);
            let actionsCell = row.insertCell(4);

            // Include admin star in username cell
            usernameCell.innerHTML = `${user.is_admin ? '<span class="admin-star">★</span> ' : ''}${user.username}`;
            userIdCell.textContent = user.user_id;

            // Format dates consistently
            const dateTimeFormat = new Intl.DateTimeFormat('zh-CN', { // Adjust locale as needed
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: 'numeric',
                second: 'numeric'
            });

            let createdAt = 'N/A';
            if (user.created_at && !isNaN(new Date(user.created_at))) {
                createdAt = dateTimeFormat.format(new Date(user.created_at));
            }
            createdAtCell.textContent = createdAt;

            let lastUsedAt = 'N/A';
            if (user.last_used_at && !isNaN(new Date(user.last_used_at))) {
                lastUsedAt = dateTimeFormat.format(new Date(user.last_used_at));
            }
            lastUsedAtCell.textContent = lastUsedAt;

            // Create action dropdown menu
            let actionMenu = document.createElement('div');
            actionMenu.className = 'dropdown';
            actionMenu.innerHTML = `
                <button class="dropdown-btn">操作</button>
                <ul class="dropdown-content" id="dropdown-${user.user_id}">
                    <li><a href="#" data-action="toggleEnable">${user.enabled ? '禁用' : '启用'}</a></li>
                    <li><a href="#" data-action="resetApiKey">重置密钥</a></li>
                    <li><a href="#" data-action="toggleAdmin">${user.is_admin ? '取消管理员' : '设为管理员'}</a></li>
                </ul>
            `;
            actionsCell.appendChild(actionMenu);

            // Add click handlers for dropdown items
            const dropdownContent = actionMenu.querySelector('.dropdown-content');
            dropdownContent.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const action = e.target.dataset.action;
                if (!action) return;

                try {
                    switch (action) {
                        case 'toggleEnable':
                            await toggleUser(user.user_id);
                            break;
                        case 'resetApiKey':
                            await resetApiKey(user.user_id);
                            break;
                        case 'toggleAdmin':
                            await toggleAdmin(user.user_id, !user.is_admin);
                            break;
                    }
                } catch (error) {
                    showToast(error.message);
                }
            });
        });

        // Add global click handler to close dropdowns
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('.dropdown-content').forEach(content => {
                    content.style.display = 'none';
                });
            }
        });
    } catch (error) {
        console.error('获取用户失败:', error);
        if (error.message.includes('权限不足')) {
            showToast('权限不足：您需要管理员权限访问此页面');
            updateVisibility(false);  // Hide admin panel
        } else {
            showToast('获取用户失败: ' + error.message);
        }
    }
}

// Function to toggle user status
async function toggleUser(userId) {
    const oauthToken = localStorage.getItem('oauthToken');
    try {
        const data = await toggleUserStatus(userId, {
            headers: {
                'Authorization': `Bearer ${oauthToken}`
            }
        });
        if (data.success) {
            displayUsers(); // Refresh user list
            showToast('用户状态已更新');
        } else {
            showToast('切换用户状态失败');
        }
    } catch (error) {
        console.error('切换用户状态失败:', error);
        showToast(error.message.includes('权限不足')
            ? '权限不足：只有管理员可以启用/禁用用户'
            : '切换用户状态失败: ' + error.message);
    }
}

async function toggleAdmin(userId, isAdmin) {
    try {
        const response = await fetchData(`/api/admin/toggle-admin/${userId}`, {
            method: 'POST',
            body: JSON.stringify({ is_admin: isAdmin })
        });
        if (response.success) {
            showToast('管理员状态已更新');
        }
    } catch (error) {
        console.error('更新管理员状态失败:', error);
        showToast(error.message.includes('权限不足') 
            ? '权限不足：只有管理员可以修改管理员状态' 
            : '更新失败: ' + error.message);
        // Revert checkbox state
        const checkbox = document.querySelector(`#admin-${userId}`);
        if (checkbox) checkbox.checked = !isAdmin;
    }
}

function updateVisibility(isLoggedIn) {
    if (isLoggedIn) {
        adminPanel.style.display = 'block';
        loginButtonContainer.style.display = 'none';
    } else {
        adminPanel.style.display = 'none';
        loginButtonContainer.style.display = 'block';
    }
}

function login() {
    const selfUrl = window.location.href;
    authWindow = window.open('/auth/linuxdo?self=' + encodeURIComponent(selfUrl), 'OAuth', 'width=600,height=400');
    checkAuthWindow();
}

// Add window check function
function checkAuthWindow() {
    if (authWindow && !authWindow.closed) {
        // If window is still open after 2 minutes, close it
        setTimeout(() => {
            if (authWindow && !authWindow.closed) {
                authWindow.close();
                showToast("登录超时 - 请重试");  // Removed warning type
            }
        }, 120000);
    }
}

// Load data on page load
window.onload = () => {
    const oauthToken = localStorage.getItem('oauthToken');
    if (!oauthToken) {
        updateVisibility(false);
        loginButton.addEventListener('click', () => {
            login();
        });
        return;
    }

    updateVisibility(true);
    displayUsers()
        .catch(error => {
            console.error("Failed to load data:", error);
            updateVisibility(false);
        });

    loginButton.addEventListener('click', () => {
        login();
    });
};

// Improved window message handling with stricter source verification
window.addEventListener('message', function(event) {
    // Check event origin and ensure the message is from the opened authWindow
    if (event.origin !== window.location.origin || event.source !== authWindow) {
        return;
    }
    // Check that event.data is an object with expected properties
    if (typeof event.data !== 'object' || (!event.data.apiKey && !event.data.oauth_token && !event.data.error)) {
        return;
    }

    if (event.data.apiKey && event.data.oauth_token) {
        localStorage.setItem('oauthToken', event.data.oauth_token); // Store OAuth Token
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
        showToast(errorMsg);
        if (authWindow && !authWindow.closed) {
            authWindow.close();
        }
    }
});
