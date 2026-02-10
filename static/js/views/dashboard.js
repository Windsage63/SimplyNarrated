/**
 * @fileoverview BookTalk - Dashboard View, library management, book grid, and sorting
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
                <h2 class="text-2xl font-bold mb-1">Welcome back!</h2>
                <p id="welcome-stats" class="text-gray-400">Loading your library...</p>
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
                <div class="flex gap-2">
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
      // Activity cards would be populated by polling - for now show placeholder
      document.getElementById("activity-cards").innerHTML = `
                <div class="glass rounded-xl p-4">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h4 class="font-semibold text-sm">Processing...</h4>
                            <p class="text-xs text-gray-400 mt-0.5">Conversion in progress</p>
                        </div>
                        <span class="text-primary text-sm font-bold">--</span>
                    </div>
                    <div class="w-full bg-dark-600 h-2 rounded-full overflow-hidden">
                        <div class="bg-primary h-full animate-pulse" style="width: 50%;"></div>
                    </div>
                </div>
            `;
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
  } catch (error) {
    console.error("Failed to load library:", error);
    document.getElementById("welcome-stats").textContent =
      "Error loading library.";
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
                        rounded-lg mb-3 flex items-center justify-center relative group">
                <span class="material-symbols-outlined text-4xl text-gray-500">menu_book</span>
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
    // If this book is currently playing, stop and clear it
    if (
      typeof playerState !== "undefined" &&
      playerState.book &&
      playerState.book.id === bookId
    ) {
      console.log("Stopping player before deletion...");
      if (playerState.audioElement) {
        playerState.audioElement.pause();
        playerState.audioElement.src = ""; // Clear source to release file handle
        playerState.audioElement.load();
      }
      playerState.isPlaying = false;
      playerState.book = null;
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
  let sorted = [...state.library];
  if (criteria === "az") {
    sorted.sort((a, b) => a.title.localeCompare(b.title));
  } else {
    // 'recent' - sort by created_at descending
    sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  renderLibraryGrid(sorted);
}
