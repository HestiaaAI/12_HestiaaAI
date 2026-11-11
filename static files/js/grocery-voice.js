const dictate = document.querySelector("#dictate-grocery");
const voiceStatus = document.querySelector("#voice-status");
const groceryName = document.querySelector("#id_name");
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!Recognition) {
    dictate.disabled = true;
    voiceStatus.textContent = "Voice typing is unavailable in this browser. You can type the name.";
} else {
    let recognition;
    dictate.addEventListener("click", () => {
        if (recognition) {
            recognition.stop();
            return;
        }

        try {
            recognition = new Recognition();
            recognition.lang = document.documentElement.lang || "en";
            recognition.interimResults = false;
            recognition.onstart = () => {
                dictate.textContent = "Stop listening";
                voiceStatus.textContent = "Listening for the grocery name…";
            };
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript.trim();
                groceryName.value = transcript.slice(0, groceryName.maxLength);
                groceryName.dispatchEvent(new Event("input", { bubbles: true }));
                voiceStatus.textContent = "Check the grocery name before saving.";
                groceryName.focus();
            };
            recognition.onerror = (event) => {
                voiceStatus.textContent = event.error === "not-allowed"
                    ? "Allow microphone access to use voice typing."
                    : "Could not hear the name. Try again or type it.";
            };
            recognition.onend = () => {
                recognition = null;
                dictate.textContent = "Use microphone";
            };
            recognition.start();
        } catch {
            recognition = null;
            voiceStatus.textContent = "Voice typing could not start. You can type the name.";
        }
    });
}
