// ---------------------------------------------------------------------------
// API Configuration — set RAILWAY_URL in index.html meta tag for production
// ---------------------------------------------------------------------------
const _meta = document.querySelector('meta[name="api-base-url"]');
const API_BASE_URL = (_meta && _meta.content) ? _meta.content.replace(/\/$/, "") : "";
const WS_BASE_URL = API_BASE_URL
    ? API_BASE_URL.replace(/^http/, "ws")   // https://... → wss://...
    : "";                                   // empty = use window.location (local)

// Application State
let inspections = [];
let currentInspection = null;
let ws = null;
let reconnectDelay = 1000;
let uploadFile = null;


// DOM Elements
const wsStatus = document.getElementById("ws-status");
const liveClock = document.getElementById("live-clock");
const triggerScanBtn = document.getElementById("btn-trigger-scan");
const uploadImageBtn = document.getElementById("btn-upload-image");
const feedList = document.getElementById("inspection-feed");
const feedCount = document.getElementById("feed-count");

// Viewer Elements
const viewerPlaceholder = document.getElementById("viewer-placeholder");
const viewerLoader = document.getElementById("viewer-loader");
const pcbContainer = document.getElementById("pcb-container");
const pcbImage = document.getElementById("pcb-image");
const defectCanvas = document.getElementById("defect-canvas");
const viewerStatusContainer = document.getElementById("viewer-status-container");
const selectedStatus = document.getElementById("selected-status");

// Stats Elements
const metricTotal = document.getElementById("metric-total");
const metricYield = document.getElementById("metric-yield");

// Control Panel Elements
const overrideFormContainer = document.getElementById("override-form-container");
const overridePlaceholder = document.getElementById("override-placeholder");
const infoBoardId = document.getElementById("info-board-id");
const infoInspectionId = document.getElementById("info-inspection-id");
const infoDefectsCount = document.getElementById("info-defects-count");
const infoSeverity = document.getElementById("info-severity");
const verdictReasonBox = document.getElementById("verdict-reason-box");
const defectsTableContainer = document.getElementById("defects-table-container");
const defectsListBody = document.getElementById("defects-list-body");
const overrideForm = document.getElementById("override-form");
const overridePass = document.getElementById("override-pass");
const overrideFail = document.getElementById("override-fail");
const operatorNotes = document.getElementById("operator-notes");
const btnSaveOverride = document.getElementById("btn-save-override");

// Upload Modal Elements
const uploadModal = document.getElementById("upload-modal");
const uploadZone = document.getElementById("upload-zone");
const uploadFileInput = document.getElementById("upload-file-input");
const uploadBoardId = document.getElementById("upload-board-id");
const uploadPreview = document.getElementById("upload-preview");
const uploadPreviewImg = document.getElementById("upload-preview-img");
const uploadPreviewName = document.getElementById("upload-preview-name");
const uploadPreviewSize = document.getElementById("upload-preview-size");
const btnSubmitUpload = document.getElementById("btn-submit-upload");
const btnCloseUploadModal = document.getElementById("btn-close-upload-modal");

// 1. Initial Load & Clock Setup
document.addEventListener("DOMContentLoaded", () => {
    initClock();
    fetchInspections();
    connectWebSocket();

    triggerScanBtn.addEventListener("click", triggerScan);
    uploadImageBtn.addEventListener("click", openUploadModal);
    btnCloseUploadModal.addEventListener("click", closeUploadModal);
    btnSubmitUpload.addEventListener("click", submitUpload);
    uploadFileInput.addEventListener("change", handleFileSelected);
    overrideForm.addEventListener("submit", submitOverride);
    pcbImage.addEventListener("load", handleImageLoaded);

    // Close modal on overlay click
    uploadModal.addEventListener("click", (e) => {
        if (e.target === uploadModal) closeUploadModal();
    });

    // Drag & Drop
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("drag-over");
    });
    uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file) setUploadFile(file);
    });

    // Recalculate canvas overlay on window resize
    window.addEventListener("resize", () => {
        if (currentInspection && currentInspection.image_url && currentInspection.status !== "PROCESSING") {
            drawDefects(currentInspection.defects || []);
        }
    });

    // Keyboard: Escape closes modal
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeUploadModal();
    });
});

// Live clock helper
function initClock() {
    setInterval(() => {
        liveClock.textContent = new Date().toLocaleTimeString();
    }, 1000);
}

