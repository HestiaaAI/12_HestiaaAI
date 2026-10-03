"use strict";

document.querySelectorAll(".chart-host").forEach(async (host) => {
    const status = host.parentElement.querySelector(".chart-status");
    try {
        const result = await vegaEmbed(host, host.dataset.spec, {
            renderer: "svg",
            actions: {export: true, source: true, compiled: false, editor: true}
        });
        const rows = result.view.data("source_0");
        status.textContent = rows.some((row) => row.count > 0) ? "" : "No tasks yet. Add a task and reload to see it here.";
    } catch (error) {
        status.textContent = "The chart could not load. Reload to retry, or use the source JSON and saved PNG links below.";
    }
});
