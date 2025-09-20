// Main JavaScript file for the Fake Certificate Recognition System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    initializePage();
    
    // Add event listeners
    addEventListeners();
});

function initializePage() {
    // Check for flash messages and auto-hide them after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 300);
        }, 5000);
    });
}

function addEventListeners() {
    // Close alert buttons
    document.querySelectorAll('.close-alert').forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="close-alert" onclick="this.parentElement.remove()">×</button>
    `;
    
    const flashContainer = document.querySelector('.flash-messages') || createFlashContainer();
    flashContainer.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    document.querySelector('.main-content').prepend(container);
    return container;
}

// API Helper Functions
function apiRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaultOptions, ...options };
    
    return fetch(url, config)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('API request failed:', error);
            throw error;
        });
}

// Certificate verification function
function verifyCertificate(certificateId) {
    return apiRequest(`/verify/${certificateId}`)
        .then(data => {
            if (data.success) {
                return data;
            } else {
                throw new Error(data.message || 'Verification failed');
            }
        });
}

// Admin dashboard functions
function refreshAdminData() {
    location.reload();
}

function exportData(format = 'json') {
    // This would implement data export functionality
    showNotification('Export functionality not implemented yet', 'warning');
}

// Form validation
function validateFile(file) {
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/tiff', 'image/bmp', 'application/pdf'];
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    if (!allowedTypes.includes(file.type)) {
        throw new Error('Invalid file type. Please upload PNG, JPG, JPEG, PDF, TIFF, or BMP files.');
    }
    
    if (file.size > maxSize) {
        throw new Error('File size too large. Maximum size is 10MB.');
    }
    
    return true;
}

// Security functions
function sanitizeInput(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Progress tracking
class ProgressTracker {
    constructor(element) {
        this.element = element;
        this.progress = 0;
    }
    
    update(progress, message = '') {
        this.progress = Math.min(100, Math.max(0, progress));
        if (this.element) {
            const progressBar = this.element.querySelector('.progress-bar');
            const progressText = this.element.querySelector('.progress-text');
            
            if (progressBar) {
                progressBar.style.width = `${this.progress}%`;
            }
            
            if (progressText && message) {
                progressText.textContent = message;
            }
        }
    }
    
    complete(message = 'Complete!') {
        this.update(100, message);
        setTimeout(() => {
            if (this.element) {
                this.element.style.display = 'none';
            }
        }, 1000);
    }
    
    error(message = 'Error occurred') {
        if (this.element) {
            this.element.classList.add('error');
            const progressText = this.element.querySelector('.progress-text');
            if (progressText) {
                progressText.textContent = message;
            }
        }
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for quick search (if implemented)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // Quick search functionality would go here
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'block') {
                modal.style.display = 'none';
            }
        });
    }
});

// Performance monitoring
function trackPageLoad() {
    window.addEventListener('load', function() {
        const loadTime = performance.now();
        console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
    });
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    // In production, you might want to send this to a logging service
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    // In production, you might want to send this to a logging service
});

// Initialize performance tracking
trackPageLoad();

// Export functions for use in other scripts
window.CertificateApp = {
    verifyCertificate,
    showNotification,
    validateFile,
    formatFileSize,
    formatDate,
    sanitizeInput,
    escapeHtml,
    ProgressTracker,
    apiRequest
};