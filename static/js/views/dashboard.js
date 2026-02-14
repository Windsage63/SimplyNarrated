/**
 * @fileoverview SimplyNarrated - Dashboard View, library management, book grid, and sorting
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
// Dashboard View
// ============================================

function renderDashboardView() {
  return `
        <div class="space-y-8">
            <!-- Welcome Section -->
            <div class="glass rounded-2xl p-6">
                <div class="flex items-center justify-between flex-wrap gap-3">
                    <h2 class="text-2xl font-bold mb-0">Welcome back!</h2>
                    <button onclick="openGutenbergLink()"
                       class="px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover font-semibold transition shadow-lg shadow-primary/20 inline-flex items-center gap-2 text-sm text-white">
                        <span class="material-symbols-outlined text-base">menu_book</span>
                        Get More Books
                    </button>
                </div>
                <p id="welcome-stats" class="text-gray-400 mt-1">Loading your library...</p>
            </div>
            
            <!-- Activity Panel -->
            <div id="activity-section" class="hidden">
                <h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">pending_actions</span>
                    Recent Activity
                </h3>
                <div id="activity-cards" class="grid md:grid-cols-2 gap-4">
                    <!-- Activity cards will be rendered here -->
                </div>
            </div>
            
            <!-- Library Header -->
            <div class="flex items-center justify-between">
                <h3 class="text-lg font-semibold flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">library_books</span>
                    My Library
                </h3>
              <div class="flex items-center gap-2">
                <input id="library-search" type="search" placeholder="Search library..."
                     class="px-3 py-1.5 text-sm rounded-lg bg-dark-700 border border-dark-600 focus:outline-none focus:border-primary w-44 sm:w-56" />
                    <button onclick="sortLibrary('recent')" class="sort-btn px-3 py-1.5 text-xs font-semibold 
                                                                     bg-dark-600 rounded-lg hover:bg-dark-700 transition"
                            data-sort="recent">Recent</button>
                    <button onclick="sortLibrary('az')" class="sort-btn px-3 py-1.5 text-xs font-semibold 
                                                                rounded-lg hover:bg-dark-700 transition"
                            data-sort="az">A-Z</button>
                </div>
            </div>
            
            <!-- Library Grid -->
            <div id="library-grid" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                <!-- Books will be rendered here -->
            </div>
            
            <!-- Empty State -->
            <div id="library-empty" class="glass rounded-2xl p-12 text-center hidden">
                <span class="material-symbols-outlined text-5xl text-gray-600 mb-4">library_books</span>
                <h3 class="text-xl font-semibold mb-2">No audiobooks yet</h3>
                <p class="text-gray-400 mb-4">Convert your first book to get started</p>
                <button onclick="showView('upload')" class="px-6 py-3 rounded-xl bg-primary hover:bg-primary-hover font-semibold transition">
                    <span class="material-symbols-outlined align-middle mr-2">upload_file</span>
                    Upload a Book
                </button>
            </div>
        </div>
    `;
}

async function initDashboardView() {
  try {
    const data = await api.getLibrary();
    state.library = data.books;

    // Update welcome stats
    const statsText =
      data.total > 0
        ? `You have ${data.total} audiobook${data.total > 1 ? "s" : ""} in your library${data.in_progress > 0 ? ` and ${data.in_progress} conversion${data.in_progress > 1 ? "s" : ""} in progress.` : "."}`
        : "Start by uploading a book to convert.";
    document.getElementById("welcome-stats").textContent = statsText;

    // Show activity panel if there are in-progress jobs
    if (data.in_progress > 0) {
      document.getElementById("activity-section").classList.remove("hidden");
      await renderActivityCards();
    }

    const grid = document.getElementById("library-grid");
    const empty = document.getElementById("library-empty");

    if (data.books.length === 0) {
      grid.classList.add("hidden");
      empty.classList.remove("hidden");
    } else {
      renderLibraryGrid(data.books);
    }

    // Set default sort button as active
    document
      .querySelector('.sort-btn[data-sort="recent"]')
      .classList.add("bg-dark-600");

    // Search filtering
    const searchInput = document.getElementById("library-search");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        renderLibraryGrid(getVisibleLibraryBooks());
      });
    }
  } catch (error) {
    console.error("Failed to load library:", error);
    document.getElementById("welcome-stats").textContent =
      "Error loading library.";
  }
}

function getVisibleLibraryBooks() {
  const searchInput = document.getElementById("library-search");
  const query = (searchInput?.value || "").trim().toLowerCase();
  if (!query) return [...state.library];

  return state.library.filter((book) => {
    const title = (book.title || "").toLowerCase();
    const author = (book.author || "").toLowerCase();
    return title.includes(query) || author.includes(query);
  });
}

async function renderActivityCards() {
  const cards = document.getElementById("activity-cards");
  if (!cards) return;

  if (!state.currentJob?.job_id) {
    cards.innerHTML = `
      <div class="glass rounded-xl p-4">
        <div class="flex justify-between items-start mb-3">
          <div>
            <h4 class="font-semibold text-sm">Processing...</h4>
            <p class="text-xs text-gray-400 mt-0.5">A conversion is running</p>
          </div>
          <span class="text-primary text-sm font-bold">--</span>
        </div>
        <div class="w-full bg-dark-600 h-2 rounded-full overflow-hidden">
          <div class="bg-primary h-full animate-pulse" style="width: 50%;"></div>
        </div>
      </div>
    `;
    return;
  }

  try {
    const status = await api.getStatus(state.currentJob.job_id);
    const pct = Math.max(0, Math.min(100, Math.round(status.progress || 0)));
    cards.innerHTML = `
      <div class="glass rounded-xl p-4">
        <div class="flex justify-between items-start mb-3">
          <div>
            <h4 class="font-semibold text-sm">${state.currentJob.filename || "Current conversion"}</h4>
            <p class="text-xs text-gray-400 mt-0.5">${status.status} • Chapter ${status.current_chapter}/${status.total_chapters || "?"}</p>
          </div>
          <span class="text-primary text-sm font-bold">${pct}%</span>
        </div>
        <div class="w-full bg-dark-600 h-2 rounded-full overflow-hidden">
          <div class="bg-primary h-full transition-all" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
  } catch {
    cards.innerHTML = "";
  }
}

/**
 * Render books into the library grid
 */
