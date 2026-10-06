const state = {
    apiBase: "",
    theme: localStorage.getItem("smartdatalab-theme") || "dark",
    datasetId: null,
    datasetName: "",
    datasetSummary: null,
    datasetInfo: "",
    datasetStats: [],
    insights: [],
    preview: { columns: [], rows: [], total_rows: 0 },
    previewFilter: "",
    history: [],
};

const elements = {};
let toastTimer;

document.addEventListener("DOMContentLoaded", async () => {
    cacheElements();
    bindEvents();
    applyTheme(state.theme);
    renderInitialState();

    try {
        await ensureApiBase();
    } catch (error) {
        showToast(error.message, "error");
    }

    refreshSuggestions("").catch(() => {});
});

function cacheElements() {
    elements.navLinks = Array.from(document.querySelectorAll(".nav-link"));
    elements.sidebarUploadButton = document.getElementById("sidebar-upload-button");
    elements.datasetFile = document.getElementById("dataset-file");
    elements.themeToggle = document.getElementById("theme-toggle");
    elements.saveVersionButton = document.getElementById("save-version-button");
    elements.connectionStatus = document.getElementById("connection-status");
    elements.activeDatasetName = document.getElementById("active-dataset-name");
    elements.activeDatasetMeta = document.getElementById("active-dataset-meta");

    elements.metricRows = document.getElementById("metric-rows");
    elements.metricColumns = document.getElementById("metric-columns");
    elements.metricQuality = document.getElementById("metric-quality");
    elements.metricHistory = document.getElementById("metric-history");

    elements.resetSessionButton = document.getElementById("reset-session-button");

    elements.uploadForm = document.getElementById("upload-form");
    elements.browseButton = document.getElementById("browse-button");
    elements.uploadDropzone = document.getElementById("upload-dropzone");
    elements.fileNameLabel = document.getElementById("file-name-label");
    elements.loaderOutput = document.getElementById("loader-output");

    elements.pathForm = document.getElementById("path-form");
    elements.pathInput = document.getElementById("path-input");

    elements.previewFilter = document.getElementById("preview-filter");
    elements.previewStatus = document.getElementById("preview-status");
    elements.previewTable = document.getElementById("preview-table");

    elements.infoOutput = document.getElementById("info-output");
    elements.statsOutput = document.getElementById("stats-output");

    elements.commandForm = document.getElementById("command-form");
    elements.commandInput = document.getElementById("command-input");
    elements.runCommandButton = document.getElementById("run-command-button");
    elements.suggestions = document.getElementById("suggestions");
    elements.commandOutputStack = document.getElementById("command-output-stack");

    elements.chartForm = document.getElementById("chart-form");
    elements.chartType = document.getElementById("chart-type");
    elements.chartX = document.getElementById("chart-x");
    elements.chartY = document.getElementById("chart-y");
    elements.renderChartButton = document.getElementById("render-chart-button");
    elements.chartOutput = document.getElementById("chart-output");

    elements.insightsOutput = document.getElementById("insights-output");

    elements.exportButtons = Array.from(document.querySelectorAll(".export-button"));
    elements.exportOutput = document.getElementById("export-output");

    elements.historyOutput = document.getElementById("history-output");
    elements.toast = document.getElementById("toast");
}

