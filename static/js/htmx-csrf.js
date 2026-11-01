// Configure htmx to include the CSRF token in all requests.
// @spec GIV-CLM-019
// The token is rendered into a csrf-token meta element in the page head;
// this wiring lives in an external file because the production
// Content-Security-Policy does not allow inline script.
document.body.addEventListener('htmx:configRequest', function (evt) {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
        evt.detail.headers['X-CSRFToken'] = meta.getAttribute('content');
    }
});
