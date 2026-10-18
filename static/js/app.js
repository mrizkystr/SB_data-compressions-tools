(() => {
  const form = document.querySelector("#utility-form");
  const fileInput = document.querySelector("#file-input");
  const uploadArea = document.querySelector("#upload-area");
  const fileRow = document.querySelector("#file-row");
  const fileName = document.querySelector("#file-name");
  const fileSize = document.querySelector("#file-size");
  const algorithmSelect = document.querySelector("#algorithm-select");
  const runButton = document.querySelector("#run-button");
  const removeButton = document.querySelector("#remove-file");
  const errorMessage = document.querySelector("#error-message");
  const resultSection = document.querySelector("#result-section");
  const resultEyebrow = document.querySelector("#result-eyebrow");
  const resultTitle = document.querySelector("#result-title");
  const metricsGrid = document.querySelector("#metrics-grid");
  const downloadResult = document.querySelector("#download-result");
  const comparisonResult = document.querySelector("#comparison-result");
  const comparisonSummary = document.querySelector("#comparison-summary");
  const comparisonRows = document.querySelector("#comparison-rows");
  const modeButtons = [...document.querySelectorAll("[data-mode]")];
  const maxUploadSize = 20 * 1024 * 1024;
  const algorithmNames = {
    gzip: "GZIP",
    bz2: "BZip2",
    lzma: "7-Zip (LZMA)",
    zlib: "DEFLATE",
  };

  let selectedFile = null;
  let currentMode = "compress";
  let currentDownloadUrl = null;

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KiB", "MiB", "GiB"];
    let value = bytes / 1024;
    let unit = units[0];
    for (let index = 1; value >= 1024 && index < units.length; index += 1) {
      value /= 1024;
      unit = units[index];
    }
    return `${value.toFixed(value < 10 ? 1 : 0)} ${unit}`;
  }

  function clearDownload() {
    if (currentDownloadUrl) URL.revokeObjectURL(currentDownloadUrl);
    currentDownloadUrl = null;
    downloadResult.hidden = true;
    downloadResult.removeAttribute("href");
  }

  function clearResult() {
    clearDownload();
    resultSection.hidden = true;
    comparisonResult.hidden = true;
    metricsGrid.replaceChildren();
    comparisonRows.replaceChildren();
    comparisonSummary.replaceChildren();
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
  }

  function clearError() {
    errorMessage.textContent = "";
    errorMessage.hidden = true;
  }

  function setFile(file) {
    clearError();
    clearResult();
    if (!file) return;
    if (file.size > maxUploadSize) {
      selectedFile = null;
      fileInput.value = "";
      fileRow.hidden = true;
      uploadArea.hidden = false;
      showError("This file is larger than the 20 MiB upload limit.");
      return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatSize(file.size);
    fileRow.hidden = false;
    uploadArea.hidden = true;
  }

  function resetFile() {
    selectedFile = null;
    fileInput.value = "";
    fileRow.hidden = true;
    uploadArea.hidden = false;
    clearError();
    clearResult();
  }

  function setMode(mode) {
    currentMode = mode;
    clearError();
    clearResult();
    modeButtons.forEach((button) => {
      const active = button.dataset.mode === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    algorithmSelect.disabled = mode === "compare";
    runButton.textContent = {
      compress: "Compress file",
      decompress: "Decompress file",
      compare: "Compare algorithms",
    }[mode];
  }

  function appendMetric(label, value, negative = false) {
    const wrapper = document.createElement("div");
    wrapper.className = "metric";
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    if (negative) detail.classList.add("is-negative");
    wrapper.append(term, detail);
    metricsGrid.append(wrapper);
  }

  function formatPercentage(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    return `${Number(value).toFixed(1)}%`;
  }

  function setDownload(blob, name) {
    clearDownload();
    currentDownloadUrl = URL.createObjectURL(blob);
    downloadResult.href = currentDownloadUrl;
    downloadResult.download = name;
    downloadResult.hidden = false;
  }

  function showCompressionResult(response, blob) {
    const originalSize = Number(response.headers.get("X-Original-Size"));
    const outputSize = Number(response.headers.get("X-Output-Size"));
    const savedBytes = Number(response.headers.get("X-Space-Saved-Bytes"));
    const savedPercent = response.headers.get("X-Space-Saved-Percent");
    const outputName = response.headers.get("X-Download-Name") || "compressed-file";
    const changeLabel = savedBytes < 0 ? "Size increase" : "Space saved";
    const changePercent = savedPercent === null
      ? "—"
      : formatPercentage(Math.abs(Number(savedPercent)));
    const changeValue = savedBytes < 0
      ? `${formatSize(Math.abs(savedBytes))} (${changePercent})`
      : `${formatSize(savedBytes)} (${formatPercentage(savedPercent)})`;

    resultEyebrow.textContent = "COMPLETE";
    resultTitle.textContent = "Compression complete";
    appendMetric("Original size", formatSize(originalSize));
    appendMetric("Compressed size", formatSize(outputSize));
    appendMetric("Compression ratio", formatPercentage(response.headers.get("X-Compression-Ratio")));
    appendMetric(changeLabel, changeValue, savedBytes < 0);
    appendMetric("Processing time", `${response.headers.get("X-Processing-Time-Ms")} ms`);
    setDownload(blob, outputName);
    resultSection.hidden = false;
  }

  function showDecompressionResult(response, blob) {
    const originalSize = Number(response.headers.get("X-Original-Size"));
    const outputSize = Number(response.headers.get("X-Output-Size"));
    const outputName = response.headers.get("X-Download-Name") || "decompressed-file";
    resultEyebrow.textContent = "COMPLETE";
    resultTitle.textContent = "Decompression complete";
    appendMetric("Compressed size", formatSize(originalSize));
    appendMetric("Decompressed size", formatSize(outputSize));
    appendMetric("Expansion", originalSize ? `${(outputSize / originalSize).toFixed(1)}×` : "—");
    appendMetric("Processing time", `${response.headers.get("X-Processing-Time-Ms")} ms`);
    setDownload(blob, outputName);
    resultSection.hidden = false;
  }

  function addSummary(label, value) {
    const item = document.createElement("span");
    item.className = "summary-item";
    const strong = document.createElement("strong");
    strong.textContent = value;
    item.append(document.createTextNode(`${label}: `), strong);
    comparisonSummary.append(item);
  }

  function showComparisonResult(payload) {
    const largestOutput = Math.max(1, ...payload.results.map((item) => item.compressed_size));
    resultEyebrow.textContent = "COMPARISON";
    resultTitle.textContent = "Results for this file";
    comparisonResult.hidden = false;
    addSummary("Smallest output", algorithmNames[payload.best_by_size]);
    addSummary("Fastest", algorithmNames[payload.fastest]);

    payload.results.forEach((item) => {
      const row = document.createElement("tr");
      const nameCell = document.createElement("td");
      nameCell.className = "algorithm-name";
      nameCell.textContent = algorithmNames[item.algorithm];

      const sizeCell = document.createElement("td");
      sizeCell.className = "output-cell";
      const sizeValue = document.createElement("span");
      sizeValue.className = "size-value";
      sizeValue.textContent = formatSize(item.compressed_size);
      const bar = document.createElement("div");
      bar.className = "size-bar";
      bar.setAttribute("aria-hidden", "true");
      const fill = document.createElement("div");
      fill.className = "size-bar-fill";
      fill.style.width = `${(item.compressed_size / largestOutput) * 100}%`;
      bar.append(fill);
      sizeCell.append(sizeValue, bar);

      const ratioCell = document.createElement("td");
      ratioCell.textContent = formatPercentage(item.compression_ratio);
      const timeCell = document.createElement("td");
      timeCell.textContent = `${item.processing_time_ms} ms`;
      const bestCell = document.createElement("td");
      const tags = document.createElement("div");
      tags.className = "best-tags";
      if (item.algorithm === payload.best_by_size) tags.append(makeTag("Smallest"));
      if (item.algorithm === payload.fastest) tags.append(makeTag("Fastest"));
      bestCell.append(tags);
      row.append(nameCell, sizeCell, ratioCell, timeCell, bestCell);
      comparisonRows.append(row);
    });

    resultSection.hidden = false;
  }

  function makeTag(text) {
    const tag = document.createElement("span");
    tag.className = "best-tag";
    tag.textContent = text;
    return tag;
  }

  async function errorFromResponse(response) {
    try {
      const payload = await response.json();
      return payload.error || "The request could not be completed.";
    } catch {
      return "The request could not be completed. Please try again.";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    clearResult();
    if (!selectedFile) {
      showError("Choose a file before continuing.");
      return;
    }

    const mode = currentMode;
    const endpoint = {
      compress: "/api/compress",
      decompress: "/api/decompress",
      compare: "/api/compare",
    }[mode];
    const label = {
      compress: "Compressing…",
      decompress: "Decompressing…",
      compare: "Comparing…",
    }[mode];
    const formData = new FormData();
    formData.append("file", selectedFile, selectedFile.name);
    if (mode !== "compare") formData.append("algorithm", algorithmSelect.value);

    runButton.disabled = true;
    removeButton.disabled = true;
    algorithmSelect.disabled = true;
    modeButtons.forEach((button) => { button.disabled = true; });
    runButton.textContent = label;
    uploadArea.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(endpoint, { method: "POST", body: formData });
      if (!response.ok) {
        showError(await errorFromResponse(response));
        return;
      }
      if (mode === "compare") {
        showComparisonResult(await response.json());
      } else {
        const blob = await response.blob();
        if (mode === "compress") showCompressionResult(response, blob);
        else showDecompressionResult(response, blob);
      }
    } catch {
      showError("Could not reach the server. Check your connection and try again.");
    } finally {
      runButton.disabled = false;
      removeButton.disabled = false;
      algorithmSelect.disabled = currentMode === "compare";
      modeButtons.forEach((button) => { button.disabled = false; });
      runButton.textContent = {
        compress: "Compress file",
        decompress: "Decompress file",
        compare: "Compare algorithms",
      }[currentMode];
      uploadArea.removeAttribute("aria-busy");
    }
  });

  uploadArea.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("click", (event) => event.stopPropagation());
  uploadArea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", () => setFile(fileInput.files?.[0] || null));
  removeButton.addEventListener("click", resetFile);
  modeButtons.forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });
  ["dragenter", "dragover"].forEach((eventName) => {
    uploadArea.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadArea.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    uploadArea.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadArea.classList.remove("is-dragging");
    });
  });
  uploadArea.addEventListener("drop", (event) => {
    setFile(event.dataTransfer?.files?.[0] || null);
  });
  window.addEventListener("beforeunload", () => clearDownload());
})();