function renderLibraryGrid(books) {
  const grid = document.getElementById("library-grid");
  grid.innerHTML = books
    .map(
      (book) => `
        <div class="glass rounded-xl p-4 cursor-pointer hover:border-primary transition relative group/card"
             onclick="showPlayer('${book.id}')">
            <!-- Delete Button -->
            <button onclick="deleteBook(event, '${book.id}', '${book.title.replace(/'/g, "\\'")}')"
                    class="absolute top-2 right-2 z-10 w-8 h-8 rounded-full bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white 
                           flex items-center justify-center opacity-0 group-hover/card:opacity-100 transition duration-200"
                    title="Delete audiobook">
                <span class="material-symbols-outlined text-sm">delete</span>
            </button>

            <div class="aspect-[3/4] bg-gradient-to-br from-primary/30 via-dark-600 to-primary/10 
                        rounded-lg mb-3 flex items-center justify-center relative group overflow-hidden">
                ${
                  book.cover_url
                    ? `<img src="${book.cover_url}" alt="Book cover" class="w-full h-full object-cover">`
                    : '<span class="material-symbols-outlined text-4xl text-gray-500">menu_book</span>'
                }
                <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 
                            transition flex items-center justify-center rounded-lg">
                    <div class="w-12 h-12 rounded-full bg-primary flex items-center justify-center">
                        <span class="material-symbols-outlined text-2xl">play_arrow</span>
                    </div>
                </div>
            </div>
            <h4 class="font-medium truncate">${book.title}</h4>
            <p class="text-sm text-gray-400">${book.total_chapters} chapters • ${book.total_duration || "--"}</p>
        </div>
    `,
    )
    .join("");
}

/**
 * Handle book deletion
 */
async function deleteBook(event, bookId, title) {
  event.stopPropagation();

  if (
    confirm(
      `Are you sure you want to delete "${title}"? This action cannot be undone.`,
    )
  ) {
    // Always release any player resources before deleting a book.
    // This prevents stale browser file handles after leaving the player view.
    if (typeof teardownPlayerView === "function") {
      teardownPlayerView();
    } else if (typeof playerState !== "undefined" && playerState.audioElement) {
      playerState.audioElement.pause();
      playerState.audioElement.removeAttribute("src");
      playerState.audioElement.load();
      playerState.isPlaying = false;
      playerState.book = null;
      playerState.audioElement = null;
    }

    try {
      await api.delete(bookId);
      // Refresh library
      await initDashboardView();
    } catch (error) {
      alert("Error: " + error.message);
    }
  }
}

/**
 * Sort library by criteria
 */
function sortLibrary(criteria) {
  // Update button states
  document.querySelectorAll(".sort-btn").forEach((btn) => {
    btn.classList.toggle("bg-dark-600", btn.dataset.sort === criteria);
  });

  // Sort books
  let sorted = getVisibleLibraryBooks();
  if (criteria === "az") {
    sorted.sort((a, b) => a.title.localeCompare(b.title));
  } else {
    // 'recent' - sort by created_at descending
    sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  renderLibraryGrid(sorted);
}

/**
 * Show a tip dialog then open Project Gutenberg in a new tab.
 */
function openGutenbergLink() {
  const dialog = document.createElement("div");
  dialog.className =
    "fixed inset-0 z-50 flex items-center justify-center bg-black/60";
  dialog.innerHTML = `
    <div class="glass rounded-2xl p-8 max-w-md mx-4 text-center space-y-4">
      <span class="material-symbols-outlined text-primary text-5xl">menu_book</span>
      <h3 class="text-xl font-bold">Downloading from Project Gutenberg</h3>
      <p class="text-gray-300 text-sm leading-relaxed">
        For the best results, download books as <strong>HTML (zip)</strong> files.
        Plain <strong>.txt</strong> files also work well.<br><br>
        After downloading, come back here and upload the file to convert it into an audiobook.
      </p>
      <button onclick="this.closest('.fixed').remove(); window.open('https://www.gutenberg.org/', '_blank', 'noopener,noreferrer')"
              class="px-6 py-3 rounded-xl bg-primary hover:bg-primary-hover font-semibold transition shadow-lg shadow-primary/20 inline-flex items-center gap-2">
        <span class="material-symbols-outlined">open_in_new</span>
        Go to Project Gutenberg
      </button>
      <button onclick="this.closest('.fixed').remove()"
              class="block mx-auto text-sm text-gray-400 hover:text-white transition">Cancel</button>
    </div>
  `;
  document.body.appendChild(dialog);
}
