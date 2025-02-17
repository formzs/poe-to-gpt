let authWindow;

function updateVisibility(apiKey = '') {
    const apiKeyInput = document.getElementById('api_key');
    const apiKeyMasked = document.getElementById('api_key_masked');
    const loginBtn = document.getElementById('login_btn');
    const resetBtn = document.getElementById('reset_btn');

    if (apiKey) {
        apiKeyInput.value = apiKey;
        apiKeyMasked.value = apiKey; // Show full API key instead of masked version
        loginBtn.style.display = 'none';
        resetBtn.style.display = 'block';
    } else {
        apiKeyInput.value = '';
        apiKeyMasked.value = '';
        loginBtn.style.display = 'block';
        resetBtn.style.display = 'none';
    }
}

// Remove any stored tokens on page load
window.onload = () => {
    sessionStorage.removeItem('oauthToken');
    updateVisibility();
};

// Function to handle login
function login() {
    const width = 600;
    const height = 700;
    const left = (window.screen.width / 2) - (width / 2);
    const top = (window.screen.height / 2) - (height / 2);
    authWindow = window.open('/auth/linuxdo', 'Login', 
        `width=${width},height=${height},left=${left},top=${top}`);

    window.addEventListener('message', function(event) {
        if (event.origin === window.location.origin) {
            const data = event.data;
            
            if (data.error) {
                showToast(data.error);
                return;
            }
            
            if (data.apiKey) {
                document.getElementById('api_key').value = data.apiKey;
                document.getElementById('api_key_masked').value = data.apiKey;
                document.getElementById('reset_btn').style.display = 'block';
                document.getElementById('login_btn').style.display = 'none';
                showToast('登录成功！');
            }
        }
    });
}

// Function to handle API key reset
async function resetApiKey() {
    try {
        const response = await fetch('/auth/reset', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${document.getElementById('api_key').value}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to reset API key');
        }

        const data = await response.json();
        updateVisibility(data.apiKey);
    } catch (error) {
        console.error('Error resetting API key:', error);
        showToast('Failed to reset API key');
    }
}

// Handle OAuth callback
window.addEventListener('message', function(event) {
    if (event.origin !== window.location.origin || event.source !== authWindow) {
        return;
    }

    if (event.data.apiKey) {
        updateVisibility(event.data.apiKey);
        if (authWindow) {
            authWindow.close();
        }
    } else if (event.data.error) {
        showToast(event.data.error);
        if (authWindow) {
            authWindow.close();
        }
    }
});

// Helper function to show a toast message
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = message;
    
    if (type === 'error') {
        toast.style.backgroundColor = '#dc3545';
    } else if (type === 'success') {
        toast.style.backgroundColor = '#28a745';
    } else {
        toast.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    }
    
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fadeOut');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add click listener to copy API key to clipboard using toast notifications
document.addEventListener("DOMContentLoaded", function() {
    const apiKeyMaskedInput = document.getElementById('api_key_masked');
    if (apiKeyMaskedInput) {
        apiKeyMaskedInput.addEventListener('click', function() {
            const key = this.value;
            if (key) {
                navigator.clipboard.writeText(key).then(function() {
                    showToast("API 密钥已复制到剪贴板！");
                }, function() {
                    showToast("复制失败，请手动复制。");
                });
            }
        });
    }
});

// Function to parse query parameters from the URL
function getQueryParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Add window check function
function checkAuthWindow() {
    if (authWindow && !authWindow.closed) {
        // If window is still open after 2 minutes, close it
        setTimeout(() => {
            if (authWindow && !authWindow.closed) {
                authWindow.close();
                showToast("Login timeout - please try again");
            }
        }, 120000);
    }
}

// Check if user is already logged in
document.addEventListener('DOMContentLoaded', function() {
    const apiKey = document.getElementById('api_key').value;
    if (apiKey) {
        document.getElementById('api_key_masked').value = apiKey;
        document.getElementById('reset_btn').style.display = 'block';
        document.getElementById('login_btn').style.display = 'none';
    }
});
