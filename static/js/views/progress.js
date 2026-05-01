/**
 * @fileoverview SimplyNarrated - Progress View, conversion progress tracking and status polling
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
// Progress View
// ============================================

function renderProgressView() {
  return `
        <div class="glass rounded-2xl p-8">
            <div class="text-center mb-8">
                <!-- Circular Progress -->
                <div class="relative inline-block">
                    <svg class="progress-ring w-48 h-48">
                        <circle cx="96" cy="96" r="88" fill="none" stroke="#1a2633" stroke-width="8"/>
                        <circle id="progress-circle" cx="96" cy="96" r="88" fill="none" stroke="#137fec" 
                            stroke-width="8" stroke-linecap="round"
                            stroke-dasharray="553" stroke-dashoffset="553"/>
                    </svg>
                    <div class="absolute inset-0 flex items-center justify-center flex-col">
                        <span id="progress-percent" class="text-4xl font-bold">0%</span>
                        <span id="progress-chapter" class="text-gray-400">Preparing...</span>
                    </div>
                </div>
            </div>
            
            <!-- Stats -->
            <div class="grid grid-cols-2 gap-4 mb-8">
                <div class="bg-dark-700 rounded-lg p-4 text-center">
                    <p class="text-gray-400 text-sm">Time Remaining</p>
                    <p id="time-remaining" class="text-xl font-semibold">Calculating...</p>
                </div>
                <div class="bg-dark-700 rounded-lg p-4 text-center">
                    <p class="text-gray-400 text-sm">Processing Rate</p>
                    <p id="processing-rate" class="text-xl font-semibold">--</p>
                </div>
            </div>
            
            <!-- Activity Log -->
            <div class="bg-dark-700 rounded-lg p-4 h-48 overflow-y-auto no-scrollbar">
                <h4 class="text-sm text-gray-400 mb-2">Activity Log</h4>
                <div id="activity-log" class="space-y-2 text-sm">
                    <!-- Log entries will be added here -->
                </div>
            </div>
            
            <!-- Cancel Button -->
            <button id="cancel-btn"
                class="w-full mt-6 py-3 rounded-xl bg-red-600 hover:bg-red-700 font-semibold transition">
                <span class="material-symbols-outlined align-middle mr-2">cancel</span>
                Cancel Conversion
            </button>
        </div>
    `;
}

let progressInterval = null;

function initProgressView() {
  teardownProgressView();

  const cancelButton = document.getElementById("cancel-btn");
  if (cancelButton) {
    cancelButton.onclick = cancelConversion;
  }

  // Start polling for status
  pollStatus();
  progressInterval = setInterval(pollStatus, 5000);
}

function teardownProgressView() {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

function renderActivityLog(entries) {
  const logContainer = document.getElementById("activity-log");
  if (!logContainer) {
    return;
  }

  const rows = entries.map((entry) => {
    const row = document.createElement("div");
    row.className = "flex items-start gap-2";

    const icon = document.createElement("span");
    icon.className = `material-symbols-outlined text-sm ${
      entry.status === "success"
        ? "text-green-400"
        : entry.status === "error"
          ? "text-red-400"
          : entry.status === "warning"
            ? "text-yellow-400"
            : "text-gray-400"
    }`;
    icon.textContent =
      entry.status === "success"
        ? "check_circle"
        : entry.status === "error"
          ? "error"
          : entry.status === "warning"
            ? "warning"
            : "info";

    const message = document.createElement("span");
    message.className = "text-gray-300";
    message.textContent = entry.message || "";

    row.append(icon, message);
    return row;
  });

  logContainer.replaceChildren(...rows);
  logContainer.scrollTop = logContainer.scrollHeight;
}

async function pollStatus() {
  if (!state.currentJob) return;

  try {
    const status = await api.getStatus(state.currentJob.job_id);

    // Update progress ring
    const circle = document.getElementById("progress-circle");
    const percent = document.getElementById("progress-percent");
    const chapter = document.getElementById("progress-chapter");
    const timeRemaining = document.getElementById("time-remaining");
    const processingRate = document.getElementById("processing-rate");

    if (!circle || !percent || !chapter || !timeRemaining || !processingRate) {
      teardownProgressView();
      return;
    }

    const circumference = 553;
    const offset = circumference - (status.progress / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    percent.textContent = `${Math.round(status.progress)}%`;

    if (status.current_chapter > 0) {
      chapter.textContent = `Chapter ${status.current_chapter}/${status.total_chapters}`;
    }

    // Update stats
    timeRemaining.textContent = status.time_remaining || "Calculating...";
    processingRate.textContent = status.processing_rate || "--";

    // Update activity log
    renderActivityLog(status.activity_log || []);

    // Check if completed
    if (status.status === "completed") {
      teardownProgressView();
      document.getElementById("cancel-btn").classList.add("hidden");

      // Show completion UI
      const completionCircle = document.getElementById("progress-circle");
      if (completionCircle) completionCircle.style.strokeDashoffset = "0";
      document.getElementById("progress-percent").textContent = "100%";
      document.getElementById("progress-chapter").textContent =
        "Conversion Complete!";
      document.getElementById("time-remaining").textContent = "Ready to play";

      // After a brief moment, open the player
      setTimeout(() => {
        showPlayer(state.currentJob.job_id);
      }, 1500);
    } else if (status.status === "failed" || status.status === "cancelled") {
      teardownProgressView();
      alert("Conversion " + status.status);
      showView("upload");
    }
  } catch (error) {
    console.error("Status poll failed:", error);
  }
}

async function cancelConversion() {
  if (!state.currentJob) return;

  if (confirm("Are you sure you want to cancel this conversion?")) {
    try {
      await api.cancel(state.currentJob.job_id);
      teardownProgressView();
      showView("upload");
    } catch (error) {
      alert("Failed to cancel: " + error.message);
    }
  }
}
