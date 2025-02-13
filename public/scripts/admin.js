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
            let usernameCell = row.insertCell(0);
            let userIdCell = row.insertCell(1);
            let enabledCell = row.insertCell(2);
            let adminCell = row.insertCell(3);
            let reasonCell = row.insertCell(4);  // Add reason cell
            let actionsCell = row.insertCell(5);  // Move actions to last column

            usernameCell.textContent = user.username;
            userIdCell.textContent = user.user_id;
            
            // Enabled status checkbox
            enabledCell.innerHTML = `
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="enabled-${user.user_id}" 
                           ${user.enabled ? 'checked' : ''}>
                    <label for="enabled-${user.user_id}"></label>
                </div>`;
            
            // Admin status checkbox
            adminCell.innerHTML = `
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="admin-${user.user_id}" 
                           ${user.is_admin ? 'checked' : ''}>
                    <label for="admin-${user.user_id}"></label>
                </div>`;

            // Add disable reason (if any)
            reasonCell.textContent = user.disable_reason || '-';
            if (!user.enabled && user.disable_reason) {
                reasonCell.style.color = '#dc3545';  // Red color for disabled reason
            }

            // Add event listeners
            enabledCell.querySelector('input').addEventListener('change', async (e) => {
                await toggleUser(user.user_id);
            });

            adminCell.querySelector('input').addEventListener('change', async (e) => {
                await toggleAdmin(user.user_id, e.target.checked);
            });

            let resetButton = document.createElement('button');
            resetButton.textContent = '重置密钥';
            resetButton.onclick = async () => {
                await resetApiKey(user.user_id);
            };
            actionsCell.appendChild(resetButton);
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
