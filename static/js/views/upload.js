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
                        <p class="text-sm text-gray-500">Supports: TXT, MD, PDF (max 50MB)</p>
                    </div>
                    <div id="file-selected" class="hidden">
                        <span class="material-symbols-outlined text-5xl text-green-500 mb-4">check_circle</span>
                        <h2 class="text-xl font-semibold mb-2" id="selected-filename">filename.txt</h2>
                        <p class="text-gray-400" id="selected-filesize">1.2 MB</p>
                        <button onclick="clearFile()" class="mt-4 text-primary hover:underline">Choose different file</button>
                    </div>
                    <input type="file" id="file-input" class="hidden" accept=".txt,.md,.pdf">
                </div>
            </div>
            
            <!-- Voice Selection -->
            <div class="glass rounded-2xl p-8">
                <h3 class="text-lg font-semibold mb-4">
                    <span class="material-symbols-outlined align-middle mr-2">record_voice_over</span>
                    Select Narrator Voice
                </h3>
                <div id="voice-grid" class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <!-- Voices will be rendered here -->
                </div>
            </div>
            
            <!-- Audio Settings -->
            <div class="glass rounded-2xl p-8">
                <h3 class="text-lg font-semibold mb-4">
                    <span class="material-symbols-outlined align-middle mr-2">tune</span>
                    Audio Settings
                </h3>
                <div class="grid md:grid-cols-3 gap-6">
                    <!-- Speed -->
                    <div>
                        <label class="block text-sm text-gray-400 mb-2">Speed: <span id="speed-value">1.0x</span></label>
                        <input type="range" id="speed-slider" min="0.5" max="2" step="0.1" value="1"
                            class="w-full h-2 bg-dark-600 rounded-lg appearance-none cursor-pointer">
                    </div>
                    
                    <!-- Quality -->
                    <div>
                        <label class="block text-sm text-gray-400 mb-2">Quality</label>
                        <div class="flex gap-2">
                            <button onclick="setQuality('sd')" class="quality-btn px-4 py-2 rounded-lg bg-primary" data-quality="sd">SD</button>
                            <button onclick="setQuality('hd')" class="quality-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-quality="hd">HD</button>
                            <button onclick="setQuality('ultra')" class="quality-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-quality="ultra">Ultra</button>
                        </div>
                    </div>
                    
                    <!-- Remove Footnotes -->
                    <div>
                        <label class="block text-sm text-gray-400 mb-2">Remove Footnotes / Numbers</label>
                        <div class="flex gap-2">
                            <button onclick="toggleFootnoteRemoval('square')" class="footnote-toggle-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-footnote="square">[###]</button>
                            <button onclick="toggleFootnoteRemoval('paren')" class="footnote-toggle-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-footnote="paren">(###)</button>
                        </div>
                    </div>
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

  // Load voices
  loadVoices();

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

  // Speed slider
  const speedSlider = document.getElementById("speed-slider");
  speedSlider.addEventListener("input", (e) => {
    state.audioSettings.speed = parseFloat(e.target.value);
    document.getElementById("speed-value").textContent = `${e.target.value}x`;
  });
}

// Track currently playing audio for voice previews
let currentPreviewAudio = null;
let currentPreviewVoiceId = null;

async function loadVoices() {
  try {
    const data = await api.getVoices();
    state.voices = data.voices;

    const grid = document.getElementById("voice-grid");
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
    const audio = new Audio(`/api/voice-sample/${voiceId}`);
    currentPreviewAudio = audio;
    currentPreviewVoiceId = voiceId;

    // Use addEventListener with { once: true } to prevent duplicate play() calls
    audio.addEventListener("canplaythrough", () => {
      // Guard: only play if this audio is still the current one (user may have cancelled)
      if (currentPreviewAudio !== audio) return;
      iconSpan.textContent = "stop";
      iconSpan.classList.remove("animate-spin");
      audio.play();
    }, { once: true });

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
  loadVoices(); // Re-render to update selection
}

function handleFileSelect(file) {
  const validExts = [".txt", ".md", ".pdf"];
  const ext = file.name.toLowerCase().substring(file.name.lastIndexOf("."));

  if (!validExts.includes(ext)) {
    alert("Unsupported file type. Please use TXT, MD, or PDF.");
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
  document.getElementById("convert-btn").disabled = false;
}

function clearFile() {
  state.selectedFile = null;
  document.getElementById("upload-content").classList.remove("hidden");
  document.getElementById("file-selected").classList.add("hidden");
  document.getElementById("convert-btn").disabled = true;
  document.getElementById("file-input").value = "";
}

function setQuality(quality) {
  state.audioSettings.quality = quality;
  document.querySelectorAll(".quality-btn").forEach((btn) => {
    btn.classList.toggle("bg-primary", btn.dataset.quality === quality);
    btn.classList.toggle("bg-dark-600", btn.dataset.quality !== quality);
  });
}

function toggleFootnoteRemoval(type) {
  if (type === "square") {
    state.audioSettings.removeSquareBracketNumbers =
      !state.audioSettings.removeSquareBracketNumbers;
  } else if (type === "paren") {
    state.audioSettings.removeParenNumbers =
      !state.audioSettings.removeParenNumbers;
  }
  document.querySelectorAll(".footnote-toggle-btn").forEach((btn) => {
    const ft = btn.dataset.footnote;
    const isOn =
      ft === "square"
        ? state.audioSettings.removeSquareBracketNumbers
        : state.audioSettings.removeParenNumbers;
    btn.classList.toggle("bg-primary", isOn);
    btn.classList.toggle("bg-dark-600", !isOn);
    btn.classList.toggle("hover:bg-dark-700", !isOn);
  });
}

async function startConversion() {
  if (!state.selectedFile) return;

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
      voice: state.selectedVoice,
      ...state.audioSettings,
    });

    // Switch to progress view
    showView("progress");
  } catch (error) {
    alert("Error: " + error.message);
    btn.disabled = false;
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