// 2. Fetch History via REST API
async function fetchInspections() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/inspections/?limit=50`);
        if (response.ok) {
            inspections = await response.json();
            renderFeed();
            updateMetrics();
        }
    } catch (error) {
        console.error("Error fetching inspections:", error);
    }
}

// 3. WebSocket Real-time Connection
function connectWebSocket() {
    const wsUrl = WS_BASE_URL
        ? `${WS_BASE_URL}/ws`
        : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        wsStatus.className = "status-indicator connected";
        wsStatus.querySelector(".status-label").textContent = "Connected Live";
        reconnectDelay = 1000;

        // Clear polling fallback if connected
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            console.log("WebSocket connected. Cleared polling fallback.");
        }
    };

    ws.onmessage = (event) => {
        try {
            handleWebSocketEvent(JSON.parse(event.data));
        } catch (err) {
            console.error("Error parsing WebSocket event:", err);
        }
    };

    ws.onclose = () => {
        wsStatus.className = "status-indicator disconnected";
        wsStatus.querySelector(".status-label").textContent = "Disconnected (Polling active)";

        // Start polling fallback if not already running
        if (!pollingInterval) {
            console.log("WebSocket disconnected. Starting polling fallback...");
            pollingInterval = setInterval(fetchInspections, 3000);
        }

        setTimeout(connectWebSocket, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    };

    ws.onerror = (error) => console.error("WebSocket error:", error);
}

// 4. Handle Real-Time WS Messages
function handleWebSocketEvent(payload) {
    const { event, data } = payload;

    if (event === "inspection_processing") {
        const idx = inspections.findIndex(item => item.id === data.id);
        const itemData = { ...data, defects: [], image_url: null };
        if (idx !== -1) inspections[idx] = { ...inspections[idx], ...itemData };
        else inspections.unshift(itemData);

        renderFeed();
        if (currentInspection && currentInspection.id === data.id) {
            currentInspection = inspections.find(item => item.id === data.id);
            showProcessingState();
        }
    }
    else if (event === "inspection_completed") {
        const idx = inspections.findIndex(item => item.id === data.id);
        if (idx !== -1) inspections[idx] = { ...inspections[idx], ...data };
        else inspections.unshift(data);

        renderFeed();
        updateMetrics();

        if (currentInspection && currentInspection.id === data.id) {
            currentInspection = inspections.find(item => item.id === data.id);
            displayInspection(currentInspection);
        } else if (!currentInspection) {
            currentInspection = inspections[0];
            displayInspection(currentInspection);
        }
    }
    else if (event === "inspection_error") {
        const idx = inspections.findIndex(item => item.id === data.id);
        if (idx !== -1) {
            inspections[idx].status = "ERROR";
            renderFeed();
            if (currentInspection && currentInspection.id === data.id) {
                currentInspection.status = "ERROR";
                displayInspection(currentInspection);
            }
        }
    }
}

// 5. Render Feed Sidebar
function renderFeed() {
    feedCount.textContent = `${inspections.length} Boards`;

    if (inspections.length === 0) {
        feedList.innerHTML = `
            <div class="empty-feed">
                <i class="fa-solid fa-circle-nodes"></i>
                <p>Waiting for scan triggers...</p>
            </div>
        `;
        return;
    }

    feedList.innerHTML = "";
    inspections.forEach(item => {
        const div = document.createElement("div");
        div.className = `feed-item ${currentInspection && currentInspection.id === item.id ? 'active' : ''}`;
        div.onclick = () => selectInspection(item.id);

        const date = new Date(item.created_at || item.updated_at);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        const statusClass = item.status ? item.status.toLowerCase() : "pending";

        div.innerHTML = `
            <div class="feed-item-header">
                <span class="feed-item-id">${item.board_id}</span>
                <span class="feed-status ${statusClass}">${item.status || 'PENDING'}</span>
            </div>
            <div class="feed-item-time">
                <i class="fa-regular fa-clock"></i> ${timeStr}
            </div>
        `;
        feedList.appendChild(div);
    });
}

// 6. Select and view Inspection
function selectInspection(id) {
    const item = inspections.find(insp => insp.id === id);
    if (!item) return;
    currentInspection = item;
    document.querySelectorAll(".feed-item").forEach((el, index) => {
        el.classList.toggle("active", inspections[index] && inspections[index].id === id);
    });
    displayInspection(item);
}

// 7. Display Inspection in Viewer & Console
function displayInspection(item) {
    if (item.status === "PENDING" || item.status === "PROCESSING") {
        showProcessingState();
        hideConsole();
        return;
    }

    viewerPlaceholder.style.display = "none";
    viewerLoader.style.display = "none";
    pcbContainer.style.display = "flex";
    viewerStatusContainer.style.display = "block";

    selectedStatus.textContent = item.status;
    selectedStatus.className = `status-badge ${(item.status || "").toLowerCase()}`;

    if (item.image_url) pcbImage.src = item.image_url;
    showConsole(item);
}

function showProcessingState() {
    viewerPlaceholder.style.display = "none";
    pcbContainer.style.display = "none";
    viewerStatusContainer.style.display = "none";
    viewerLoader.style.display = "flex";
}

function showConsole(item) {
    overridePlaceholder.style.display = "none";
    overrideFormContainer.style.display = "flex";

    infoBoardId.textContent = item.board_id;
    infoInspectionId.textContent = `#${item.id}`;

    const defectCount = item.defects ? item.defects.length : 0;
    infoDefectsCount.textContent = `${defectCount} found`;
    infoDefectsCount.className = defectCount > 0 ? "val text-danger" : "val";

    // Severity badge (Phase 4)
    const severity = (item.severity || "NONE").toLowerCase();
    if (infoSeverity) {
        infoSeverity.innerHTML = `<span class="severity-badge ${severity}">${(item.severity || "NONE").toUpperCase()}</span>`;
    }

    // Verdict reason box (Phase 4)
    if (verdictReasonBox) {
        const reason = item.verdict_reason || "";
        if (reason) {
            const reasonClass = item.status === "FAIL" ? "fail-reason"
                : item.status === "WARNING" ? "warning-reason"
                : "pass-reason";
            verdictReasonBox.className = `verdict-reason-box active ${reasonClass}`;
            verdictReasonBox.textContent = reason;
        } else {
            verdictReasonBox.className = "verdict-reason-box";
        }
    }

    // Defects table
    if (defectCount > 0) {
        defectsTableContainer.style.display = "block";
        defectsListBody.innerHTML = "";
        item.defects.forEach(d => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${d.class_name}</strong></td>
                <td>${(d.confidence * 100).toFixed(0)}%</td>
                <td><span class="feed-status pending" style="padding:1px 6px;font-size:9px;">${d.status}</span></td>
            `;
            defectsListBody.appendChild(tr);
        });
    } else {
        defectsTableContainer.style.display = "none";
    }

    overridePass.checked = item.status === "PASS";
    overrideFail.checked = item.status === "FAIL";
    operatorNotes.value = item.operator_notes || "";
    btnSaveOverride.disabled = false;
}

function hideConsole() {
    overrideFormContainer.style.display = "none";
    overridePlaceholder.style.display = "flex";
}

// 8. Bounding Box Draw Overlay
function handleImageLoaded() {
    if (currentInspection && currentInspection.defects) {
        drawDefects(currentInspection.defects);
    }
}

function drawDefects(defects) {
    if (!pcbImage.complete || pcbImage.naturalWidth === 0) return;

    defectCanvas.width = pcbImage.clientWidth;
    defectCanvas.height = pcbImage.clientHeight;

    const ctx = defectCanvas.getContext("2d");
    ctx.clearRect(0, 0, defectCanvas.width, defectCanvas.height);

    const scaleX = pcbImage.clientWidth / pcbImage.naturalWidth;
    const scaleY = pcbImage.clientHeight / pcbImage.naturalHeight;

    // Color map by severity
    const colorMap = {
        missing: "#ef4444", bridge: "#f43f5e", tombstone: "#f97316",
        misaligned: "#f59e0b", default: "#f43f5e"
    };

    defects.forEach(defect => {
        const x = defect.x_min * scaleX;
        const y = defect.y_min * scaleY;
        const w = (defect.x_max - defect.x_min) * scaleX;
        const h = (defect.y_max - defect.y_min) * scaleY;
        const color = colorMap[defect.class_name] || colorMap.default;

        ctx.shadowBlur = 10;
        ctx.shadowColor = color;
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, w, h);
        ctx.shadowBlur = 0;

        const label = `${defect.class_name} (${(defect.confidence * 100).toFixed(0)}%)`;
        ctx.font = "600 11px Inter, sans-serif";
        const textWidth = ctx.measureText(label).width;

        ctx.fillStyle = color + "d9";
        ctx.fillRect(x, y - 22, textWidth + 10, 22);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, x + 5, y - 7);
    });
}

// 9. Trigger scan via REST API (MockCamera)
async function triggerScan() {
    triggerScanBtn.disabled = true;
    const originalHTML = triggerScanBtn.innerHTML;
    triggerScanBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Triggering...`;

    try {
        const randomBoardId = `PCB-${Math.floor(1000 + Math.random() * 9000)}`;
        const response = await fetch(`${API_BASE_URL}/api/inspections/trigger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ board_id: randomBoardId })
        });
        if (!response.ok) console.error("Trigger scan failed:", await response.text());
    } catch (err) {
        console.error("Error triggering scan:", err);
    } finally {
        setTimeout(() => {
            triggerScanBtn.disabled = false;
            triggerScanBtn.innerHTML = originalHTML;
        }, 1000);
    }
}

// 10. Upload Modal
function openUploadModal() {
    uploadFile = null;
    uploadFileInput.value = "";
    uploadBoardId.value = "";
    uploadPreview.classList.remove("active");
    btnSubmitUpload.disabled = true;
    uploadModal.classList.add("active");
    uploadBoardId.focus();
}

function closeUploadModal() {
    uploadModal.classList.remove("active");
}

function handleFileSelected(e) {
    const file = e.target.files[0];
    if (file) setUploadFile(file);
}

function setUploadFile(file) {
    const allowedTypes = ["image/jpeg", "image/png", "image/jpg"];
    if (!allowedTypes.includes(file.type)) {
        alert("Unsupported file type. Please upload a JPEG or PNG image.");
        return;
    }
    if (file.size > 20 * 1024 * 1024) {
        alert("File too large. Maximum size is 20 MB.");
        return;
    }

    uploadFile = file;

    // Preview
    const reader = new FileReader();
    reader.onload = (e) => { uploadPreviewImg.src = e.target.result; };
    reader.readAsDataURL(file);
    uploadPreviewName.textContent = file.name;
    uploadPreviewSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    uploadPreview.classList.add("active");

    btnSubmitUpload.disabled = false;
}

async function submitUpload() {
    if (!uploadFile) return;

    const boardId = uploadBoardId.value.trim() || `PCB-${Math.floor(1000 + Math.random() * 9000)}`;

    btnSubmitUpload.disabled = true;
    btnSubmitUpload.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Uploading...`;

    try {
        const formData = new FormData();
        formData.append("board_id", boardId);
        formData.append("file", uploadFile);

        const response = await fetch(`${API_BASE_URL}/api/inspections/upload`, {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            closeUploadModal();
        } else {
            const err = await response.json().catch(() => ({ detail: "Unknown error" }));
            alert(`Upload failed: ${err.detail || "Server error"}`);
        }
    } catch (err) {
        console.error("Error uploading image:", err);
        alert("Upload failed. Please check server connection.");
    } finally {
        btnSubmitUpload.disabled = false;
        btnSubmitUpload.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Start Inspection`;
    }
}

// 11. Submit Operator Override Verdict
async function submitOverride(event) {
    event.preventDefault();
    if (!currentInspection) return;

    const verdictInput = document.querySelector('input[name="verdict"]:checked');
    if (!verdictInput) { alert("Please select a verdict."); return; }

    const verdict = verdictInput.value;
    const notes = operatorNotes.value;
    btnSaveOverride.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/inspections/${currentInspection.id}/override`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operator_verdict: verdict, operator_notes: notes })
        });

        if (response.ok) {
            const updated = await response.json();
            const idx = inspections.findIndex(item => item.id === updated.id);
            if (idx !== -1) {
                inspections[idx] = { ...inspections[idx], ...updated };
                currentInspection = inspections[idx];
                renderFeed();
                updateMetrics();
                displayInspection(currentInspection);
            }
        } else {
            alert("Failed to save override verdict.");
        }
    } catch (err) {
        console.error("Error saving override verdict:", err);
    } finally {
        btnSaveOverride.disabled = false;
    }
}

// 12. Update Metrics counters
function updateMetrics() {
    const total = inspections.length;
    metricTotal.textContent = total;

    if (total === 0) { metricYield.textContent = "0%"; return; }

    const passes = inspections.filter(item => item.status === "PASS").length;
    metricYield.textContent = `${((passes / total) * 100).toFixed(1)}%`;
}
