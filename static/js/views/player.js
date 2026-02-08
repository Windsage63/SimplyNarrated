/**
 * BookTalk - Audiobook Player View
 * Full-featured audiobook player adapted from Stitch design
 */

/**
 * Render the player view
 * @param {string} bookId - ID of the book to play
 */
function renderPlayerView(bookId) {
    return `
        <div class="player-container flex flex-col lg:flex-row gap-8">
            <!-- Main Player Area -->
            <div class="flex-1 glass rounded-2xl p-8">
                <!-- Book Info Header -->
                <div class="text-center mb-8">
                    <h2 id="book-title" class="text-3xl font-bold mb-2">Loading...</h2>
                    <p id="book-author" class="text-lg text-gray-400">--</p>
                </div>
                
                <!-- Book Cover / Gradient Placeholder -->
                <div class="flex justify-center mb-8">
                    <div id="book-cover" class="relative group">
                        <div class="w-64 h-80 rounded-xl bg-gradient-to-br from-primary/40 via-dark-600 to-primary/20 
                                    flex items-center justify-center shadow-2xl border border-white/10">
                            <span class="material-symbols-outlined text-7xl text-white/30">menu_book</span>
                        </div>
                    </div>
                </div>
                
                <!-- Primary Controls -->
                <div class="flex items-center justify-center gap-8 mb-8">
                    <button onclick="skipBackward()" class="text-gray-400 hover:text-white transition p-2">
                        <span class="material-symbols-outlined text-4xl">replay_30</span>
                    </button>
                    <button id="play-btn" onclick="togglePlay()" 
                            class="w-20 h-20 rounded-full bg-white text-dark-900 flex items-center justify-center
                                   hover:scale-105 active:scale-95 transition shadow-xl">
                        <span class="material-symbols-outlined text-5xl" id="play-icon">play_arrow</span>
                    </button>
                    <button onclick="skipForward()" class="text-gray-400 hover:text-white transition p-2">
                        <span class="material-symbols-outlined text-4xl">forward_30</span>
                    </button>
                </div>
                
                <!-- Progress Scrubber -->
                <div class="mb-6">
                    <div class="relative group">
                        <input type="range" id="progress-slider" min="0" max="100" value="0"
                               class="w-full h-2 bg-dark-600 rounded-lg appearance-none cursor-pointer
                                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                                      [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                                      [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:cursor-pointer"
                               oninput="seekTo(this.value)">
                    </div>
                    <div class="flex justify-between mt-2 text-sm">
                        <span id="current-time" class="font-medium">0:00</span>
                        <span id="total-time" class="text-gray-500">0:00</span>
                    </div>
                </div>
                
                <!-- Utility Controls -->
                <div class="flex items-center justify-center gap-6 text-sm">
                    <!-- Speed -->
                    <button onclick="cycleSpeed()" class="flex items-center gap-2 px-3 py-2 rounded-lg 
                                                           bg-dark-600 hover:bg-dark-700 transition">
                        <span class="material-symbols-outlined text-lg">speed</span>
                        <span id="speed-value" class="font-bold">1.0x</span>
                    </button>
                    
                    <!-- Save Bookmark -->
                    <button onclick="saveCurrentBookmark()" class="flex items-center gap-2 px-3 py-2 rounded-lg 
                                                                    bg-dark-600 hover:bg-dark-700 transition">
                        <span class="material-symbols-outlined text-lg">bookmark_add</span>
                        <span>Bookmark</span>
                    </button>
                    
                    <!-- Volume -->
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-lg text-gray-400">volume_up</span>
                        <input type="range" id="volume-slider" min="0" max="100" value="100"
                               class="w-24 h-1 bg-dark-600 rounded-lg appearance-none cursor-pointer
                                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
                                      [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full
                                      [&::-webkit-slider-thumb]:bg-primary"
                               oninput="setVolume(this.value)">
                    </div>
                </div>
            </div>
            
            <!-- Chapter Sidebar -->
            <div class="w-full lg:w-80 glass rounded-2xl flex flex-col max-h-[600px]">
                <div class="p-4 border-b border-white/10 flex items-center justify-between">
                    <h3 class="font-bold">Chapters</h3>
                    <span id="chapter-count" class="text-xs font-bold uppercase tracking-widest text-primary">0 Chapters</span>
                </div>
                <div id="chapter-list" class="flex-1 overflow-y-auto p-2 space-y-1 no-scrollbar">
                    <!-- Chapters will be rendered here -->
                </div>
                <div class="p-4 bg-dark-800/50 border-t border-white/10">
                    <div class="flex items-center justify-between text-xs font-bold text-gray-500 mb-2">
                        <span>OVERALL PROGRESS</span>
                        <span id="overall-progress">0%</span>
                    </div>
                    <div class="h-1.5 w-full bg-dark-600 rounded-full overflow-hidden">
                        <div id="overall-progress-bar" class="h-full bg-primary rounded-full transition-all" style="width: 0%"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Hidden Audio Element -->
        <audio id="audio-player" preload="auto"></audio>
    `;
}

