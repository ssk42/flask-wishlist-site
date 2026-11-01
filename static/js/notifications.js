// Notification mark-read: clicking a notification fires a
// fire-and-forget read receipt, then navigation proceeds. The target
// URL arrives per notification as a data attribute. External because
// the production CSP blocks inline handlers (@spec GIV-CLM-021).
document.querySelectorAll('[data-mark-read-url]').forEach(function (el) {
    el.addEventListener('click', function () {
        const markReadUrl = el.dataset.markReadUrl;
        try {
            navigator.sendBeacon(markReadUrl);
        } catch (e) {
            // Fallback for older browsers
            fetch(markReadUrl, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
        }
    });
});
