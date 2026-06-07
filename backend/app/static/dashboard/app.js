// ============ STATE ============
let selectedCameraId = null;
let selectedCamera = null;
let cameras = [];
let isAnalyzing = false;
let autoAnalyzeTimer = null;
let aiFeedTimer = null;
let aiFeedActive = false;
let feedMode = "preprocessed";
let lastInferenceMs = 0;
let activeRequestSeq = 0;
let allCameraAnalysisActive = false;
let allCameraAnalysisTimer = null;
let allCameraAnalysisIndex = 0;
let isPrimingAllCameras = false;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 3;

const cameraPlaybackState = {};
const cameraStats = {};

const MIN_AI_INTERVAL_MS = 500;
const AI_SAFETY_MARGIN_MS = 150;
const AI_FEED_DELAY_WARNING_MS = 3000;
const ALL_CAMERA_SAFETY_MARGIN_MS = 250;
const AI_FEED_PLACEHOLDER_SRC = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";

const FLOW_NODES = {
  cam_checkin: {
    order: 1,
    shortName: "Check-in",
    area: "Public landside",
    position: { x: 15, y: 15 },
    capacity: 500
  },
  cam_access: {
    order: 2,
    shortName: "Access Control",
    area: "Gate validation",
    position: { x: 35, y: 20 },
    capacity: 220
  },
  cam_security: {
    order: 3,
    shortName: "Security",
    area: "Screening lanes",
    position: { x: 50, y: 40 },
    capacity: 500
  },
  cam_to_t4: {
    order: 4,
    shortName: "T4 Corridor",
    area: "Sterile corridor",
    position: { x: 65, y: 55 },
    capacity: 260
  },
  cam_boarding_gate: {
    order: 5,
    shortName: "Boarding Hall",
    area: "Gate lounge",
    position: { x: 80, y: 70 },
    capacity: 700
  },
  cam_jetbridge: {
    order: 6,
    shortName: "Jet Bridge",
    area: "Aircraft funnel",
    position: { x: 95, y: 80 },
    capacity: 120
  },
  cam_checkin_3_8: {
    order: 7,
    shortName: "Check-in 3-8",
    area: "Check-in overview",
    position: { x: 24, y: 18 },
    capacity: 620
  },
  cam_egate_business: {
    order: 8,
    shortName: "E Gate 13-14",
    area: "Business gate lounge",
    position: { x: 94, y: 58 },
    capacity: 260
  }
};

const FLOW_EDGES = [
  ["cam_checkin", "cam_access"],
  ["cam_checkin_3_8", "cam_access"],
  ["cam_access", "cam_security"],
  ["cam_security", "cam_to_t4"],
  ["cam_to_t4", "cam_boarding_gate"],
  ["cam_boarding_gate", "cam_egate_business"],
  ["cam_egate_business", "cam_jetbridge"]
];

const FALLBACK_CAMERAS = [
  { id: "cam_checkin", name: "1. Check-in", video_found: true, video_url: "/api/cameras/cam_checkin/video", preprocessed_video_url: "/api/cameras/cam_checkin/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_access", name: "2. Control acces", video_found: true, video_url: "/api/cameras/cam_access/video", preprocessed_video_url: "/api/cameras/cam_access/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_security", name: "3. Control de securitate", video_found: true, video_url: "/api/cameras/cam_security/video", preprocessed_video_url: "/api/cameras/cam_security/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_to_t4", name: "4. Spre sala de pasageri T4", video_found: true, video_url: "/api/cameras/cam_to_t4/video", preprocessed_video_url: "/api/cameras/cam_to_t4/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_boarding_gate", name: "5. Sala pasageri + poarta imbarcare", video_found: true, video_url: "/api/cameras/cam_boarding_gate/video", preprocessed_video_url: "/api/cameras/cam_boarding_gate/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_jetbridge", name: "6. Interior burduf", video_found: true, video_url: "/api/cameras/cam_jetbridge/video", preprocessed_video_url: "/api/cameras/cam_jetbridge/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_checkin_3_8", name: "7. Check-in 3-8 Ansamblu", video_found: true, video_url: "/api/cameras/cam_checkin_3_8/video", preprocessed_video_url: "/api/cameras/cam_checkin_3_8/preprocessed-video", preprocessed_video_found: true },
  { id: "cam_egate_business", name: "8. E Gate 13-14 Business", video_found: true, video_url: "/api/cameras/cam_egate_business/video", preprocessed_video_url: "/api/cameras/cam_egate_business/preprocessed-video", preprocessed_video_found: true }
];

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setDebug(label, value) {
  try {
    const targets = {
      "JS Loaded": "jsLoaded",
      jsLoaded: "jsLoaded",
      Cameras: "camerasCount",
      camerasCount: "camerasCount",
      Selected: "selectedCameraDebug",
      selectedCameraDebug: "selectedCameraDebug",
      "Last Error": "lastError",
      lastError: "lastError"
    };
    const node = el(targets[label]);
    if (node) node.textContent = String(value);
  } catch (error) {
    console.warn("Debug update failed:", label, error);
  }
}

function showError(message, nonIntrusive = false) {
  const text = message || "Unknown error";
  const errorBox = el("errorMessage");
  const feedWarning = el("feedWarning");

  if (nonIntrusive && feedWarning) {
    feedWarning.textContent = text;
    feedWarning.style.display = "block";
  } else if (errorBox) {
    errorBox.textContent = text;
    errorBox.style.display = "block";
  }

  setDebug("Last Error", text);
}

function clearError() {
  const errorBox = el("errorMessage");
  const feedWarning = el("feedWarning");
  if (errorBox) {
    errorBox.textContent = "";
    errorBox.style.display = "none";
  }
  if (feedWarning) {
    feedWarning.textContent = "";
    feedWarning.style.display = "none";
  }
  setDebug("Last Error", "None");
}

