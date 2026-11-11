// Native POST forms under no-referrer can send Origin: null. A same-origin
// CORS-mode fetch sends the real Origin while retaining the normal CSRF token.
document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.method.toLowerCase() !== 'post') return;
    const target = new URL(form.getAttribute('action') || window.location.href, window.location.href);
    if (target.origin !== window.location.origin) return;
    event.preventDefault();
    if (form.dataset.submitting) return;
    const data = new FormData(form);
    if (event.submitter?.name) data.append(event.submitter.name, event.submitter.value);
    form.dataset.submitting = 'true';
    try {
        const response = await fetch(target, {
            method: 'POST', mode: 'cors', credentials: 'same-origin',
            referrerPolicy: 'no-referrer', body: data,
        });
        if (new URL(response.url).origin !== window.location.origin) throw new Error('Unexpected destination');
        if (response.redirected) {
            window.history.replaceState(null, '', response.url);
        }
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        document.documentElement.replaceWith(page.documentElement);
        document.querySelector('main')?.focus();
    } catch {
        delete form.dataset.submitting;
        let error = form.querySelector('[data-submit-error]');
        if (!error) {
            error = document.createElement('p');
            error.dataset.submitError = 'true';
            error.setAttribute('role', 'alert');
            form.append(error);
        }
        error.textContent = 'The response could not be loaded. Reload to check the invitation status before trying again.';
    }
});
