// Cross-page micro-behaviors, delegated at document level so they also
// work inside HTMX-swapped partials. The production CSP blocks inline
// event handlers, so templates declare these hooks with data-*
// attributes and classes instead (@spec GIV-CLM-021):
//
//   form[data-confirm-message]  - ask before submitting; the message is
//                                 the attribute's value.
//   form[data-item-form]        - on submit, disable the submit button
//                                 and swap in its data-saving-label.
//   .js-split-amount            - button that fills the input named by
//                                 data-target with data-amount.
//   .js-img-fallback            - image that swaps to data-fallback-src
//                                 once if it fails to load.
//   .js-history-back            - link that navigates back in history.

// Saving-state swap: disable the form's submit button and, when it
// declares a saving label, show it with a spinner.
function armSavingButton(form) {
    var button = form.querySelector('button[type="submit"]');
    if (button && !button.disabled) {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        if (button.dataset.savingLabel) {
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' + button.dataset.savingLabel;
        }
    }
}

document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    if (form.dataset.confirmMessage &&
        !window.confirm(form.dataset.confirmMessage)) {
        event.preventDefault();
        return;
    }
    var button = form.querySelector('button[type="submit"]');
    if (form.hasAttribute('data-item-form') ||
        (button && button.dataset.savingLabel)) {
        armSavingButton(form);
    }
});

document.addEventListener('click', function (event) {
    var amountButton = event.target.closest('.js-split-amount');
    if (amountButton) {
        var input = document.getElementById(amountButton.dataset.target);
        if (input) {
            input.value = amountButton.dataset.amount;
        }
        return;
    }
    var backLink = event.target.closest('.js-history-back');
    if (backLink) {
        event.preventDefault();
        window.history.back();
    }
});

// Image error events do not bubble; capture phase still sees them.
document.addEventListener('error', function (event) {
    var img = event.target;
    if (img && img.classList && img.classList.contains('js-img-fallback') &&
        !img.dataset.fallbackApplied) {
        img.dataset.fallbackApplied = 'true';
        img.src = img.dataset.fallbackSrc;
    }
}, true);