function showLoading(show) {
  const loading = el("loading");
  if (loading) {
    loading.style.display = show ? "flex" : "none";
    // If it's a first-time load, it might take a while due to server spin-up
    const loadingText = loading.querySelector("p");
    if (loadingText) {
      loadingText.textContent = show ? "Analyzing frame (server may be warming up)..." : "Analyzing frame...";
    }
  }

  const analyzeBtn = el("analyzeBtn");
  const manualAnalyzeBtn = el("manualAnalyzeBtn");
  if (analyzeBtn) analyzeBtn.disabled = show || !selectedCameraId;
  if (manualAnalyzeBtn) manualAnalyzeBtn.disabled = show || !selectedCameraId;
}

function setVideoStatus(message, isError = false) {
  const status = el("videoStatus") || el("videoInfo");
  if (!status) return;
  status.textContent = message || "";
  status.style.display = message ? "block" : "none";
  status.classList.toggle("error", Boolean(isError));
}

function cameraUrl(cameraId) {
  return `/api/cameras/${cameraId}/video`;
}

function preprocessedCameraUrl(cameraId) {
  return `/api/cameras/${cameraId}/preprocessed-video`;
}

function videoSourceForMode(camera, mode = getFeedMode()) {
  if (mode === "preprocessed" && camera.preprocessed_video_url && camera.preprocessed_video_found !== false) {
    return {
      src: camera.preprocessed_video_url,
      status: "Playing preprocessed AI video",
      missingProcessed: false
    };
  }

  return {
    src: camera.video_url || cameraUrl(camera.id),
    status: mode === "preprocessed" ? "Preprocessed video missing; using raw local video" : "Playing raw local video",
    missingProcessed: mode === "preprocessed"
  };
}

function getFeedMode() {
  const modeSelect = el("feedMode");
  const value = modeSelect ? modeSelect.value : feedMode;
  if (value === "raw") return "raw";
  if (value === "ai") return "ai";
  return "preprocessed";
}

function getMinimumAiIntervalMs() {
  const input = el("aiFeedIntervalMs");
  const parsed = input ? parseInt(input.value, 10) : MIN_AI_INTERVAL_MS;
  const interval = Math.max(MIN_AI_INTERVAL_MS, Number.isFinite(parsed) ? parsed : MIN_AI_INTERVAL_MS);
  if (input && String(interval) !== input.value) input.value = String(interval);
  return interval;
}

function graphToMapPosition(position) {
  return {
    x: position.x,
    y: 100 - position.y
  };
}

function statsFromResult(result) {
  const counts = result.counts || {};
  const totalPeople = Number(result.status?.total_people ?? Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0));
  return {
    total_people: Number.isFinite(totalPeople) ? totalPeople : 0,
    risk_level: result.status?.risk_level || riskFromTotal(totalPeople),
    counts,
    detections_count: Number(result.detections_count || 0),
    summary: result.status?.summary || "",
    performance: result.performance || {},
    timestamp_seconds: Number(result.timestamp_seconds || 0),
    last_updated: Date.now()
  };
}

function riskFromTotal(totalPeople) {
  if (!Number.isFinite(totalPeople)) return "unknown";
  if (totalPeople >= 16) return "high";
  if (totalPeople >= 6) return "medium";
  return "low";
}

