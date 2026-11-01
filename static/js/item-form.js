// Item form behavior: "Autofill from URL" fetches page metadata and
// fills the form. Shared by the submit and edit item pages. External
// because the production CSP blocks inline script (@spec GIV-CLM-021).
// The submit button's saving state is handled by app-behaviors.js via
// the form's data-item-form attribute.
var autofillBtn = document.getElementById('autofill-btn');
if (autofillBtn) {
    autofillBtn.addEventListener('click', async function () {
        const linkInput = document.getElementById('link');
        const url = linkInput.value;
        if (!url) {
            alert('Please enter a URL first');
            return;
        }

        const btn = this;
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Fetching...';

        try {
            const response = await fetch('/api/fetch-metadata', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();
            if (data.error) {
                console.error(data.error);
                alert('Could not fetch details. Please fill manually.');
            } else {
                if (data.title) {
                    // Truncate if too long (DB limit 750)
                    document.getElementById('description').value = data.title.substring(0, 749);
                }
                if (data.price) document.getElementById('price').value = data.price;
                if (data.image_url) document.getElementById('image_url').value = data.image_url;
                if (data.category && document.getElementById('category')) {
                    // Only autofill category if empty, to not overwrite user choice
                    if (!document.getElementById('category').value) {
                        document.getElementById('category').value = data.category;
                    }
                }

                // Visual feedback
                linkInput.classList.add('is-valid');
                setTimeout(() => linkInput.classList.remove('is-valid'), 2000);
            }
        } catch (e) {
            console.error(e);
            alert('Failed to connect to server.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}
