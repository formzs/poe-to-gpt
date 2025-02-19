let authWindow;

function updateVisibility(apiKey = '') {
    const apiKeyInput = document.getElementById('apikey');
    const apiKeyMasked = document.getElementById('apikey-masked');
    const apiKeySection = document.getElementById('apikey-section');
    const loginBtn = document.getElementById('login-button');
    const resetBtn = document.getElementById('reset-button');

    if (apiKey) {
        apiKeyInput.value = apiKey;  // Store full key in hidden input
        // Remove old event listeners first
        const oldMasked = apiKeyMasked.cloneNode(true);
        apiKeyMasked.parentNode.replaceChild(oldMasked, apiKeyMasked);
        
        // Create masking function
        const setMasked = () => {
            oldMasked.value = apiKey.slice(0, 6) + '•'.repeat(apiKey.length - 12) + apiKey.slice(-6);
        };
        const setFull = () => {
            oldMasked.value = apiKey;
        };
        
        // Set initial masked value
        setMasked();
        
        // Add hover events
        oldMasked.addEventListener('mouseenter', setFull);
        oldMasked.addEventListener('mouseleave', setMasked);
        
        // Add click-to-copy
        oldMasked.addEventListener('click', () => {
            navigator.clipboard.writeText(apiKey).then(() => {
                showToast("完整 API 密钥已复制到剪贴板！");
            }, () => {
                showToast("复制失败，请手动复制。");
            });
        });
        
        apiKeySection.classList.remove('hidden');
        loginBtn.classList.add('hidden');
        resetBtn.classList.remove('hidden');
    } else {
        apiKeyInput.value = '';
        apiKeyMasked.value = '';
        apiKeySection.classList.add('hidden');
        loginBtn.classList.remove('hidden');
        resetBtn.classList.add('hidden');
    }
}

function updateTitleAndHeading(isLoggedIn) {
    const pageTitle = document.getElementById('page-title');
    if (isLoggedIn) {
        document.title = '阿康poe转接 - API密钥管理';
        pageTitle.textContent = '阿康poe转接 - API密钥管理';
    } else {
        document.title = '阿康poe转接';
        pageTitle.textContent = '登录阿康poe转接';
    }
}

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
                document.getElementById('apikey').value = data.apiKey;
                document.getElementById('apikey-masked').value = data.apiKey;
                document.getElementById('reset-button').style.display = 'block';
                document.getElementById('login-button').style.display = 'none';
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
                'Authorization': `Bearer ${document.getElementById('apikey').value}`
            }
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || '重置密钥失败');
        }

        updateVisibility(data.apiKey);
    } catch (error) {
        console.error('Error resetting API key:', error);
        showToast(error.message || '重置密钥失败', 'error');
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

// Initialize event handlers
document.addEventListener('DOMContentLoaded', () => {
    // Remove stored tokens
    sessionStorage.removeItem('oauthToken');
    
    // Setup login button
    const loginBtn = document.getElementById('login-button');
    if (loginBtn) {
        loginBtn.disabled = false;  // Enable button
        loginBtn.addEventListener('click', () => handleLogin());
    }

    // Setup API key click-to-copy
    const apiKeyMaskedInput = document.getElementById('apikey-masked');
    if (apiKeyMaskedInput) {
        apiKeyMaskedInput.addEventListener('click', function() {
            const fullKey = document.getElementById('apikey').value;  // Get full key from hidden input
            if (fullKey) {
                navigator.clipboard.writeText(fullKey).then(function() {
                    showToast("完整 API 密钥已复制到剪贴板！");
                }, function() {
                    showToast("复制失败，请手动复制。");
                });
            }
        });
    }

    // Check existing API key
    const apiKey = document.getElementById('apikey').value;
    if (apiKey) {
        document.getElementById('apikey-masked').value = apiKey;
        document.getElementById('reset-button').style.display = 'block';
        document.getElementById('login-button').style.display = 'none';
    }

    // Initial visibility update
    updateVisibility();

    // Update titles based on initial state
    updateTitleAndHeading(!!apiKey);
});

function handleLogin() {
    const width = 600;
    const height = 600;
    const left = (screen.width / 2) - (width / 2);
    const top = (screen.height / 2) - (height / 2);
    
    const loginWindow = window.open(
        '/auth/linuxdo',
        'Login',
        `width=${width},height=${height},left=${left},top=${top}`
    );

    const messageHandler = async (event) => {
        if (event.origin !== window.location.origin) return;
        
        const data = event.data;
        if (data.error) {
            loginWindow.close();
            // Show only the error message without status code
            const errorMsg = data.error.includes(':') ? 
                data.error.split(':')[1].trim() : 
                data.error;
            showToast(errorMsg, 'error');
            return;
        }

        if (data.oauth_token && data.apiKey) {
            loginWindow.close();
            localStorage.setItem('oauth_token', data.oauth_token);
            document.getElementById('apikey').value = data.apiKey;  // Store full key
            document.getElementById('apikey-section').style.display = 'block';
            updateVisibility(data.apiKey);  // This will handle the masking
            updateTitleAndHeading(true);
            showToast('登录成功！', 'success');
        }
    };

    window.addEventListener('message', messageHandler);

    const checkClosed = setInterval(() => {
        if (loginWindow.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', messageHandler);
        }
    }, 1000);
}