function heatClassForStats(stats) {
  if (!stats) return "heat-unknown";
  return `heat-${riskFromTotal(stats.total_people)}`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function interpolateColor(start, end, ratio) {
  const t = clamp(ratio, 0, 1);
  const a = start.match(/\w\w/g).map((part) => parseInt(part, 16));
  const b = end.match(/\w\w/g).map((part) => parseInt(part, 16));
  const mixed = a.map((value, index) => Math.round(value + (b[index] - value) * t));
  return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
}

function pressureScore(totalPeople) {
  if (!Number.isFinite(Number(totalPeople))) return null;
  return clamp(Number(totalPeople) / 24, 0, 1);
}

function heatColorForTotal(totalPeople) {
  const score = pressureScore(totalPeople);
  if (score === null) return "#4f8cff";
  if (score < 0.25) return interpolateColor("22d3ee", "1fe37c", score / 0.25);
  if (score < 0.5) return interpolateColor("1fe37c", "facc15", (score - 0.25) / 0.25);
  if (score < 0.75) return interpolateColor("facc15", "ff8a00", (score - 0.5) / 0.25);
  return interpolateColor("ff8a00", "ff3b30", (score - 0.75) / 0.25);
}

function heatGlowForTotal(totalPeople) {
  const score = pressureScore(totalPeople);
  if (score === null) return "rgba(79, 140, 255, 0.45)";
  if (score < 0.35) return "rgba(31, 227, 124, 0.45)";
  if (score < 0.7) return "rgba(255, 176, 32, 0.55)";
  return "rgba(255, 59, 48, 0.72)";
}

function heatColorForStats(stats) {
  return heatColorForTotal(stats?.total_people);
}

function backendStatusFromElapsed(elapsedMs) {
  if (!Number.isFinite(elapsedMs)) return "OK";
  if (elapsedMs < 700) return "Fast";
  if (elapsedMs < 1800) return "OK";
  return "Slow";
}

function formatClock(seconds) {
  const safeSeconds = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  const minutes = Math.floor(safeSeconds / 60);
  const wholeSeconds = Math.floor(safeSeconds % 60);
  return `${minutes}:${String(wholeSeconds).padStart(2, "0")}`;
}

function updateVideoTime(seconds) {
  const safeSeconds = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  const currentVideoTime = el("currentVideoTime");
  const videoTime = el("videoTime");
  const timestampInput = el("timestampInput");

  if (currentVideoTime) currentVideoTime.textContent = safeSeconds.toFixed(1);
  if (videoTime) videoTime.textContent = formatClock(safeSeconds);
  if (timestampInput) timestampInput.value = safeSeconds.toFixed(1);
  updateFeedOverlayStats();
}

function updatePerformancePanel(inferenceMs = null, backendStatus = null, nextDelayMs = null) {
  const currentMode = getFeedMode();
  const feedModeStatus = el("feedModeStatus");
  const aiIntervalStatus = el("aiIntervalStatus");
  const lastInferenceNode = el("lastInferenceMs");
  const effectiveFps = el("effectiveFps");
  const backendStatusNode = el("backendStatus");
  const nextFrameNode = el("nextFrameInMs");

  if (feedModeStatus) {
    if (currentMode === "preprocessed") feedModeStatus.textContent = "Preprocessed";
    else if (currentMode === "ai") feedModeStatus.textContent = "Live AI";
    else feedModeStatus.textContent = "Raw";
  }
  
  if (aiIntervalStatus) {
    if (currentMode === "preprocessed") aiIntervalStatus.textContent = "Video";
    else if (currentMode === "ai") aiIntervalStatus.textContent = `Adaptive, min ${getMinimumAiIntervalMs()} ms`;
    else aiIntervalStatus.textContent = "Manual";
  }

  if (Number.isFinite(inferenceMs)) {
    const rounded = Math.round(inferenceMs);
    lastInferenceMs = rounded;
    if (lastInferenceNode) lastInferenceNode.textContent = `${rounded} ms`;
    if (effectiveFps) effectiveFps.textContent = inferenceMs > 0 ? (1000 / inferenceMs).toFixed(2) : "-";
  }

  if (backendStatusNode && backendStatus) backendStatusNode.textContent = backendStatus;
  if (nextFrameNode && Number.isFinite(nextDelayMs)) nextFrameNode.textContent = `${Math.round(nextDelayMs)} ms`;
  updateFeedOverlayStats();
}

function normalizeCamera(camera, index) {
  const fallback = FALLBACK_CAMERAS.find((item) => item.id === camera.id) || FALLBACK_CAMERAS[index] || {};
  const id = camera.id || fallback.id || `camera_${index + 1}`;
  const flow = FLOW_NODES[id] || {};
  const graphPosition = flow.position || camera.map_position || fallback.map_position || { x: 20 + index * 10, y: 20 };
  const mapPosition = graphToMapPosition(graphPosition);

  return {
    ...fallback,
    ...camera,
    id,
    name: camera.name || fallback.name || `Camera ${index + 1}`,
    shortName: flow.shortName || camera.name || fallback.name || `Camera ${index + 1}`,
    area: flow.area || "",
    order: flow.order || index + 1,
    capacity: flow.capacity || 300,
    graph_position: graphPosition,
    map_position: mapPosition,
    video_url: camera.video_url || cameraUrl(id),
    preprocessed_video_url: camera.preprocessed_video_url || fallback.preprocessed_video_url || preprocessedCameraUrl(id),
    preprocessed_video_found: camera.preprocessed_video_found ?? fallback.preprocessed_video_found ?? true
  };
}

function normalizeCameras(source) {
  return source.map((camera, index) => normalizeCamera(camera || {}, index));
}

async function loadCameras() {
  setDebug("Last Error", "Loading cameras...");

  try {
    const response = await fetch("/api/cameras", { cache: "no-store" });
    if (!response.ok) throw new Error(`Camera API returned ${response.status}`);

    const data = await response.json();
    const loadedCameras = Array.isArray(data) ? data : (data && Array.isArray(data.cameras) ? data.cameras : []);
    if (!loadedCameras.length) throw new Error("API returned zero cameras");

    cameras = normalizeCameras(loadedCameras);
    clearError();
  } catch (error) {
    console.warn("Using fallback cameras:", error);
    cameras = normalizeCameras(FALLBACK_CAMERAS);
    setDebug("Last Error", `Using fallback cameras: ${error.message}`);
  }

  setDebug("Cameras", cameras.length);
  renderCameraMarkers();
  renderCameraListButtons();
  renderCorridors();
  if (!selectedCameraId && cameras.length) selectCamera(cameras[0]);
  primeAllCameraStats();
}

function getCameraById(cameraId) {
  return cameras.find((camera) => camera.id === cameraId) || null;
}

function getOrCreateMarkerContainer() {
  let container = el("cameraButtons") || el("camera-overlay") || el("cameraOverlay") || document.querySelector(".camera-overlay");
  if (container) return container;

  const mapWrapper = document.querySelector(".map-wrapper") || (el("mapImage") ? el("mapImage").parentElement : null);
  if (!mapWrapper) {
    showError("Map wrapper missing; cannot render camera markers");
    return null;
  }

  mapWrapper.style.position = "relative";
  container = document.createElement("div");
  container.id = "cameraButtons";
  container.className = "camera-overlay";
  mapWrapper.appendChild(container);
  return container;
}

function renderCameraMarkers() {
  const container = getOrCreateMarkerContainer();
  if (!container) return;

  container.innerHTML = "";
  container.style.position = "absolute";
  container.style.inset = "0";
  container.style.pointerEvents = "none";

  cameras.forEach((camera) => {
    const stats = cameraStats[camera.id];
    const total = stats ? stats.total_people : null;
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `camera-marker ${heatClassForStats(stats)}`;
    marker.dataset.cameraId = camera.id;
    marker.title = `${camera.name} - ${total ?? "unknown"} people`;
    marker.style.left = `${camera.map_position.x}%`;
    marker.style.top = `${camera.map_position.y}%`;
    marker.style.setProperty("--heat-size", `${markerSizeForTotal(total)}px`);
    marker.style.setProperty("--heat-color", heatColorForTotal(total));
    marker.style.setProperty("--heat-glow", heatGlowForTotal(total));
    marker.style.setProperty("--heat-text", riskFromTotal(Number(total)) === "high" ? "#fff" : "#06101a");
    marker.innerHTML = `
      <span class="marker-cam">CAM ${camera.order}</span>
      <span class="marker-count">${total ?? "-"}</span>
    `;
    marker.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      selectCamera(camera);
    });
    container.appendChild(marker);
  });

  highlightSelectedCamera();
}

