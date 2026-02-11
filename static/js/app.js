/**
 * @fileoverview SimplyNarrated - Main JavaScript Application, SPA routing, state management, and API client
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
// State Management
// ============================================

const state = {
  currentView: "upload",
  currentJob: null,
  currentBook: null,
  selectedFile: null,
  selectedVoice: "af_heart",
  audioSettings: {
    speed: 1.0,
    quality: "sd",
    format: "mp3",
    removeSquareBracketNumbers: false,
    removeParenNumbers: false,
  },
  voices: [],
  library: [],
};

// ============================================
// API Client
// ============================================

const api = {
  baseUrl: "/api",

  async upload(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  },

  async generate(jobId, config) {
    const response = await fetch(`${this.baseUrl}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        narrator_voice: config.voice,
        speed: config.speed,
        quality: config.quality,
        format: config.format,
        remove_square_bracket_numbers:
          config.removeSquareBracketNumbers || false,
        remove_paren_numbers: config.removeParenNumbers || false,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Generation failed");
    }

    return response.json();
  },

  async getStatus(jobId) {
    const response = await fetch(`${this.baseUrl}/status/${jobId}`);
    if (!response.ok) {
      throw new Error("Failed to get status");
    }
    return response.json();
  },

  async cancel(jobId) {
    const response = await fetch(`${this.baseUrl}/cancel/${jobId}`, {
      method: "POST",
    });
    return response.json();
  },

  async getVoices() {
    const response = await fetch(`${this.baseUrl}/voices`);
    return response.json();
  },

  async getLibrary() {
    const response = await fetch(`${this.baseUrl}/library`);
    return response.json();
  },

  async getBook(bookId) {
    const response = await fetch(`${this.baseUrl}/book/${bookId}`);
    if (!response.ok) {
      throw new Error("Book not found");
    }
    return response.json();
  },

  async getBookmark(bookId) {
    const response = await fetch(`${this.baseUrl}/bookmark/${bookId}`);
    return response.json();
  },

  async saveBookmark(bookId, chapter, position) {
    const response = await fetch(
      `${this.baseUrl}/bookmark?book_id=${bookId}&chapter=${chapter}&position=${position}`,
      {
        method: "POST",
      },
    );
    return response.json();
  },

  async updateMetadata(bookId, data) {
    const response = await fetch(`${this.baseUrl}/book/${bookId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to update metadata");
    }
    return response.json();
  },

  async delete(bookId) {
    const response = await fetch(`${this.baseUrl}/book/${bookId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to delete book");
    }
    return response.json();
  },

  async uploadCover(bookId, file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/book/${bookId}/cover`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to upload cover");
    }
    return response.json();
  },
};

// ============================================
// View Rendering
// ============================================

function showView(viewName) {
  state.currentView = viewName;

  // Update nav active state
  document.querySelectorAll("nav button").forEach((btn) => {
    btn.classList.remove("bg-dark-700");
  });
  const navBtn = document.getElementById(`nav-${viewName}`);
  if (navBtn) navBtn.classList.add("bg-dark-700");

  // Render view
  const container = document.getElementById("view-container");

  switch (viewName) {
    case "upload":
      container.innerHTML = renderUploadView();
      initUploadView();
      break;
    case "progress":
      container.innerHTML = renderProgressView();
      initProgressView();
      break;
    case "dashboard":
      container.innerHTML = renderDashboardView();
      initDashboardView();
      break;
    case "player":
      // Player view requires a book ID
      if (state.currentBook) {
        container.innerHTML = renderPlayerView(state.currentBook);
        initPlayerView(state.currentBook);
      } else {
        showView("dashboard");
      }
      break;
    default:
      container.innerHTML = "<p>View not found</p>";
  }
}

/**
 * Open a book in the player view
 * @param {string} bookId - ID of the book to play
 */
function showPlayer(bookId) {
  state.currentBook = bookId;
  showView("player");
}

// ============================================
// Initialize App
// ============================================

document.addEventListener("DOMContentLoaded", () => {
  showView("upload");
});
