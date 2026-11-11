const receiptImage = document.querySelector("#receipt-image");
const scanButton = document.querySelector("#scan-image");
const scanStatus = document.querySelector("#scan-status");
const receiptText = document.querySelector("#receipt-text");
const receiptForm = document.querySelector("#receipt-text-form");

scanButton.hidden = false;
scanButton.addEventListener("click", async () => {
    const image = receiptImage.files[0];
    if (!image || !["image/jpeg", "image/png", "image/webp"].includes(image.type)) {
        scanStatus.textContent = "Choose a JPG, PNG, or WebP receipt photo.";
        return;
    }
    if (image.size > 10 * 1024 * 1024) {
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
        const { data } = await worker.recognize(image, { rotateAuto: true });
        const text = data.text.trim();
        if (!text || text.length > receiptText.maxLength) {
            scanStatus.textContent = "Try a clearer photo of a shorter receipt.";
            return;
        }
        receiptText.value = text;
        receiptForm.requestSubmit();
    } catch {
        scanStatus.textContent = "The scanner could not read this photo. Try again or paste receipt text.";
    } finally {
        try {
            await worker?.terminate();
        } finally {
            scanButton.disabled = false;
            receiptImage.disabled = false;
        }
    }
});