function markerSizeForTotal(totalPeople) {
  if (!Number.isFinite(Number(totalPeople))) return 46;
  return Math.max(46, Math.min(78, 46 + Number(totalPeople)));
}

function renderCorridors() {
  const svg = el("mapCorridors");
  if (!svg) return;

  svg.innerHTML = "";

  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const filter = document.createElementNS("http://www.w3.org/2000/svg", "filter");
  filter.setAttribute("id", "corridorGlow");
  filter.setAttribute("x", "-35%");
  filter.setAttribute("y", "-35%");
  filter.setAttribute("width", "170%");
  filter.setAttribute("height", "170%");
  filter.innerHTML = `
    <feGaussianBlur stdDeviation="1.2" result="blur"></feGaussianBlur>
    <feMerge>
      <feMergeNode in="blur"></feMergeNode>
      <feMergeNode in="SourceGraphic"></feMergeNode>
    </feMerge>
  `;
  defs.appendChild(filter);
  svg.appendChild(defs);

  FLOW_EDGES.forEach(([fromId, toId]) => {
    const from = getCameraById(fromId);
    const to = getCameraById(toId);
    if (!from || !to) return;

    const fromStats = cameraStats[fromId];
    const toStats = cameraStats[toId];
    const maxPeople = Math.max(Number(fromStats?.total_people || 0), Number(toStats?.total_people || 0));
    const pressure = riskFromTotal(maxPeople);
    const width = Math.max(2.2, Math.min(7.2, 2.2 + maxPeople / 6));
    const fromColor = heatColorForTotal(fromStats?.total_people);
    const toColor = heatColorForTotal(toStats?.total_people);
    const ids = `${fromId}-${toId}`.replace(/[^a-zA-Z0-9_-]/g, "_");
    const gradientId = `corridorGradient-${ids}`;
    const markerId = `corridorArrow-${ids}`;

    const gradient = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
    gradient.setAttribute("id", gradientId);
    gradient.setAttribute("gradientUnits", "userSpaceOnUse");
    gradient.setAttribute("x1", from.map_position.x);
    gradient.setAttribute("y1", from.map_position.y);
    gradient.setAttribute("x2", to.map_position.x);
    gradient.setAttribute("y2", to.map_position.y);
    gradient.innerHTML = `
      <stop offset="0%" stop-color="${fromColor}"></stop>
      <stop offset="52%" stop-color="${heatColorForTotal(maxPeople)}"></stop>
      <stop offset="100%" stop-color="${toColor}"></stop>
    `;
    defs.appendChild(gradient);

    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", markerId);
    marker.setAttribute("viewBox", "0 0 12 12");
    marker.setAttribute("refX", "10");
    marker.setAttribute("refY", "6");
    marker.setAttribute("markerWidth", "3.8");
    marker.setAttribute("markerHeight", "3.8");
    marker.setAttribute("orient", "auto");
    marker.innerHTML = `<path d="M1,2 L10.5,6 L1,10 L3.2,6 Z" fill="${toColor}" stroke="rgba(255,255,255,0.72)" stroke-width="0.55"></path>`;
    defs.appendChild(marker);

    const midX = (from.map_position.x + to.map_position.x) / 2;
    const midY = (from.map_position.y + to.map_position.y) / 2;
    const curveOffset = Math.max(-8, Math.min(8, (to.map_position.x - from.map_position.x) * 0.08));
    const d = `M ${from.map_position.x} ${from.map_position.y} Q ${midX + curveOffset} ${midY - 4} ${to.map_position.x} ${to.map_position.y}`;

    const glow = document.createElementNS("http://www.w3.org/2000/svg", "path");
    glow.setAttribute("d", d);
    glow.setAttribute("class", `flow-corridor-glow corridor-${pressure}`);
    glow.setAttribute("stroke", `url(#${gradientId})`);
    glow.setAttribute("stroke-width", width + 5);
    svg.appendChild(glow);

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    path.setAttribute("class", `flow-corridor corridor-${pressure}`);
    path.setAttribute("stroke", `url(#${gradientId})`);
    path.setAttribute("stroke-width", width);
    path.setAttribute("marker-end", `url(#${markerId})`);
    svg.appendChild(path);
  });
}

function corridorPressure(fromStats, toStats) {
  const risks = [fromStats, toStats].map((stats) => stats ? riskFromTotal(stats.total_people) : "unknown");
  if (risks.includes("high")) return "high";
  if (risks.includes("medium")) return "medium";
  if (risks.every((risk) => risk === "low")) return "low";
  return "unknown";
}

function getOrCreateListContainer() {
  let container = el("cameraListButtons") || el("camera-list") || el("cameraList") || document.querySelector(".camera-list");
  if (container) return container;

  const mapSection = document.querySelector(".map-section") || document.body;
  const section = document.createElement("div");
  section.className = "camera-list-section";
  const heading = document.createElement("h3");
  heading.textContent = "Cameras";
  section.appendChild(heading);
  container = document.createElement("div");
  container.id = "cameraListButtons";
  section.appendChild(container);
  mapSection.appendChild(section);
  return container;
}

function renderCameraListButtons() {
  const container = getOrCreateListContainer();
  if (!container) return;

  container.innerHTML = "";
  cameras.forEach((camera) => {
    const stats = cameraStats[camera.id];
    const total = stats ? stats.total_people : "-";
    const button = document.createElement("button");
    button.type = "button";
    button.className = `camera-list-btn ${heatClassForStats(stats)}`;
    button.dataset.cameraId = camera.id;
    button.innerHTML = `
      <span>${escapeHtml(camera.order)}. ${escapeHtml(camera.shortName)}</span>
      <strong>${escapeHtml(total)}</strong>
    `;
    button.addEventListener("click", () => selectCamera(camera));
    container.appendChild(button);
  });

  highlightSelectedCamera();
}

function refreshMapHeatmap() {
  renderCameraMarkers();
  renderCameraListButtons();
  renderCorridors();
}