// Player state
const playerState = {
    book: null,
    currentChapter: 1,
    isPlaying: false,
    speed: 1.0,
    audioElement: null,
    bookmarkSaveTimeout: null
};

/**
 * Initialize the player view
 * @param {string} bookId - ID of the book to play
 */
async function initPlayerView(bookId) {
    try {
        // Fetch book details
        const response = await fetch(`/api/book/${bookId}`);
        if (!response.ok) {
            throw new Error('Failed to load book');
        }
        playerState.book = await response.json();
        
        // Update UI with book info
        document.getElementById('book-title').textContent = playerState.book.title;
        document.getElementById('book-author').textContent = playerState.book.author || 'Unknown Author';
        document.getElementById('chapter-count').textContent = `${playerState.book.total_chapters} Chapters`;
        
        // Render chapter list
        renderChapterList();
        
        // Get audio element
        playerState.audioElement = document.getElementById('audio-player');
        setupAudioListeners();
        
        // Load saved bookmark
        await loadBookmark(bookId);
        
        // Load first chapter (or bookmarked position)
        loadChapter(playerState.currentChapter);
        
    } catch (error) {
        console.error('Failed to initialize player:', error);
        document.getElementById('book-title').textContent = 'Error loading book';
    }
}

/**
 * Render the chapter list sidebar
 */
function renderChapterList() {
    const container = document.getElementById('chapter-list');
    if (!playerState.book || !playerState.book.chapters) {
        container.innerHTML = '<p class="text-gray-500 p-4">No chapters found</p>';
        return;
    }
    
    container.innerHTML = playerState.book.chapters.map(chapter => `
        <button onclick="loadChapter(${chapter.number})" 
                class="chapter-item w-full flex items-center gap-3 p-3 rounded-xl transition
                       ${chapter.number === playerState.currentChapter ? 'bg-primary/20 border border-primary/30' : 'hover:bg-dark-700'}">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center
                        ${chapter.number === playerState.currentChapter ? 'bg-primary' : 'bg-dark-600'}">
                <span class="material-symbols-outlined text-sm">
                    ${chapter.number === playerState.currentChapter ? 'equalizer' : 
                      chapter.completed ? 'check_circle' : 'play_arrow'}
                </span>
            </div>
            <div class="flex-1 text-left">
                <p class="text-sm font-medium ${chapter.number === playerState.currentChapter ? 'text-white' : 'text-gray-300'}">
                    ${chapter.title || `Chapter ${chapter.number}`}
                </p>
                <p class="text-xs text-gray-500">${chapter.duration || '--'}</p>
            </div>
        </button>
    `).join('');
}

/**
 * Set up audio element event listeners
 */
function setupAudioListeners() {
    const audio = playerState.audioElement;
    
    audio.addEventListener('timeupdate', () => {
        updateProgressUI();
        autoSaveBookmark();
    });
    
    audio.addEventListener('loadedmetadata', () => {
        document.getElementById('total-time').textContent = formatTime(audio.duration);
        document.getElementById('progress-slider').max = audio.duration;
    });
    
    audio.addEventListener('ended', () => {
        // Auto-advance to next chapter
        if (playerState.currentChapter < playerState.book.total_chapters) {
            loadChapter(playerState.currentChapter + 1);
        } else {
            playerState.isPlaying = false;
            updatePlayButton();
        }
    });
    
    audio.addEventListener('play', () => {
        playerState.isPlaying = true;
        updatePlayButton();
    });
    
    audio.addEventListener('pause', () => {
        playerState.isPlaying = false;
        updatePlayButton();
    });
}

/**
 * Load a specific chapter
 * @param {number} chapterNum - Chapter number to load
 */
