// Service worker registration. External because the production CSP
// blocks inline script (@spec GIV-CLM-021); the worker URL arrives as a
// data attribute on this script tag, rendered by the base template.
(function () {
    var swUrl = document.currentScript.dataset.swUrl;
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register(swUrl)
                .then(function () { console.log('SW registered'); })
                .catch(function (err) {
                    console.log('SW registration failed: ', err);
                });
        });
    }
})();