function highlightSelectedCamera() {
  document.querySelectorAll(".camera-marker, .camera-list-btn").forEach((button) => {
    button.classList.toggle("selected", button.dataset.cameraId === selectedCameraId);
  });
}

function resetAiFeedImage() {
  const image = el("aiFeedImage");
  if (!image) return;
  image.src = AI_FEED_PLACEHOLDER_SRC;
  image.dataset.hasFrame = "false";
}

function updateAiFeedImage(result) {
  const image = el("aiFeedImage");
  if (!image || !result?.annotated_frame_url) return;
  const separator = result.annotated_frame_url.includes("?") ? "&" : "?";
  image.src = `${result.annotated_frame_url}${separator}t=${Date.now()}`;
  image.dataset.hasFrame = "true";
  
  const currentMode = getFeedMode();
  image.style.display = currentMode === "ai" ? "block" : "none";
}

function updateFeedVisibility() {
  feedMode = getFeedMode();
  const video = el("cameraVideo");
  const image = el("aiFeedImage");
  const overlay = el("feedOverlayStats");
  const analysisContent = el("analysisContent");

  const isLiveAiImageMode = feedMode === "ai";
  const isVideoMode = feedMode === "raw" || feedMode === "preprocessed";

  if (video) {
    video.loop = true;
    video.muted = true;
    video.style.display = isVideoMode ? "block" : "none";
    video.controls = feedMode === "raw";
  }

  if (image) {
    if (!image.getAttribute("src")) resetAiFeedImage();
    image.style.display = isLiveAiImageMode ? "block" : "none";
  }

  if (overlay) overlay.style.display = "block";
  if (analysisContent) analysisContent.style.display = (feedMode === "ai" || feedMode === "preprocessed") ? "none" : "flex";
  updatePerformancePanel(lastInferenceMs || null, null, null);
  updateFeedOverlayStats();
}

function updateFeedOverlayStats() {
  const overlay = el("feedOverlayStats");
  if (!overlay) return;

  const stats = selectedCameraId ? cameraStats[selectedCameraId] : null;
  const video = el("cameraVideo");
  const currentTime = video && Number.isFinite(video.currentTime) ? video.currentTime : Number(stats?.timestamp_seconds || 0);
  const total = stats ? stats.total_people : "-";
  const risk = stats ? String(stats.risk_level || riskFromTotal(stats.total_people)).toUpperCase() : "UNKNOWN";
  const perf = stats?.performance || {};
  const inference = Number(perf.inference_ms || lastInferenceMs || 0);
  const fps = Number(perf.effective_fps || (inference > 0 ? 1000 / inference : 0));
  const counts = stats?.counts || {};
  const chips = Object.keys(counts).length ? Object.entries(counts) : [["waiting", "-"], ["outside", "-"]];

  const modeLabel = feedMode === "preprocessed" ? "PREPROCESSED FEED" : (feedMode === "ai" ? "AI FEED" : "RAW FEED");

  overlay.innerHTML = `
    <div class="feed-overlay-top">
      <div>
        <div class="overlay-camera">${escapeHtml(selectedCamera?.shortName || selectedCamera?.name || "No Camera")}</div>
        <div class="overlay-sub">CAM ${escapeHtml(selectedCamera?.order || "-")} - ${modeLabel} - ${formatClock(currentTime)}</div>
      </div>
      <div class="overlay-metrics">
        <span>People <strong>${escapeHtml(total)}</strong></span>
        <span>Risk <strong class="risk-${escapeHtml(String(risk).toLowerCase())}">${escapeHtml(risk)}</strong></span>
        <span>YOLO <strong>${inference ? `${Math.round(inference)} ms` : "-"}</strong></span>
        <span>FPS <strong>${fps ? fps.toFixed(2) : "-"}</strong></span>
      </div>
    </div>
    <div class="feed-overlay-bottom">
      ${chips.map(([zone, count]) => `<span class="zone-chip">${escapeHtml(zone)} <strong>${escapeHtml(count)}</strong></span>`).join("")}
    </div>
  `;
}

function updateCameraStatsFromResult(result) {
  if (!result?.camera_id) return;
  cameraStats[result.camera_id] = statsFromResult(result);
  refreshMapHeatmap();
  updateFeedOverlayStats();
}

function selectCamera(camera) {
  try {
    const video = el("cameraVideo");
    if (selectedCameraId && selectedCameraId !== camera.id && video && Number.isFinite(video.currentTime)) {
      cameraPlaybackState[selectedCameraId] = video.currentTime;
    }

    const previousCameraId = selectedCameraId;
    if (previousCameraId !== camera.id) {
      activeRequestSeq++;
      stopAiFeedLoop();
      resetAiFeedImage();
    }

    selectedCameraId = camera.id;
    selectedCamera = camera;

    const cameraName = el("cameraName");
    if (cameraName) cameraName.textContent = camera.name;

    const selectedDebug = el("selectedCameraDebug");
    if (selectedDebug) selectedDebug.textContent = `${camera.shortName} - ${camera.area}`;

    const videoPanel = el("videoPanel");
    if (videoPanel) videoPanel.style.display = "block";

    const analyzeBtn = el("analyzeBtn");
    const manualAnalyzeBtn = el("manualAnalyzeBtn");
    if (analyzeBtn) analyzeBtn.disabled = false;
    if (manualAnalyzeBtn) manualAnalyzeBtn.disabled = false;

    clearError();
    highlightSelectedCamera();
    updateFeedVisibility();

    if (previousCameraId !== camera.id) switchVideoToCamera(camera);
    if (getFeedMode() === "ai") startAiFeedLoop();
  } catch (error) {
    showError(`Camera selection failed: ${error.message}`);
  }
}