function loadChapter(chapterNum) {
    if (!playerState.book) return;
    
    playerState.currentChapter = chapterNum;
    const audio = playerState.audioElement;
    
    // Update audio source
    audio.src = `/api/audio/${playerState.book.id}/${chapterNum}`;
    audio.playbackRate = playerState.speed;
    
    // If was playing, continue playing
    if (playerState.isPlaying) {
        audio.play();
    }
    
    // Update UI
    renderChapterList();
    updateOverallProgress();
}

/**
 * Toggle play/pause
 */
function togglePlay() {
    const audio = playerState.audioElement;
    if (!audio.src) return;
    
    if (playerState.isPlaying) {
        audio.pause();
    } else {
        audio.play();
    }
}

/**
 * Update the play button icon
 */
function updatePlayButton() {
    const icon = document.getElementById('play-icon');
    icon.textContent = playerState.isPlaying ? 'pause' : 'play_arrow';
}

/**
 * Skip backward 30 seconds
 */
function skipBackward() {
    const audio = playerState.audioElement;
    audio.currentTime = Math.max(0, audio.currentTime - 30);
}

/**
 * Skip forward 30 seconds
 */
function skipForward() {
    const audio = playerState.audioElement;
    audio.currentTime = Math.min(audio.duration, audio.currentTime + 30);
}

/**
 * Seek to a specific position
 * @param {number} value - Position in seconds
 */
function seekTo(value) {
    playerState.audioElement.currentTime = value;
}

/**
 * Cycle through playback speeds
 */
function cycleSpeed() {
    const speeds = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0];
    const currentIndex = speeds.indexOf(playerState.speed);
    const nextIndex = (currentIndex + 1) % speeds.length;
    playerState.speed = speeds[nextIndex];
    
    playerState.audioElement.playbackRate = playerState.speed;
    document.getElementById('speed-value').textContent = `${playerState.speed}x`;
}

/**
 * Set volume
 * @param {number} value - Volume 0-100
 */
function setVolume(value) {
    playerState.audioElement.volume = value / 100;
}

/**
 * Update progress UI elements
 */
function updateProgressUI() {
    const audio = playerState.audioElement;
    if (!audio.duration) return;
    
    document.getElementById('current-time').textContent = formatTime(audio.currentTime);
    document.getElementById('progress-slider').value = audio.currentTime;
}

/**
 * Update overall book progress
 */
function updateOverallProgress() {
    if (!playerState.book) return;
    
    const progress = Math.round((playerState.currentChapter / playerState.book.total_chapters) * 100);
    document.getElementById('overall-progress').textContent = `${progress}%`;
    document.getElementById('overall-progress-bar').style.width = `${progress}%`;
}

/**
 * Auto-save bookmark every 30 seconds of playback
 */
function autoSaveBookmark() {
    if (playerState.bookmarkSaveTimeout) return;
    
    playerState.bookmarkSaveTimeout = setTimeout(async () => {
        await saveBookmarkToServer();
        playerState.bookmarkSaveTimeout = null;
    }, 30000);
}

/**
 * Load bookmark from server
 * @param {string} bookId - Book ID
 */
async function loadBookmark(bookId) {
    try {
        const response = await fetch(`/api/bookmark/${bookId}`);
        if (response.ok) {
            const bookmark = await response.json();
            playerState.currentChapter = bookmark.chapter || 1;
            
            // Wait for audio to load, then seek to position
            if (bookmark.position > 0) {
                playerState.audioElement.addEventListener('loadedmetadata', function seekOnce() {
                    playerState.audioElement.currentTime = bookmark.position;
                    playerState.audioElement.removeEventListener('loadedmetadata', seekOnce);
                });
            }
        }
    } catch (error) {
        console.error('Failed to load bookmark:', error);
    }
}

/**
 * Save current position as bookmark
 */
async function saveCurrentBookmark() {
    await saveBookmarkToServer();
    // Visual feedback
    const btn = event.target.closest('button');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<span class="material-symbols-outlined text-lg text-green-400">check</span><span>Saved!</span>';
    setTimeout(() => {
        btn.innerHTML = originalContent;
    }, 1500);
}

/**
 * Save bookmark to server
 */
async function saveBookmarkToServer() {
    if (!playerState.book) return;
    
    try {
        await fetch(`/api/bookmark?book_id=${playerState.book.id}&chapter=${playerState.currentChapter}&position=${playerState.audioElement.currentTime}`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Failed to save bookmark:', error);
    }
}

/**
 * Format seconds to mm:ss
 * @param {number} seconds 
 * @returns {string}
 */
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
