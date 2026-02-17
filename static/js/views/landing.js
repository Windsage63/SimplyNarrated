/**
 * @fileoverview SimplyNarrated - Landing View, lightweight app entry view
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

function renderLandingView() {
  return `
        <div class="space-y-8">
            <!-- Hero Image -->
            <div class="rounded-2xl overflow-hidden">
                <img src="/static/img/hero.png" alt="SimplyNarrated — Upload documents, process with local AI, get your audiobook" class="w-full h-auto block rounded-2xl" />
            </div>

            <!-- Hero Copy -->
            <div class="text-center pt-2">
                <h2 class="text-3xl md:text-4xl font-bold mb-3">Turn Documents Into Audiobooks, Locally</h2>
                <p class="text-gray-300 max-w-2xl mx-auto mb-6">
                    Upload TXT, Markdown, PDF, or Project Gutenberg HTML ZIP files and generate
                    single file M4A audiobooks with natural AI voices — directly on your machine.
                </p>
                <div class="flex flex-col sm:flex-row justify-center gap-3">
                    <button onclick="showView('upload')" class="px-6 py-3 rounded-xl bg-primary hover:bg-primary-hover font-semibold transition shadow-lg shadow-primary/20">
                        <span class="material-symbols-outlined align-middle mr-2">upload_file</span>
                        Start Converting
                    </button>
                    <button onclick="showView('dashboard')" class="px-6 py-3 rounded-xl bg-dark-600 hover:bg-dark-700 font-semibold transition border border-white/10">
                        <span class="material-symbols-outlined align-middle mr-2">library_books</span>
                        Open Library
                    </button>
                </div>
            </div>

            <!-- Proof Strip -->
            <div class="proof-strip py-2">
                <div class="proof-item">
                    <span class="material-symbols-outlined">shield</span>
                    Local-first processing
                </div>
                <div class="proof-item">
                    <span class="material-symbols-outlined">lists</span>
                    Chapter-based output
                </div>
                <div class="proof-item">
                    <span class="material-symbols-outlined">play_circle</span>
                    Built-in player + bookmarks
                </div>
                <div class="proof-item">
                    <span class="material-symbols-outlined">menu_book</span>
                    Project Gutenberg ready
                </div>
            </div>

            <!-- Feature Cards -->
            <div class="grid md:grid-cols-3 gap-4">
                <div class="glass rounded-xl p-6 feature-card">
                    <span class="material-symbols-outlined text-primary text-3xl mb-3 block">upload_file</span>
                    <h3 class="font-semibold mb-1">1. Upload</h3>
                    <p class="text-sm text-gray-400">Drop your TXT, Markdown, PDF, or Gutenberg HTML ZIP and choose voice and quality settings.</p>
                </div>
                <div class="glass rounded-xl p-6 feature-card">
                    <span class="material-symbols-outlined text-primary text-3xl mb-3 block">neurology</span>
                    <h3 class="font-semibold mb-1">2. Generate</h3>
                    <p class="text-sm text-gray-400">AI processes your text locally — track chapter progress in real time.</p>
                </div>
                <div class="glass rounded-xl p-6 feature-card">
                    <span class="material-symbols-outlined text-primary text-3xl mb-3 block">headphones</span>
                    <h3 class="font-semibold mb-1">3. Listen</h3>
                    <p class="text-sm text-gray-400">Play chapters, resume with bookmarks, and manage your audiobook library.</p>
                </div>
            </div>
        </div>
    `;
}

function initLandingView() {
  // No-op for now; reserved for future landing analytics/telemetry hooks.
}