function switchVideoToCamera(camera) {
  const video = el("cameraVideo");
  if (!video) {
    setVideoStatus("Video player not found", true);
    return;
  }

  const resumeTime = cameraPlaybackState[camera.id] || 0;
  const mode = getFeedMode();
  const source = videoSourceForMode(camera, mode);
  const src = source.src;

  setVideoStatus(mode === "preprocessed" ? "Loading preprocessed AI video..." : "Loading local video...");
  updateVideoTime(resumeTime);

  video.muted = true;
  video.autoplay = true;
  video.loop = true;
  video.playsInline = true;
  video.setAttribute("muted", "");
  video.setAttribute("autoplay", "");
  video.setAttribute("loop", "");
  video.setAttribute("playsinline", "");

  video.onloadedmetadata = () => {
    if (selectedCameraId !== camera.id) return;
    const duration = Number(video.duration);
    if (resumeTime > 0 && (!Number.isFinite(duration) || resumeTime < duration)) {
      try {
        video.currentTime = resumeTime;
      } catch (error) {
        console.warn("Could not restore video time:", error);
      }
    }

    updateVideoTime(video.currentTime);
    const playPromise = video.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise
        .then(() => {
          const currentMode = getFeedMode();
          if (currentMode === "ai") {
            setVideoStatus("AI feed warming up...");
            startAiFeedLoop();
          } else {
            setVideoStatus(source.status, source.missingProcessed);
          }
        })
        .catch(() => setVideoStatus("Press play to start video"));
    }
  };

  video.ontimeupdate = () => {
    if (selectedCameraId !== camera.id) return;
    updateVideoTime(video.currentTime);
  };

  video.onerror = () => {
    if (selectedCameraId !== camera.id) return;
    setVideoStatus("Video file missing or cannot be played", true);
  };

  video.onended = () => {
    if (selectedCameraId !== camera.id) return;
    video.currentTime = 0;
    video.play().catch(() => {});
  };

  video.src = src;
  video.load();
}

