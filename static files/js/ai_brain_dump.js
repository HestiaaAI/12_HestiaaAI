"use strict";

const generationForm = document.querySelector("[data-ai-generate]");

if (generationForm) {
    const button = generationForm.querySelector("[data-ai-submit]");
    const status = generationForm.querySelector("[data-ai-loading]");
    const originalLabel = button.textContent;

    generationForm.addEventListener("submit", (event) => {
        if (button.disabled) {
            event.preventDefault();
            return;
        }
        button.disabled = true;
        button.textContent = button.dataset.pendingLabel;
        generationForm.setAttribute("aria-busy", "true");
        status.hidden = false;
    });

    // Restore controls when Back returns a pending page from the browser cache.
    window.addEventListener("pageshow", () => {
        button.disabled = false;
        button.textContent = originalLabel;
        generationForm.removeAttribute("aria-busy");
        status.hidden = true;
    });
}