function bindEvents() {
    elements.navLinks.forEach((button) => {
        button.addEventListener("click", () => {
            elements.navLinks.forEach((nav) => nav.classList.remove("is-active"));
            button.classList.add("is-active");
            scrollToTarget(button.dataset.target);
        });
    });

    elements.sidebarUploadButton.addEventListener("click", () => {
        scrollToTarget("loader-panel");
        elements.datasetFile.click();
    });

    elements.browseButton.addEventListener("click", () => elements.datasetFile.click());
    elements.datasetFile.addEventListener("change", updateFileNameLabel);

    elements.uploadForm.addEventListener("submit", handleFileUpload);
    elements.pathForm.addEventListener("submit", handlePathUpload);

    elements.uploadDropzone.addEventListener("dragover", (event) => {
        event.preventDefault();
        elements.uploadDropzone.classList.add("is-dragging");
    });

    elements.uploadDropzone.addEventListener("dragleave", (event) => {
        event.preventDefault();
        elements.uploadDropzone.classList.remove("is-dragging");
    });

    elements.uploadDropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        elements.uploadDropzone.classList.remove("is-dragging");
        const [file] = event.dataTransfer.files;
        if (!file) {
            return;
        }
        const transfer = new DataTransfer();
        transfer.items.add(file);
        elements.datasetFile.files = transfer.files;
        updateFileNameLabel();
    });

    elements.previewFilter.addEventListener(
        "input",
        debounce(() => {
            state.previewFilter = elements.previewFilter.value.trim();
            refreshPreview().catch(handleRequestError);
        }, 220)
    );

    elements.commandInput.addEventListener(
        "input",
        debounce(() => refreshSuggestions(elements.commandInput.value.trim()).catch(() => {}), 120)
    );
    elements.commandForm.addEventListener("submit", handleCommandExecution);

    elements.chartType.addEventListener("change", updateChartFieldState);
    elements.chartForm.addEventListener("submit", handleChartExecution);

    elements.exportButtons.forEach((button) => {
        button.addEventListener("click", () => exportDataset(button.dataset.exportFormat));
    });

    elements.saveVersionButton.addEventListener("click", saveDatasetVersion);
    elements.resetSessionButton.addEventListener("click", resetSession);

    elements.themeToggle.addEventListener("click", () => {
        const nextTheme = state.theme === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
    });
}

function renderInitialState() {
    renderDatasetState();
    renderPreview();
    renderInfo();
    renderStats();
    renderInsights();
    renderHistory();
    updateControlState();
    updateChartFieldState();
    renderChartPlaceholder();
}