function readManualTimestamp() {
  const timestampInput = el("timestampInput");
  const parsed = timestampInput ? parseFloat(timestampInput.value) : 0;
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

async function analyzeSelectedCamera(useManualTimestamp = false, options = {}) {
  const updateMainFeed = options.updateMainFeed || false;
  const updateAnalysisContent = options.updateAnalysisContent ?? !updateMainFeed;
  const showBusy = options.showLoading !== false;
  const silent = options.silent || false;

  if (!selectedCameraId) {
    if (!silent) showError("No camera selected");
    return null;
  }

  if (isAnalyzing) return null;

  const requestCameraId = selectedCameraId;
  const requestSeq = ++activeRequestSeq;
  const video = el("cameraVideo");
  let timestamp = readManualTimestamp();
  if (!useManualTimestamp && video && Number.isFinite(video.currentTime)) {
    timestamp = video.currentTime;
  }

  timestamp = Number.isFinite(timestamp) && timestamp >= 0 ? timestamp : 0;
  const timestampInput = el("timestampInput");
  if (timestampInput) timestampInput.value = timestamp.toFixed(1);

  isAnalyzing = true;
  if (!updateMainFeed) clearError();
  if (showBusy) showLoading(true);
  if (updateMainFeed) setVideoStatus("AI processing...");

  let delayTimer = null;
  const start = performance.now();

  try {
    delayTimer = setTimeout(() => {
      if (updateMainFeed && requestCameraId === selectedCameraId) {
        setVideoStatus("AI feed throttled", true);
        showError("AI feed throttled", true);
        updatePerformancePanel(null, "Slow", null);
      }
    }, AI_FEED_DELAY_WARNING_MS);

    const isDemo = getFeedMode() === "preprocessed";
    const url = `/api/cameras/${encodeURIComponent(requestCameraId)}/analyze-snapshot?timestamp_seconds=${encodeURIComponent(timestamp)}${isDemo ? '&demo=true' : ''}`;
    const response = await fetch(url, { method: "POST", cache: "no-store" });
    const elapsed = performance.now() - start;
    clearTimeout(delayTimer);
    delayTimer = null;

    if (!response.ok) {
      let message = `Analysis failed with HTTP ${response.status}`;
      try {
        const errorBody = await response.json();
        if (typeof errorBody.detail === "string") message = errorBody.detail;
      } catch (parseError) {
        console.warn("Could not parse analysis error response:", parseError);
      }
      throw new Error(message);
    }

    const result = await response.json();
    result._client_elapsed_ms = elapsed;

    if (requestSeq !== activeRequestSeq || selectedCameraId !== requestCameraId || result.camera_id !== selectedCameraId) {
      return null;
    }

    const displayedInference = Number(result.performance?.inference_ms || elapsed);
    updatePerformancePanel(displayedInference, backendStatusFromElapsed(elapsed), null);
    updateCameraStatsFromResult(result);

    if (updateMainFeed) updateAiFeedImage(result);
    displayAnalysisResult(result, { updateAnalysisContent });

    if (timestampInput) timestampInput.value = timestamp.toFixed(1);
    if (updateMainFeed) setVideoStatus("AI feed live");
    return result;
  } catch (error) {
    updatePerformancePanel(null, "Error", null);
    if (updateMainFeed) {
      setVideoStatus(`AI feed warning: ${error.message}`, true);
      showError(`AI feed warning: ${error.message}`, true);
    } else if (!silent) {
      showError(`Analysis failed: ${error.message}`);
    }
    return null;
  } finally {
    if (delayTimer) clearTimeout(delayTimer);
    isAnalyzing = false;
    if (showBusy) showLoading(false);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setAllCameraStatus(message) {
  const autoStatus = el("autoAnalyzeStatus");
  if (autoStatus) autoStatus.textContent = message;
}

function updateAllCameraButton() {
  const button = el("allCamerasAnalyzeBtn");
  if (!button) return;
  button.classList.toggle("active", allCameraAnalysisActive);
  if (isPrimingAllCameras) {
    button.textContent = "Priming All Cameras";
  } else {
    button.textContent = allCameraAnalysisActive ? "Stop All-Camera Monitor" : "Monitor All Cameras";
  }
}

function nextBackgroundTimestamp(cameraId) {
  const previous = Number(cameraStats[cameraId]?.timestamp_seconds || 0);
  return (previous + 2) % 30;
}

async function analyzeCameraForStats(camera, timestampSeconds = 0, options = {}) {
  if (!camera || isAnalyzing) return null;

  isAnalyzing = true;
  const start = performance.now();

  try {
    const url = `/api/cameras/${encodeURIComponent(camera.id)}/analyze-snapshot?timestamp_seconds=${encodeURIComponent(timestampSeconds)}`;
    const response = await fetch(url, { method: "POST", cache: "no-store" });
    const elapsed = performance.now() - start;

    if (!response.ok) {
      let message = `Analysis failed with HTTP ${response.status}`;
      try {
        const errorBody = await response.json();
        if (typeof errorBody.detail === "string") message = errorBody.detail;
      } catch (parseError) {
        console.warn("Could not parse background analysis error:", parseError);
      }
      throw new Error(message);
    }

    const result = await response.json();
    if (result.camera_id !== camera.id) return null;

    result._client_elapsed_ms = elapsed;
    updateCameraStatsFromResult(result);
    return result;
  } catch (error) {
    if (!options.silent) showError(`Map analysis failed for ${camera.shortName}: ${error.message}`, true);
    return null;
  } finally {
    isAnalyzing = false;
  }
}

async function primeAllCameraStats() {
  if (isPrimingAllCameras || !cameras.length) return;

  isPrimingAllCameras = true;
  updateAllCameraButton();
  setAllCameraStatus("Priming map heat");

  for (const camera of cameras) {
    let waits = 0;
    while (isAnalyzing && waits < 30) {
      await sleep(250);
      waits += 1;
    }
    if (!isAnalyzing) {
      await analyzeCameraForStats(camera, 0, { silent: true });
      setAllCameraStatus(`Primed CAM ${camera.order}`);
    }
  }

  isPrimingAllCameras = false;
  updateAllCameraButton();
  setAllCameraStatus(allCameraAnalysisActive ? "All-camera monitor active" : "AI Feed ready");
  renderCorridors();
}

function stopAllCameraAnalysis() {
  allCameraAnalysisActive = false;
  if (allCameraAnalysisTimer) {
    clearTimeout(allCameraAnalysisTimer);
    allCameraAnalysisTimer = null;
  }
  updateAllCameraButton();
  setAllCameraStatus(getFeedMode() === "ai" ? "AI Feed active" : "Off");
}

function startAllCameraAnalysis() {
  if (!cameras.length) return;
  allCameraAnalysisActive = true;
  updateAllCameraButton();
  setAllCameraStatus("All-camera monitor active");
  scheduleAllCameraAnalysis(0);
}

function toggleAllCameraAnalysis() {
  if (allCameraAnalysisActive) {
    stopAllCameraAnalysis();
  } else {
    startAllCameraAnalysis();
  }
}

function scheduleAllCameraAnalysis(delayMs) {
  if (allCameraAnalysisTimer) clearTimeout(allCameraAnalysisTimer);
  if (!allCameraAnalysisActive) return;
  allCameraAnalysisTimer = setTimeout(allCameraAnalysisTick, delayMs);
}

async function allCameraAnalysisTick() {
  if (!allCameraAnalysisActive || !cameras.length) return;

  let elapsed = 600;
  if (!isAnalyzing) {
    const inactiveCameras = cameras.filter((camera) => camera.id !== selectedCameraId);
    if (inactiveCameras.length) {
      const camera = inactiveCameras[allCameraAnalysisIndex % inactiveCameras.length];
      allCameraAnalysisIndex += 1;
      setAllCameraStatus(`Scanning CAM ${camera.order}`);
      const result = await analyzeCameraForStats(camera, nextBackgroundTimestamp(camera.id), { silent: true });
      elapsed = Number(result?._client_elapsed_ms || result?.performance?.inference_ms || elapsed);
      setAllCameraStatus("All-camera monitor active");
    }
  }

  const nextDelay = Math.max(600, elapsed + ALL_CAMERA_SAFETY_MARGIN_MS);
  scheduleAllCameraAnalysis(nextDelay);
}

function displayAnalysisResult(result, options = {}) {
  const updateAnalysisContent = options.updateAnalysisContent !== false;
  const content = el("analysisContent");
  if (content && updateAnalysisContent) {
    content.innerHTML = "";
    if (result.annotated_frame_url) {
      const image = document.createElement("img");
      image.className = "annotated-frame";
      image.alt = "Annotated Frame";
      const separator = result.annotated_frame_url.includes("?") ? "&" : "?";
      image.src = `${result.annotated_frame_url}${separator}t=${Date.now()}`;
      content.appendChild(image);
    }
  }

  const status = result.status || {};
  const counts = result.counts || {};
  const totalPeople = status.total_people ?? Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0);
  const risk = String(status.risk_level || riskFromTotal(totalPeople)).toLowerCase();

  const statusPanel = el("statusPanel");
  if (statusPanel) statusPanel.style.display = "block";

  const riskLevel = el("riskLevel");
  if (riskLevel) {
    riskLevel.textContent = risk.toUpperCase();
    riskLevel.className = `value risk-${risk}`;
  }

  const totalPeopleNode = el("totalPeople");
  if (totalPeopleNode) totalPeopleNode.textContent = String(totalPeople);

  const detectionsCount = el("detectionsCount");
  if (detectionsCount) detectionsCount.textContent = String(result.detections_count ?? 0);

  const summary = el("summary");
  if (summary) summary.textContent = status.summary || "No summary returned";

  const countsPanel = el("countsPanel");
  const countsGrid = el("countsGrid");
  if (countsPanel) countsPanel.style.display = "block";
  if (countsGrid) {
    countsGrid.innerHTML = "";
    Object.entries(counts).forEach(([zone, count]) => {
      const item = document.createElement("div");
      item.className = `count-item ${zone === "outside" ? "zone-outside" : "zone-active"}`;
      item.innerHTML = `<span class="zone-name">${escapeHtml(zone)}</span><span class="zone-count">${escapeHtml(count)}</span>`;
      countsGrid.appendChild(item);
    });
  }
}

function stopAiFeedLoop() {
  aiFeedActive = false;
  if (aiFeedTimer) {
    clearTimeout(aiFeedTimer);
    aiFeedTimer = null;
  }
}

async function aiFeedTick() {
  if (!aiFeedActive || getFeedMode() !== "ai" || !selectedCameraId) return;

  if (!isAnalyzing) {
    const result = await analyzeSelectedCamera(false, {
      updateMainFeed: true,
      silent: true,
      showLoading: false
    });

    if (result) {
      consecutiveErrors = 0;
      const elapsed = Number(result?._client_elapsed_ms || result?.performance?.inference_ms || lastInferenceMs || getMinimumAiIntervalMs());
      lastInferenceMs = elapsed;
    } else {
      consecutiveErrors++;
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        setVideoStatus("AI feed stopped due to errors", true);
        showError("Too many connection errors. The server might be overwhelmed. Try refreshing or switching cameras.", true);
        stopAiFeedLoop();
        return;
      }
    }
  }

  const currentMode = getFeedMode();
  const baseInterval = getMinimumAiIntervalMs();
  const nextDelay = Math.max(baseInterval, lastInferenceMs + AI_SAFETY_MARGIN_MS);
  const backendStatus = backendStatusFromElapsed(lastInferenceMs);
  updatePerformancePanel(lastInferenceMs, backendStatus, nextDelay);

  if (backendStatus === "Slow" && currentMode === "ai") {
    setVideoStatus("AI feed throttled", true);
  } else if (aiFeedActive && currentMode === "ai" && selectedCameraId) {
    setVideoStatus("AI feed live");
  }

  if (aiFeedActive && getFeedMode() === "ai" && selectedCameraId) {
    aiFeedTimer = setTimeout(aiFeedTick, nextDelay);
  }
}

function startAiFeedLoop() {
  stopAiFeedLoop();
  updateFeedVisibility();
  const currentMode = getFeedMode();
  if (currentMode !== "ai" || !selectedCameraId) return;

  aiFeedActive = true;
  aiFeedTimer = setTimeout(aiFeedTick, 0);
}

function handleFeedModeChange() {
  feedMode = getFeedMode();
  activeRequestSeq++;
  stopAiFeedLoop();
  updateFeedVisibility();

  if (selectedCamera) switchVideoToCamera(selectedCamera);
  if (feedMode === "ai") startAiFeedLoop();

  setupAutoAnalyze();
}

function setupAutoAnalyze() {
  const autoBox = el("autoAnalyzeCheckbox");
  const autoStatus = el("autoAnalyzeStatus");
  if (!autoBox) return;

  if (autoAnalyzeTimer) {
    clearInterval(autoAnalyzeTimer);
    autoAnalyzeTimer = null;
  }

  if (getFeedMode() === "ai") {
    if (autoStatus) autoStatus.textContent = selectedCameraId ? "Live AI active" : "Live AI ready";
    return;
  }

  if (getFeedMode() === "preprocessed") {
    if (autoStatus) autoStatus.textContent = selectedCameraId ? "Preprocessed video active" : "Preprocessed ready";
    return;
  }

  if (!autoBox.checked) {
    if (autoStatus) autoStatus.textContent = "Off";
    return;
  }

  if (autoStatus) autoStatus.textContent = selectedCameraId ? "On" : "On, select a camera";
  autoAnalyzeTimer = setInterval(() => {
    if (!autoBox.checked) {
      setupAutoAnalyze();
      return;
    }
    if (!isAnalyzing && selectedCameraId) analyzeSelectedCamera(false);
  }, 5000);
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard JS loaded ai_heatmap_final");
  setDebug("JS Loaded", "\u2713");
  setDebug("Cameras", "0");
  setDebug("Selected", "None");
  setDebug("Last Error", "None");

  const feedModeSelect = el("feedMode");
  if (feedModeSelect) {
    feedModeSelect.value = "preprocessed";
    feedModeSelect.addEventListener("change", handleFeedModeChange);
  }

  const intervalInput = el("aiFeedIntervalMs");
  if (intervalInput) {
    intervalInput.value = String(getMinimumAiIntervalMs());
    intervalInput.addEventListener("change", () => {
      getMinimumAiIntervalMs();
      updatePerformancePanel(lastInferenceMs || null, null, null);
      if (getFeedMode() === "ai" && selectedCameraId) startAiFeedLoop();
    });
  }

  const video = el("cameraVideo");
  if (video) video.loop = true;
  resetAiFeedImage();
  updateFeedVisibility();
  loadCameras();

  const analyzeBtn = el("analyzeBtn");
  if (analyzeBtn) {
    analyzeBtn.addEventListener("click", () => analyzeSelectedCamera(false, { updateMainFeed: getFeedMode() === "ai" }));
  }

  const manualAnalyzeBtn = el("manualAnalyzeBtn");
  if (manualAnalyzeBtn) {
    manualAnalyzeBtn.addEventListener("click", () => analyzeSelectedCamera(true, { updateMainFeed: getFeedMode() === "ai" }));
  }

  const autoBox = el("autoAnalyzeCheckbox");
  if (autoBox) {
    autoBox.checked = false;
    autoBox.addEventListener("change", setupAutoAnalyze);
    setupAutoAnalyze();
  }

  const allCamerasAnalyzeBtn = el("allCamerasAnalyzeBtn");
  if (allCamerasAnalyzeBtn) {
    allCamerasAnalyzeBtn.addEventListener("click", toggleAllCameraAnalysis);
    updateAllCameraButton();
  }

  window.addEventListener("error", (event) => {
    showError(event.message || "Dashboard error");
  });

  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason && event.reason.message ? event.reason.message : String(event.reason || "Unhandled promise rejection");
    showError(reason);
  });
});
