
 let authWindow;

 function login() {
    const selfUrl = window.location.href;
    authWindow = window.open('/auth/linuxdo?self=' + encodeURIComponent(selfUrl), 'OAuth', 'width=600,height=400');
    checkAuthWindow();
 }

 // Function to show the API key section without storing token locally
 function showApiKeySection(apiKey) {
    const apiKeyMaskedInput = document.getElementById('api_key_masked');
    const apiKeyInput = document.getElementById('api_key');
    const loginButton = document.getElementById('login_btn');
    if (apiKey) {
        apiKeyInput.value = apiKey;
        apiKeyMaskedInput.value = apiKey; // Directly show the API key
        document.getElementById('reset_btn').style.display = 'inline-block';
        if (loginButton) {
            loginButton.style.display = 'none';
        }
    } else {
        apiKeyMaskedInput.value = '';
        apiKeyInput.value = '';
        document.getElementById('reset_btn').style.display = 'none';
        if (loginButton) {
            loginButton.style.display = 'inline-block';
        }
    }
 }

 // Helper function to show a toast message
 function showToast(message) {
    const toast = document.createElement('div');
    toast.innerText = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    toast.style.color = 'white';
    toast.style.padding = '10px 20px';
    toast.style.borderRadius = '4px';
    toast.style.zIndex = 9999;
    document.body.appendChild(toast);
    setTimeout(() => {
        document.body.removeChild(toast);
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

 function resetApiKey() {
    fetch('/auth/reset', { 
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + document.getElementById('api_key').value
      }
    })
    .then(response => response.json())
    .then(data => {
        if (data.apiKey) {
            showApiKeySection(data.apiKey);
            localStorage.setItem('apiKey', data.apiKey); // Store API Key
        } else {
           console.error('Reset error:', data || 'API 密钥重置失败');
            showToast(data.detail || 'API 密钥重置失败');
        }
    })
    .catch(error => {
        console.error('Reset error:', error)
     }
  );
 }

 // Function to parse query parameters from the URL
 function getQueryParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
 }

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
      // console.log('Received message:', event.data);
        showApiKeySection(event.data.apiKey);
        localStorage.setItem('oauthToken', event.data.oauth_token); // Store OAuth Token
        localStorage.setItem('apiKey', event.data.apiKey); // Store API Key
        if (authWindow && !authWindow.closed) {
            authWindow.close();
        }
    } else if (event.data.error) {
        showToast(event.data.error);
        if (authWindow && !authWindow.closed) {
            authWindow.close();
        }
    }
 });

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