function scrollToTarget(targetId) {
    const target = document.getElementById(targetId);
    if (!target) {
        return;
    }
    target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function applyTheme(theme) {
    state.theme = theme;
    document.body.dataset.theme = theme;
    localStorage.setItem("smartdatalab-theme", theme);
    elements.themeToggle.textContent = theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme";
}

async function ensureApiBase(force = false) {
    if (state.apiBase && !force) {
        return state.apiBase;
    }

    const candidates = [];
    if (window.location.protocol.startsWith("http")) {
        candidates.push(window.location.origin);
    }
    candidates.push("http://127.0.0.1:5000", "http://localhost:5000");

    const uniqueCandidates = [...new Set(candidates)];

    for (const candidate of uniqueCandidates) {
        const url = `${candidate}/api/health`;
        try {
            const response = await fetch(url, { method: "GET" });
            if (!response.ok) {
                continue;
            }
            state.apiBase = candidate;
            setConnectionStatus("Backend ready", "good");
            return state.apiBase;
        } catch (_error) {
            continue;
        }
    }

    setConnectionStatus("Backend unavailable", "error");
    const openHint = window.location.protocol.startsWith("http")
        ? "Use the Flask URL http://127.0.0.1:5000 (not index.html or a separate Live Server tab)."
        : "Open the app at http://127.0.0.1:5000 instead of opening index.html directly.";
    throw new Error(
        "Failed to fetch backend API. Start Flask with `python app.py`. " + openHint
    );
}

function setConnectionStatus(label, tone) {
    elements.connectionStatus.textContent = label;
    elements.connectionStatus.className = `status-chip ${tone || ""}`.trim();
}

function apiUrl(path) {
    return `${state.apiBase}${path}`;
}

async function apiJson(path, options = {}) {
    await ensureApiBase();

    const config = { ...options };
    if (config.body && !(config.body instanceof FormData)) {
        config.headers = {
            "Content-Type": "application/json",
            ...(config.headers || {}),
        };
    }

    let response;
    try {
        response = await fetch(apiUrl(path), config);
    } catch (_error) {
        throw new Error("Failed to fetch backend. Verify the Flask server is running and reachable.");
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
        throw new Error(payload.error || payload.message || "Request failed.");
    }

    return payload;
}

function updateFileNameLabel() {
    const [file] = elements.datasetFile.files;
    elements.fileNameLabel.textContent = file ? file.name : "No file selected";
}

async function handleFileUpload(event) {
    event.preventDefault();
    const [file] = elements.datasetFile.files;
    if (!file) {
        showToast("Choose a dataset file first.", "warning");
        return;
    }

    const formData = new FormData();
    formData.append("dataset", file);

    try {
        const payload = await apiJson("/api/upload", { method: "POST", body: formData });
        handleLoadedDataset(payload, `Loaded ${file.name}.`);
    } catch (error) {
        handleRequestError(error);
    }
}

async function handlePathUpload(event) {
    event.preventDefault();
    const pathValue = elements.pathInput.value.trim();
    if (!pathValue) {
        showToast("Enter a local dataset path.", "warning");
        return;
    }

    try {
        const payload = await apiJson("/api/upload-path", {
            method: "POST",
            body: JSON.stringify({ path: pathValue }),
        });
        handleLoadedDataset(payload, `Loaded dataset from path ${pathValue}.`);
    } catch (error) {
        handleRequestError(error);
    }
}

function handleLoadedDataset(payload, fallbackMessage) {
    applyDatasetPayload(payload);
    elements.loaderOutput.textContent = payload.note || fallbackMessage;
    elements.exportOutput.textContent = "Dataset ready for export.";
    elements.commandOutputStack.innerHTML = "";
    renderChartPlaceholder();
    addHistoryEntry("Dataset loaded", `upload ${payload.name}`, payload.note || fallbackMessage);
    showToast(payload.note || "Dataset loaded successfully.", "success");
}

function applyDatasetPayload(payload) {
    state.datasetId = payload.datasetId;
    state.datasetName = payload.name;
    state.datasetSummary = payload.summary;
    state.datasetInfo = payload.info || "";
    state.datasetStats = payload.stats || [];
    state.insights = payload.insights || [];
    state.preview = payload.preview || { columns: [], rows: [], total_rows: 0 };

    renderDatasetState();
    renderPreview();
    renderInfo();
    renderStats();
    renderInsights();
    populateChartSelectors();
    updateControlState();
}

function renderDatasetState() {
    const summary = state.datasetSummary;
    if (!summary) {
        elements.activeDatasetName.textContent = "No dataset loaded";
        elements.activeDatasetMeta.textContent = "Load CSV, Excel, or JSON to start notebook execution.";
        elements.metricRows.textContent = "--";
        elements.metricColumns.textContent = "--";
        elements.metricQuality.textContent = "--";
        elements.metricHistory.textContent = String(state.history.length);
        return;
    }

    elements.activeDatasetName.textContent = state.datasetName;
    elements.activeDatasetMeta.textContent = `${formatNumber(summary.rows)} rows, ${formatNumber(summary.columns)} columns`;
    elements.metricRows.textContent = formatNumber(summary.rows);
    elements.metricColumns.textContent = formatNumber(summary.columns);
    elements.metricQuality.textContent = `${summary.quality_score}`;
    elements.metricHistory.textContent = String(state.history.length);
}

async function refreshPreview() {
    if (!state.datasetId) {
        return;
    }

    const params = new URLSearchParams({
        filter: state.previewFilter,
        limit: "50",
    });

    const preview = await apiJson(`/api/preview/${state.datasetId}?${params.toString()}`);
    state.preview = preview;
    renderPreview();
}

function renderPreview() {
    if (!state.preview.columns.length) {
        elements.previewStatus.textContent = "Awaiting dataset";
        elements.previewTable.innerHTML = `
            <tbody>
                <tr>
                    <td>
                        <div class="empty-state">Load a dataset to render df.head() output.</div>
                    </td>
                </tr>
            </tbody>
        `;
        return;
    }

    const columns = state.preview.columns;
    const rows = state.preview.rows;

    elements.previewStatus.textContent = `Showing ${formatNumber(rows.length)} of ${formatNumber(state.preview.total_rows)} rows`;

    const header = columns
        .map((column) => `<th>${escapeHtml(column.name)}<br><small>${escapeHtml(column.dtype)}</small></th>`)
        .join("");

    const body = rows
        .map(
            (row) => `
                <tr>
                    ${columns.map((column) => `<td>${formatCell(row[column.name])}</td>`).join("")}
                </tr>
            `
        )
        .join("");

    elements.previewTable.innerHTML = `<thead><tr>${header}</tr></thead><tbody>${body}</tbody>`;
}

function renderInfo() {
    elements.infoOutput.textContent = state.datasetInfo || "Load a dataset to see dataframe info output.";
}

function renderStats() {
    if (!state.datasetStats.length) {
        elements.statsOutput.innerHTML = `<div class="empty-state">Load a dataset to render df.describe() output.</div>`;
        return;
    }

    const keys = ["column", "count", "mean", "std", "min", "max", "top", "freq"];
    const rows = state.datasetStats.slice(0, 12);
    const activeKeys = keys.filter((key) => rows.some((row) => row[key] !== null && row[key] !== undefined));

    const columns = activeKeys.map((name) => ({ name }));
    elements.statsOutput.innerHTML = renderTableMarkup(columns, rows, 12);
}

function renderInsights() {
    if (!state.insights.length) {
        elements.insightsOutput.innerHTML = `<div class="empty-state">Load a dataset to view AI insight diagnostics.</div>`;
        return;
    }

    elements.insightsOutput.innerHTML = state.insights
        .map(
            (insight) => `
                <article class="insight-card ${escapeHtml(insight.severity || "info")}">
                    <h4>${escapeHtml(insight.title)}</h4>
                    <p>${escapeHtml(insight.detail)}</p>
                    <p class="muted-copy">${escapeHtml(insight.recommendation)}</p>
                </article>
            `
        )
        .join("");
}

function updateControlState() {
    const hasDataset = Boolean(state.datasetId);

    elements.runCommandButton.disabled = !hasDataset;
    elements.chartType.disabled = !hasDataset;
    elements.chartX.disabled = !hasDataset;
    elements.chartY.disabled = !hasDataset;
    elements.renderChartButton.disabled = !hasDataset;
    elements.saveVersionButton.disabled = !hasDataset;

    elements.exportButtons.forEach((button) => {
        button.disabled = !hasDataset;
    });
}

function populateChartSelectors() {
    const summary = state.datasetSummary;
    if (!summary) {
        populateSelect(elements.chartX, [], "Select X column");
        populateSelect(elements.chartY, [], "Select Y column");
        return;
    }

    const numericColumns = summary.numeric_columns || [];
    const allColumns = summary.column_names || [];
    const chartType = elements.chartType.value;

    if (chartType === "scatter") {
        populateSelect(elements.chartX, numericColumns, "Select X column", elements.chartX.value);
        populateSelect(elements.chartY, numericColumns, "Select Y column", elements.chartY.value);
        return;
    }

    populateSelect(elements.chartX, numericColumns.length ? numericColumns : allColumns, "Select X column", elements.chartX.value);
    populateSelect(elements.chartY, numericColumns, "Select Y column", elements.chartY.value);
}

function updateChartFieldState() {
    const chartType = elements.chartType.value;
    const showAxes = chartType !== "correlation";

    elements.chartX.style.display = showAxes ? "block" : "none";
    elements.chartY.style.display = chartType === "scatter" ? "block" : "none";

    populateChartSelectors();
}

async function handleCommandExecution(event) {
    event.preventDefault();
    if (!requireDataset("Load a dataset before executing pandas commands.")) {
        return;
    }

    const command = elements.commandInput.value.trim();
    if (!command) {
        showToast("Enter a pandas command.", "warning");
        return;
    }

    try {
        const payload = await apiJson(`/api/console/${state.datasetId}`, {
            method: "POST",
            body: JSON.stringify({ command }),
        });

        applyDatasetPayload(payload.dataset);
        appendCommandOutput(payload.command, payload.result);
        renderSuggestions(payload.suggestions || []);
        addHistoryEntry("Command executed", payload.command, payload.message);
        showToast(payload.message || "Command executed.", "success");
    } catch (error) {
        handleRequestError(error);
    }
}

function appendCommandOutput(command, result) {
    const wrapper = document.createElement("article");
    wrapper.className = "output-entry";

    let content = "";
    if (result.type === "text") {
        content = `<pre>${escapeHtml(result.content)}</pre>`;
    } else {
        content = renderTableMarkup(result.columns || [], result.rows || [], 20);
    }

    wrapper.innerHTML = `
        <h4>${escapeHtml(result.title || "Output")}</h4>
        <p class="muted-copy">${escapeHtml(command)}</p>
        ${content}
    `;

    elements.commandOutputStack.prepend(wrapper);
}

async function refreshSuggestions(query) {
    try {
        const payload = await apiJson(`/api/console/suggestions?query=${encodeURIComponent(query)}`);
        renderSuggestions(payload.suggestions || []);
    } catch (_error) {
        renderSuggestions([]);
    }
}

function renderSuggestions(suggestions) {
    if (!suggestions.length) {
        elements.suggestions.innerHTML = "";
        return;
    }

    elements.suggestions.innerHTML = suggestions
        .map((item) => `<button class="suggestion-chip" type="button" data-suggestion="${escapeAttribute(item)}">${escapeHtml(item)}</button>`)
        .join("");

    elements.suggestions.querySelectorAll("[data-suggestion]").forEach((button) => {
        button.addEventListener("click", () => {
            elements.commandInput.value = button.dataset.suggestion;
            refreshSuggestions(button.dataset.suggestion).catch(() => {});
        });
    });
}

async function handleChartExecution(event) {
    event.preventDefault();
    if (!requireDataset("Load a dataset before generating charts.")) {
        return;
    }

    const chartType = elements.chartType.value;
    const payload = {
        type: chartType,
        theme: state.theme,
    };

    if (chartType !== "correlation") {
        if (!elements.chartX.value) {
            showToast("Select an X column.", "warning");
            return;
        }
        payload.x = elements.chartX.value;
    }

    if (chartType === "scatter") {
        if (!elements.chartY.value) {
            showToast("Select a Y column for scatter plot.", "warning");
            return;
        }
        payload.y = elements.chartY.value;
    }

    try {
        const response = await apiJson(`/api/chart/${state.datasetId}`, {
            method: "POST",
            body: JSON.stringify(payload),
        });

        Plotly.newPlot(elements.chartOutput, response.figure.data, response.figure.layout, {
            responsive: true,
            displayModeBar: false,
        });

        addHistoryEntry("Chart rendered", chartCommandLabel(payload), "Visualization generated.");
        showToast("Chart rendered successfully.", "success");
    } catch (error) {
        handleRequestError(error);
    }
}

function renderChartPlaceholder() {
    elements.chartOutput.innerHTML = `<div class="empty-state">Generate a chart to display interactive output here.</div>`;
}

async function exportDataset(format) {
    if (!requireDataset("Load a dataset before exporting.")) {
        return;
    }

    try {
        await ensureApiBase();
        const response = await fetch(apiUrl(`/api/export/${state.datasetId}`), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ format, name: state.datasetName || "smartdatalab" }),
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => ({ error: "Export failed." }));
            throw new Error(payload.error || "Export failed.");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${slugify(state.datasetName || "smartdatalab")}.${format}`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);

        const message = `Exported dataset as ${format.toUpperCase()}.`;
        elements.exportOutput.textContent = message;
        addHistoryEntry("Dataset exported", `export ${format}`, message);
        showToast(message, "success");
    } catch (error) {
        handleRequestError(error);
    }
}

async function saveDatasetVersion() {
    if (!requireDataset("Load a dataset before saving a version.")) {
        return;
    }

    try {
        const payload = await apiJson(`/api/save/${state.datasetId}`, {
            method: "POST",
            body: JSON.stringify({ name: state.datasetName, format: "csv" }),
        });
        addHistoryEntry("Version saved", "save dataset", payload.message);
        showToast(payload.message || "Dataset version saved.", "success");
    } catch (error) {
        handleRequestError(error);
    }
}

function resetSession() {
    state.datasetId = null;
    state.datasetName = "";
    state.datasetSummary = null;
    state.datasetInfo = "";
    state.datasetStats = [];
    state.insights = [];
    state.preview = { columns: [], rows: [], total_rows: 0 };
    state.previewFilter = "";

    elements.datasetFile.value = "";
    elements.pathInput.value = "";
    elements.previewFilter.value = "";
    elements.commandInput.value = "";

    updateFileNameLabel();
    renderDatasetState();
    renderPreview();
    renderInfo();
    renderStats();
    renderInsights();
    renderChartPlaceholder();
    elements.commandOutputStack.innerHTML = "";
    updateControlState();

    elements.loaderOutput.textContent = "Session reset. Load a dataset to continue.";
    elements.exportOutput.textContent = "Export status will appear here.";
    showToast("Session reset.", "success");
}

function addHistoryEntry(title, command, detail) {
    state.history.unshift({
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        title,
        command,
        detail,
    });
    if (state.history.length > 120) {
        state.history = state.history.slice(0, 120);
    }

    elements.metricHistory.textContent = String(state.history.length);
    renderHistory();
}

function renderHistory() {
    if (!state.history.length) {
        elements.historyOutput.innerHTML = `<div class="empty-state">No operations executed yet.</div>`;
        return;
    }

    elements.historyOutput.innerHTML = state.history
        .map(
            (entry) => `
                <article class="history-entry">
                    <h4>${escapeHtml(entry.title)}</h4>
                    <p class="muted-copy">${escapeHtml(entry.time)} · ${escapeHtml(entry.command)}</p>
                    <p>${escapeHtml(entry.detail || "")}</p>
                </article>
            `
        )
        .join("");
}

function requireDataset(message) {
    if (state.datasetId) {
        return true;
    }
    showToast(message, "warning");
    return false;
}

function renderTableMarkup(columns, rows, limit = 20) {
    const normalizedColumns = columns.map((column) => (typeof column === "string" ? { name: column } : column));
    const visibleRows = rows.slice(0, limit);

    if (!normalizedColumns.length) {
        return `<div class="empty-state">No table data available.</div>`;
    }

    const header = normalizedColumns.map((column) => `<th>${escapeHtml(column.name)}</th>`).join("");
    const body = visibleRows
        .map(
            (row) => `
                <tr>
                    ${normalizedColumns.map((column) => `<td>${formatCell(row[column.name])}</td>`).join("")}
                </tr>
            `
        )
        .join("");

    return `
        <table class="mini-table">
            <thead><tr>${header}</tr></thead>
            <tbody>${body}</tbody>
        </table>
    `;
}

function formatCell(value) {
    if (value === null || value === undefined || value === "") {
        return '<span class="muted-copy">null</span>';
    }
    return escapeHtml(value);
}

function formatNumber(value) {
    return new Intl.NumberFormat().format(value ?? 0);
}

function chartCommandLabel(payload) {
    if (payload.type === "correlation") {
        return "chart correlation";
    }
    if (payload.type === "scatter") {
        return `chart scatter ${payload.x} ${payload.y}`;
    }
    return `chart histogram ${payload.x}`;
}

function populateSelect(selectElement, values, placeholder, selectedValue = "") {
    const options = values
        .map((value) => `<option value="${escapeAttribute(value)}">${escapeHtml(value)}</option>`)
        .join("");

    selectElement.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;

    if (selectedValue && values.includes(selectedValue)) {
        selectElement.value = selectedValue;
    }
}

function showToast(message, tone = "success") {
    clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.className = `toast ${tone} is-visible`;

    toastTimer = setTimeout(() => {
        elements.toast.className = "toast";
    }, 2800);
}

function handleRequestError(error) {
    showToast(error.message || "Request failed.", "error");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#96;");
}

function slugify(value) {
    return String(value || "smartdatalab")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "smartdatalab";
}

function debounce(callback, delay) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => callback(...args), delay);
    };
}
