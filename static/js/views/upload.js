/**
 * @fileoverview SimplyNarrated - Upload View, file upload, voice selection, and audio settings
 * @author Timothy Mallory <windsage@live.com>
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory <windsage@live.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// ============================================
// Upload View
// ============================================

function renderUploadView() {
  return `
        <div class="space-y-8">
            <!-- File Upload Zone -->
            <div class="glass rounded-2xl p-8">
                <div id="drop-zone" class="drop-zone rounded-xl p-12 text-center cursor-pointer">
                    <div id="upload-content">
                        <span class="material-symbols-outlined text-5xl text-primary mb-4">cloud_upload</span>
                        <h2 class="text-xl font-semibold mb-2">Drop your file here</h2>
                        <p class="text-gray-400 mb-4">or click to browse</p>
                        <p class="text-sm text-gray-500">Supports: TXT, PDF, ZIP (max 50MB)</p>
                    </div>
                    <div id="file-selected" class="hidden">
                        <span class="material-symbols-outlined text-5xl text-green-500 mb-4">check_circle</span>
                        <h2 class="text-xl font-semibold mb-2" id="selected-filename">filename.txt</h2>
                        <p class="text-gray-400" id="selected-filesize">1.2 MB</p>
                        <button onclick="clearFile()" class="mt-4 text-primary hover:underline">Choose different file</button>
                    </div>
                    <input type="file" id="file-input" class="hidden" accept=".txt,.pdf,.zip">
                </div>
            </div>
            
            <!-- Voice Selection -->
            <div class="glass rounded-2xl p-8">
                <h3 class="text-lg font-semibold mb-4">
                    <span class="material-symbols-outlined align-middle mr-2">record_voice_over</span>
                    Select Narrator Voice
                </h3>
              <div class="mb-4">
                <label for="model-select" class="block text-sm text-gray-400 mb-2">TTS Model</label>
                <select id="model-select" class="w-full rounded-lg bg-dark-600 border border-white/10 px-3 py-2 text-white focus:outline-none focus:border-primary transition">
                  <option value="">Select a model</option>
                </select>
              </div>
                <div id="voice-grid" class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <p class="col-span-full text-sm text-gray-500">Select a model to load available voices.</p>
                </div>
            </div>
            
            <!-- Convert Button -->
            <button id="convert-btn" onclick="startConversion()" disabled
                class="w-full py-4 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-lg transition">
                <span class="material-symbols-outlined align-middle mr-2">play_circle</span>
                Start Conversion
            </button>
        </div>
    `;
}

function initUploadView() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const modelSelect = document.getElementById("model-select");

  // Load available models
  loadModels();

  // Drag and drop handlers
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  });

  modelSelect.addEventListener("change", async (e) => {
    await selectModel(e.target.value);
  });

  updateConvertButtonState();
}

// Track currently playing audio for voice previews
let currentPreviewAudio = null;
let currentPreviewVoiceId = null;

async function loadModels() {
  try {
    const data = await api.getModels();
    const modelSelect = document.getElementById("model-select");

    modelSelect.innerHTML = `
      <option value="">Select a model</option>
      ${data.models
        .map((model) => `<option value="${model}">${model}</option>`)
        .join("")}
    `;
  } catch (error) {
    console.error("Failed to load models:", error);
  }
}

async function selectModel(model) {
  state.selectedModel = model || null;
  state.selectedVoice = null;
  stopVoicePreview();

  if (!state.selectedModel) {
    state.voices = [];
    document.getElementById("voice-grid").innerHTML =
      '<p class="col-span-full text-sm text-gray-500">Select a model to load available voices.</p>';
    updateConvertButtonState();
    return;
  }

  try {
    await api.switchModel(state.selectedModel);
    await loadVoices(state.selectedModel);
  } catch (error) {
    console.error("Failed to switch model:", error);
  }

  updateConvertButtonState();
}

async function loadVoices(model) {
  if (!model) {
    state.voices = [];
    updateConvertButtonState();
    return;
  }

  try {
    const data = await api.getVoices(model);
    state.voices = data.voices;

    const grid = document.getElementById("voice-grid");
    if (state.voices.length === 0) {
      grid.innerHTML =
        '<p class="col-span-full text-sm text-gray-500">No voices are available for this model.</p>';
      updateConvertButtonState();
      return;
    }

    grid.innerHTML = state.voices
      .map(
        (voice) => `
            <div class="voice-card glass rounded-lg p-3 cursor-pointer ${voice.id === state.selectedVoice ? "selected" : ""}"
                onclick="selectVoice('${voice.id}')">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                        <span class="material-symbols-outlined text-primary text-sm">
                            ${voice.gender === "female" ? "face_3" : voice.gender === "male" ? "face" : "person"}
                        </span>
                    </div>
                    <div class="min-w-0 flex-1">
                        <h4 class="font-medium text-sm truncate">${voice.name}</h4>
                    </div>
                    <button class="preview-btn w-7 h-7 rounded-full bg-dark-600 hover:bg-dark-700 flex items-center justify-center flex-shrink-0 transition"
                        onclick="event.stopPropagation(); playVoicePreview('${voice.id}', this)"
                        title="Preview voice">
                        <span class="material-symbols-outlined text-sm">play_arrow</span>
                    </button>
                </div>
            </div>
        `,
      )
      .join("");

    // Parse emojis for cross-browser flag support (Windows Chrome)
    if (typeof twemoji !== "undefined") {
      twemoji.parse(grid, { folder: "svg", ext: ".svg" });
    }

    updateConvertButtonState();
  } catch (error) {
    console.error("Failed to load voices:", error);
  }
}

async function playVoicePreview(voiceId, button) {
  const iconSpan = button.querySelector("span");

  // If this voice is already playing or loading, stop it
  if (currentPreviewVoiceId === voiceId && currentPreviewAudio) {
    stopVoicePreview();
    return;
  }

  // Stop any currently playing preview
  stopVoicePreview();

  // Show loading state (keep button enabled so user can cancel)
  iconSpan.textContent = "hourglass_empty";
  iconSpan.classList.add("animate-spin");

  try {
    // Fetch and play the sample
    const query = state.selectedModel
      ? `?model=${encodeURIComponent(state.selectedModel)}`
      : "";
    const audio = new Audio(`/api/voice-sample/${voiceId}${query}`);
    currentPreviewAudio = audio;
    currentPreviewVoiceId = voiceId;

    // Use addEventListener with { once: true } to prevent duplicate play() calls
    audio.addEventListener(
      "canplaythrough",
      () => {
        // Guard: only play if this audio is still the current one (user may have cancelled)
        if (currentPreviewAudio !== audio) return;
        iconSpan.textContent = "stop";
        iconSpan.classList.remove("animate-spin");
        audio.play();
      },
      { once: true },
    );

    audio.onended = () => {
      // Guard: only reset if this audio is still the current one
      if (currentPreviewAudio !== audio) return;
      iconSpan.textContent = "play_arrow";
      currentPreviewAudio = null;
      currentPreviewVoiceId = null;
    };

    audio.onerror = () => {
      if (currentPreviewAudio !== audio) return;
      iconSpan.textContent = "play_arrow";
      iconSpan.classList.remove("animate-spin");
      currentPreviewAudio = null;
      currentPreviewVoiceId = null;
      console.error("Failed to load voice sample");
    };

    audio.load();
  } catch (error) {
    console.error("Failed to play preview:", error);
    iconSpan.textContent = "play_arrow";
    iconSpan.classList.remove("animate-spin");
  }
}

function stopVoicePreview() {
  if (currentPreviewAudio) {
    currentPreviewAudio.pause();
    currentPreviewAudio.currentTime = 0;
    currentPreviewAudio = null;
  }

  // Reset all preview buttons
  document.querySelectorAll(".preview-btn span").forEach((span) => {
    span.textContent = "play_arrow";
    span.classList.remove("animate-spin");
  });
  document.querySelectorAll(".preview-btn").forEach((btn) => {
    btn.disabled = false;
  });

  currentPreviewVoiceId = null;
}

function selectVoice(voiceId) {
  state.selectedVoice = voiceId;
  document.querySelectorAll(".voice-card").forEach((card) => {
    card.classList.toggle(
      "selected",
      card.onclick.toString().includes(voiceId),
    );
  });
  updateConvertButtonState();
  loadVoices(state.selectedModel); // Re-render to update selection
}

function handleFileSelect(file) {
  const validExts = [".txt", ".pdf", ".zip"];
  const ext = file.name.toLowerCase().substring(file.name.lastIndexOf("."));

  if (!validExts.includes(ext)) {
    alert("Unsupported file type. Please use TXT, PDF, or ZIP.");
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    alert("File too large. Maximum size is 50MB.");
    return;
  }

  state.selectedFile = file;

  document.getElementById("upload-content").classList.add("hidden");
  document.getElementById("file-selected").classList.remove("hidden");
  document.getElementById("selected-filename").textContent = file.name;
  document.getElementById("selected-filesize").textContent = formatFileSize(
    file.size,
  );
  updateConvertButtonState();
}

function clearFile() {
  state.selectedFile = null;
  document.getElementById("upload-content").classList.remove("hidden");
  document.getElementById("file-selected").classList.add("hidden");
  document.getElementById("file-input").value = "";
  updateConvertButtonState();
}

function updateConvertButtonState() {
  const btn = document.getElementById("convert-btn");
  if (!btn) return;

  btn.disabled = !(
    state.selectedFile &&
    state.selectedModel &&
    state.selectedVoice
  );
}

async function startConversion() {
  if (!state.selectedFile || !state.selectedModel || !state.selectedVoice)
    return;

  const btn = document.getElementById("convert-btn");
  btn.disabled = true;
  btn.innerHTML =
    '<span class="material-symbols-outlined align-middle mr-2 animate-spin">progress_activity</span>Uploading...';

  try {
    // Upload file
    const uploadResult = await api.upload(state.selectedFile);
    state.currentJob = uploadResult;

    // Start generation
    await api.generate(uploadResult.job_id, {
      model: state.selectedModel,
      voice: state.selectedVoice,
    });

    // Switch to progress view
    showView("progress");
  } catch (error) {
    alert("Error: " + error.message);
    updateConvertButtonState();
    btn.innerHTML =
      '<span class="material-symbols-outlined align-middle mr-2">play_circle</span>Start Conversion';
  }
}

// ============================================
// Utilities (Upload-specific)
// ============================================

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}
