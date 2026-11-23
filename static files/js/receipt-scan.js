const receiptImage = document.querySelector("#receipt-image");
const scanButton = document.querySelector("#scan-image");
const scanStatus = document.querySelector("#scan-status");
const receiptText = document.querySelector("#receipt-text");
const receiptForm = document.querySelector("#receipt-text-form");

scanButton.hidden = false;
scanButton.addEventListener("click", async () => {
    const images = [...receiptImage.files];
    if (!images.length || images.length > 5 || images.some(image => !["image/jpeg", "image/png", "image/webp"].includes(image.type))) {
        scanStatus.textContent = "Choose 1–5 JPG, PNG, or WebP receipt photos.";
        return;
    }
    if (images.some(image => image.size > 10 * 1024 * 1024)) {
        scanStatus.textContent = "Choose an image under 10 MB.";
        return;
    }

    scanButton.disabled = true;
    receiptImage.disabled = true;
    scanStatus.textContent = "Starting the receipt scanner…";
    let worker;
    try {
        worker = await window.Tesseract.createWorker("eng", 1, {
            logger: ({ status, progress }) => {
                if (status === "recognizing text") {
                    scanStatus.textContent = `Reading receipt… ${Math.round(progress * 100)}%`;
                }
            },
        });
        await worker.setParameters({ tessedit_pageseg_mode: window.Tesseract.PSM.SINGLE_BLOCK });
        const texts = [];
        for (let i = 0; i < images.length; i++) {
            scanStatus.textContent = `Reading receipt ${i + 1} of ${images.length}: ${images[i].name}`;
            const { data } = await worker.recognize(images[i], { rotateAuto: true });
            const text = data.text.trim();
            if (!text || text.length > receiptText.maxLength) {
                scanStatus.textContent = `Could not read ${images[i].name}. No receipts submitted. Try a clearer photo.`;
                return;
            }
            texts.push(text);
        }
        receiptForm.querySelectorAll('[data-scanned-receipt]').forEach(field => field.remove());
        // Separate fields preserve each store receipt's own purchase date.
        for (const text of texts) {
            const field = document.createElement('input');
            field.type = 'hidden'; field.name = 'receipt_text'; field.value = text;
            field.dataset.scannedReceipt = 'true'; receiptForm.append(field);
        }
        receiptText.disabled = true;
        receiptForm.requestSubmit();
    } catch {
        scanStatus.textContent = "The scanner could not read this photo. Try again or paste receipt text.";
    } finally {
        try {
            await worker?.terminate();
        } finally {
            scanButton.disabled = false;
            receiptImage.disabled = false;
            receiptText.disabled = false;
            receiptForm.querySelectorAll('[data-scanned-receipt]').forEach(field => field.remove());
        }
    }
});
