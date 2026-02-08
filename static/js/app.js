/**
 * @fileoverview BookTalk - Main JavaScript Application, SPA routing, state management, and API client
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
    currentView: 'upload',
    currentJob: null,
    currentBook: null,
    selectedFile: null,
    selectedVoice: 'af_heart',
    audioSettings: {
        speed: 1.0,
        quality: 'hd',
        format: 'mp3'
    },
    voices: [],
    library: []
};

// ============================================
// API Client
// ============================================

const api = {
    baseUrl: '/api',
    
    async upload(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${this.baseUrl}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        return response.json();
    },
    
    async generate(jobId, config) {
        const response = await fetch(`${this.baseUrl}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: jobId,
                narrator_voice: config.voice,
                speed: config.speed,
                quality: config.quality,
                format: config.format
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }
        
        return response.json();
    },
    
    async getStatus(jobId) {
        const response = await fetch(`${this.baseUrl}/status/${jobId}`);
        if (!response.ok) {
            throw new Error('Failed to get status');
        }
        return response.json();
    },
    
    async cancel(jobId) {
        const response = await fetch(`${this.baseUrl}/cancel/${jobId}`, {
            method: 'POST'
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
            throw new Error('Book not found');
        }
        return response.json();
    },
    
    async getBookmark(bookId) {
        const response = await fetch(`${this.baseUrl}/bookmark/${bookId}`);
        return response.json();
    },
    
    async saveBookmark(bookId, chapter, position) {
        const response = await fetch(`${this.baseUrl}/bookmark?book_id=${bookId}&chapter=${chapter}&position=${position}`, {
            method: 'POST'
        });
        return response.json();
    }
};

// ============================================
// View Rendering
// ============================================

function showView(viewName) {
    state.currentView = viewName;
    
    // Update nav active state
    document.querySelectorAll('nav button').forEach(btn => {
        btn.classList.remove('bg-dark-700');
    });
    const navBtn = document.getElementById(`nav-${viewName}`);
    if (navBtn) navBtn.classList.add('bg-dark-700');
    
    // Render view
    const container = document.getElementById('view-container');
    
    switch(viewName) {
        case 'upload':
            container.innerHTML = renderUploadView();
            initUploadView();
            break;
        case 'progress':
            container.innerHTML = renderProgressView();
            initProgressView();
            break;
        case 'dashboard':
            container.innerHTML = renderDashboardView();
            initDashboardView();
            break;
        case 'player':
            // Player view requires a book ID
            if (state.currentBook) {
                container.innerHTML = renderPlayerView(state.currentBook);
                initPlayerView(state.currentBook);
            } else {
                showView('dashboard');
            }
            break;
        default:
            container.innerHTML = '<p>View not found</p>';
    }
}

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
                        <p class="text-sm text-gray-500">Supports: TXT, MD, EPUB, PDF (max 50MB)</p>
                    </div>
                    <div id="file-selected" class="hidden">
                        <span class="material-symbols-outlined text-5xl text-green-500 mb-4">check_circle</span>
                        <h2 class="text-xl font-semibold mb-2" id="selected-filename">filename.txt</h2>
                        <p class="text-gray-400" id="selected-filesize">1.2 MB</p>
                        <button onclick="clearFile()" class="mt-4 text-primary hover:underline">Choose different file</button>
                    </div>
                    <input type="file" id="file-input" class="hidden" accept=".txt,.md,.epub,.pdf">
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
                            <button onclick="setQuality('sd')" class="quality-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-quality="sd">SD</button>
                            <button onclick="setQuality('hd')" class="quality-btn px-4 py-2 rounded-lg bg-primary" data-quality="hd">HD</button>
                            <button onclick="setQuality('ultra')" class="quality-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-quality="ultra">Ultra</button>
                        </div>
                    </div>
                    
                    <!-- Format -->
                    <div>
                        <label class="block text-sm text-gray-400 mb-2">Format</label>
                        <div class="flex gap-2">
                            <button onclick="setFormat('mp3')" class="format-btn px-4 py-2 rounded-lg bg-primary" data-format="mp3">MP3</button>
                            <button onclick="setFormat('wav')" class="format-btn px-4 py-2 rounded-lg bg-dark-600 hover:bg-dark-700" data-format="wav">WAV</button>
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
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    
    // Load voices
    loadVoices();
    
    // Drag and drop handlers
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // Speed slider
    const speedSlider = document.getElementById('speed-slider');
    speedSlider.addEventListener('input', (e) => {
        state.audioSettings.speed = parseFloat(e.target.value);
        document.getElementById('speed-value').textContent = `${e.target.value}x`;
    });
}

// Track currently playing audio for voice previews
let currentPreviewAudio = null;
let currentPreviewVoiceId = null;

async function loadVoices() {
    try {
        const data = await api.getVoices();
        state.voices = data.voices;
        
        const grid = document.getElementById('voice-grid');
        grid.innerHTML = state.voices.map(voice => `
            <div class="voice-card glass rounded-lg p-3 cursor-pointer ${voice.id === state.selectedVoice ? 'selected' : ''}"
                onclick="selectVoice('${voice.id}')">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                        <span class="material-symbols-outlined text-primary text-sm">
                            ${voice.gender === 'female' ? 'face_3' : voice.gender === 'male' ? 'face' : 'person'}
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
        `).join('');
        
        // Parse emojis for cross-browser flag support (Windows Chrome)
        if (typeof twemoji !== 'undefined') {
            twemoji.parse(grid, { folder: 'svg', ext: '.svg' });
        }
    } catch (error) {
        console.error('Failed to load voices:', error);
    }
}

async function playVoicePreview(voiceId, button) {
    const iconSpan = button.querySelector('span');
    
    // If this voice is already playing, stop it
    if (currentPreviewVoiceId === voiceId && currentPreviewAudio) {
        stopVoicePreview();
        return;
    }
    
    // Stop any currently playing preview
    stopVoicePreview();
    
    // Show loading state
    iconSpan.textContent = 'hourglass_empty';
    iconSpan.classList.add('animate-spin');
    button.disabled = true;
    
    try {
        // Fetch and play the sample
        const audio = new Audio(`/api/voice-sample/${voiceId}`);
        currentPreviewAudio = audio;
        currentPreviewVoiceId = voiceId;
        
        audio.oncanplaythrough = () => {
            iconSpan.textContent = 'stop';
            iconSpan.classList.remove('animate-spin');
            button.disabled = false;
            audio.play();
        };
        
        audio.onended = () => {
            iconSpan.textContent = 'play_arrow';
            currentPreviewAudio = null;
            currentPreviewVoiceId = null;
        };
        
        audio.onerror = () => {
            iconSpan.textContent = 'play_arrow';
            iconSpan.classList.remove('animate-spin');
            button.disabled = false;
            currentPreviewAudio = null;
            currentPreviewVoiceId = null;
            console.error('Failed to load voice sample');
        };
        
        audio.load();
        
    } catch (error) {
        console.error('Failed to play preview:', error);
        iconSpan.textContent = 'play_arrow';
        iconSpan.classList.remove('animate-spin');
        button.disabled = false;
    }
}

function stopVoicePreview() {
    if (currentPreviewAudio) {
        currentPreviewAudio.pause();
        currentPreviewAudio.currentTime = 0;
        currentPreviewAudio = null;
    }
    
    // Reset all preview buttons
    document.querySelectorAll('.preview-btn span').forEach(span => {
        span.textContent = 'play_arrow';
        span.classList.remove('animate-spin');
    });
    document.querySelectorAll('.preview-btn').forEach(btn => {
        btn.disabled = false;
    });
    
    currentPreviewVoiceId = null;
}

function selectVoice(voiceId) {
    state.selectedVoice = voiceId;
    document.querySelectorAll('.voice-card').forEach(card => {
        card.classList.toggle('selected', card.onclick.toString().includes(voiceId));
    });
    loadVoices(); // Re-render to update selection
}

function handleFileSelect(file) {
    const validExts = ['.txt', '.md', '.epub', '.pdf'];
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!validExts.includes(ext)) {
        alert('Unsupported file type. Please use TXT, MD, EPUB, or PDF.');
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
        alert('File too large. Maximum size is 50MB.');
        return;
    }
    
    state.selectedFile = file;
    
    document.getElementById('upload-content').classList.add('hidden');
    document.getElementById('file-selected').classList.remove('hidden');
    document.getElementById('selected-filename').textContent = file.name;
    document.getElementById('selected-filesize').textContent = formatFileSize(file.size);
    document.getElementById('convert-btn').disabled = false;
}

function clearFile() {
    state.selectedFile = null;
    document.getElementById('upload-content').classList.remove('hidden');
    document.getElementById('file-selected').classList.add('hidden');
    document.getElementById('convert-btn').disabled = true;
    document.getElementById('file-input').value = '';
}

function setQuality(quality) {
    state.audioSettings.quality = quality;
    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.classList.toggle('bg-primary', btn.dataset.quality === quality);
        btn.classList.toggle('bg-dark-600', btn.dataset.quality !== quality);
    });
}

function setFormat(format) {
    state.audioSettings.format = format;
    document.querySelectorAll('.format-btn').forEach(btn => {
        btn.classList.toggle('bg-primary', btn.dataset.format === format);
        btn.classList.toggle('bg-dark-600', btn.dataset.format !== format);
    });
}

async function startConversion() {
    if (!state.selectedFile) return;
    
    const btn = document.getElementById('convert-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined align-middle mr-2 animate-spin">progress_activity</span>Uploading...';
    
    try {
        // Upload file
        const uploadResult = await api.upload(state.selectedFile);
        state.currentJob = uploadResult;
        
        // Start generation
        await api.generate(uploadResult.job_id, {
            voice: state.selectedVoice,
            ...state.audioSettings
        });
        
        // Switch to progress view
        showView('progress');
        
    } catch (error) {
        alert('Error: ' + error.message);
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined align-middle mr-2">play_circle</span>Start Conversion';
    }
}

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
            <button id="cancel-btn" onclick="cancelConversion()" 
                class="w-full mt-6 py-3 rounded-xl bg-red-600 hover:bg-red-700 font-semibold transition">
                <span class="material-symbols-outlined align-middle mr-2">cancel</span>
                Cancel Conversion
            </button>
        </div>
    `;
}

let progressInterval = null;

function initProgressView() {
    // Start polling for status
    pollStatus();
    progressInterval = setInterval(pollStatus, 2000);
}

async function pollStatus() {
    if (!state.currentJob) return;
    
    try {
        const status = await api.getStatus(state.currentJob.job_id);
        
        // Update progress ring
        const circle = document.getElementById('progress-circle');
        const percent = document.getElementById('progress-percent');
        const chapter = document.getElementById('progress-chapter');
        
        const circumference = 553;
        const offset = circumference - (status.progress / 100) * circumference;
        circle.style.strokeDashoffset = offset;
        percent.textContent = `${Math.round(status.progress)}%`;
        
        if (status.current_chapter > 0) {
            chapter.textContent = `Chapter ${status.current_chapter}/${status.total_chapters}`;
        }
        
        // Update stats
        document.getElementById('time-remaining').textContent = status.time_remaining || 'Calculating...';
        document.getElementById('processing-rate').textContent = status.processing_rate || '--';
        
        // Update activity log
        const logContainer = document.getElementById('activity-log');
        logContainer.innerHTML = status.activity_log.map(entry => {
            const icon = entry.status === 'success' ? 'check_circle' : 
                        entry.status === 'error' ? 'error' : 
                        entry.status === 'warning' ? 'warning' : 'info';
            const color = entry.status === 'success' ? 'text-green-400' : 
                         entry.status === 'error' ? 'text-red-400' : 
                         entry.status === 'warning' ? 'text-yellow-400' : 'text-gray-400';
            return `
                <div class="flex items-start gap-2">
                    <span class="material-symbols-outlined ${color} text-sm">${icon}</span>
                    <span class="text-gray-300">${entry.message}</span>
                </div>
            `;
        }).join('');
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Check if completed
        if (status.status === 'completed') {
            clearInterval(progressInterval);
            document.getElementById('cancel-btn').classList.add('hidden');
            
            // Show completion UI
            document.getElementById('progress-fill').style.width = '100%';
            document.getElementById('progress-text').textContent = '100%';
            document.getElementById('current-step').textContent = 'Conversion Complete!';
            document.getElementById('time-remaining').textContent = 'Ready to play';
            
            // After a brief moment, open the player
            setTimeout(() => {
                showPlayer(state.currentJob.job_id);
            }, 1500);
        } else if (status.status === 'failed' || status.status === 'cancelled') {
            clearInterval(progressInterval);
            alert('Conversion ' + status.status);
            showView('upload');
        }
        
    } catch (error) {
        console.error('Status poll failed:', error);
    }
}

async function cancelConversion() {
    if (!state.currentJob) return;
    
    if (confirm('Are you sure you want to cancel this conversion?')) {
        try {
            await api.cancel(state.currentJob.job_id);
            clearInterval(progressInterval);
            showView('upload');
        } catch (error) {
            alert('Failed to cancel: ' + error.message);
        }
    }
}

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
        const statsText = data.total > 0 
            ? `You have ${data.total} audiobook${data.total > 1 ? 's' : ''} in your library${data.in_progress > 0 ? ` and ${data.in_progress} conversion${data.in_progress > 1 ? 's' : ''} in progress.` : '.'}`
            : 'Start by uploading a book to convert.';
        document.getElementById('welcome-stats').textContent = statsText;
        
        // Show activity panel if there are in-progress jobs
        if (data.in_progress > 0) {
            document.getElementById('activity-section').classList.remove('hidden');
            // Activity cards would be populated by polling - for now show placeholder
            document.getElementById('activity-cards').innerHTML = `
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
        
        const grid = document.getElementById('library-grid');
        const empty = document.getElementById('library-empty');
        
        if (data.books.length === 0) {
            grid.classList.add('hidden');
            empty.classList.remove('hidden');
        } else {
            renderLibraryGrid(data.books);
        }
        
        // Set default sort button as active
        document.querySelector('.sort-btn[data-sort="recent"]').classList.add('bg-dark-600');
        
    } catch (error) {
        console.error('Failed to load library:', error);
        document.getElementById('welcome-stats').textContent = 'Error loading library.';
    }
}

/**
 * Render books into the library grid
 */
function renderLibraryGrid(books) {
    const grid = document.getElementById('library-grid');
    grid.innerHTML = books.map(book => `
        <div class="glass rounded-xl p-4 cursor-pointer hover:border-primary transition"
             onclick="showPlayer('${book.id}')">
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
            <p class="text-sm text-gray-400">${book.total_chapters} chapters • ${book.total_duration || '--'}</p>
        </div>
    `).join('');
}

/**
 * Sort library by criteria
 */
function sortLibrary(criteria) {
    // Update button states
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.classList.toggle('bg-dark-600', btn.dataset.sort === criteria);
    });
    
    // Sort books
    let sorted = [...state.library];
    if (criteria === 'az') {
        sorted.sort((a, b) => a.title.localeCompare(b.title));
    } else {
        // 'recent' - sort by created_at descending
        sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }
    
    renderLibraryGrid(sorted);
}

// ============================================
// Utilities
// ============================================

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Open a book in the player view
 * @param {string} bookId - ID of the book to play
 */
function showPlayer(bookId) {
    state.currentBook = bookId;
    showView('player');
}

// ============================================
// Initialize App
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    showView('upload');
});
