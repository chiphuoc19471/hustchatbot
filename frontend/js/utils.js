// js/utils.js
function showLoading(btn) {
    btn.disabled = true;
    btn.textContent = 'Đang xử lý...';
}

function hideLoading(btn, originalText) {
    btn.disabled = false;
    btn.textContent = originalText;
}

function displayError(element, message) {
    if (element) {
        element.textContent = message;
        element.classList.remove('hidden');
    }
    console.error(message);
}

function clearError(element) {
    if (element) element.classList.add('hidden');
}
