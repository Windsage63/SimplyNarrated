# TTS Multi-Model Architecture Plan

**Date:** 2026-05-02  
**Branch:** Refactor-Docling  
**Status:** Draft — Awaiting Approval

---

## Answers to Clarifying Questions (Recorded)

| # | Question | Answer |
| --- | -------- | ------ |
| 1 | Model selection scope | Dropdown on upload page below "Select Narrator Voice", default blank (selection required). Model stored in book metadata for reconvert. |
| 2 | Footnote handling | **Product decision:** Remove the entire legacy audio-settings surface in Phase 1 plumbing, including footnote toggles. These settings are no longer part of the supported product flow. |
| 3 | CosyVoice version | CosyVoice2-0.5B with reference voices (no cloning yet). |
| 4 | Kokoro fate | Kokoro remains as a selectable model. Legacy books without model field get `kokoro` auto-assigned. |
| 5 | Multi-user / multi-model | Single user, single machine — only one model active at a time. |

### Additional Decisions

  - **All models installed via `install.bat`** — CosyVoice2 is not optional; both models install together on setup once Phase 2 lands.
  - **Phase 1 simplification** — Remove the current upload-page audio settings and related request/config fields at the same time as the TTS plumbing refactor.
  - **Model registry timing** — Introduce the registry in Phase 1, but register only `kokoro` initially. CosyVoice2 is added to the registry in Phase 2.
  - **Config file** — A new `config.yaml` (or `config.json`) will centralize TTS model/voice settings, loaded at startup as a single source of truth.
  - **Library usage** — Kokoro via `kokoro` Python library (`from kokoro import KPipeline`). CosyVoice2 via direct Python library (`cosyvoice.cli.cosyvoice.AutoModel`). No Docker, no vLLM, no LM Studio required.
  - **CosyVoice2 reference voices** — English reference audio samples will be curated as a project-managed preset pack from first-party recordings or clearly licensed external corpora. They are not taken from Kokoro `.pt` voice assets, and they are not assumed to ship with CosyVoice2 itself.

---

## Current Architecture (Baseline)

```markdown
┌─────────────────────────────────────────────────────┐
│  Frontend (upload.js)                               │
│  - Voice cards from /api/voices                     │
│  - Audio settings: speed, quality, footnote removal │
│  - Preview via /api/voice-sample/{voice_id}         │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  API Routes (routes.py)                             │
│  - POST /generate → GenerateRequest schema          │
│  - GET  /voices → PRESET_VOICES (Kokoro only)       │
│  - GET  /voice-sample/{id} → Kokoro generate_sample │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  Pipeline (pipeline.py)                             │
│  - get_tts_engine() → Kokoro TTSEngine singleton    │
│  - Config: voice, speed, quality, footnotes         │
│  - generate_speech(text, voice_id, speed)           │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  TTSEngine (tts_engine.py) — Kokoro-specific        │
│  - KPipeline (American / British)                   │
│  - PRESET_VOICES list (28 Kokoro voices)            │
│  - .pt voice files in static/voices/                │
└─────────────────────────────────────────────────────┘
```

---

## Phase 1: Abstract Kokoro into Selectable Engine

### Goal

Decouple Kokoro from being the hardcoded TTS backend, remove the obsolete audio-settings surface, and land a model registry that initially contains only Kokoro.

### Changes Required

### 1.1 Backend — New Abstraction Layer

**File: `src/core/tts_engine.py`**

  - Create `BaseTTSModel` abstract class:

  ```python
  class BaseTTSModel(ABC):
      name: str              # "kokoro" or "cosyvoice2"
      
      @abstractmethod
      def load(self) -> None: ...
      @abstractmethod
      def unload(self) -> None: ...
      @abstractmethod
      def is_loaded(self) -> bool: ...
      @abstractmethod
      def get_voices(self) -> List[VoiceConfig]: ...
      @abstractmethod
      def generate_speech(self, text: str, voice_id: str) -> Tuple[np.ndarray, int]: ...
      @abstractmethod
      def generate_sample(self, voice_id: str) -> Tuple[np.ndarray, int]: ...
  ```

  - Rename current `TTSEngine` → `KokoroTTSModel` (implements `BaseTTSModel`)

  - Create `TTSModelManager` singleton:

  ```python
  class TTSModelManager:
    _active_model: Optional[BaseTTSModel] = None
    _model_registry: Dict[str, type] = {
      "kokoro": KokoroTTSModel,
    }

    def switch_model(self, model_name: str) -> BaseTTSModel:
      # Unload current, load new, return instance
    def get_active_model(self) -> BaseTTSModel:
      # Return or auto-load default (kokoro)
    def get_available_model_names(self) -> List[str]:
      ...
  ```

  - Replace `get_tts_engine()` → `get_tts_manager()`
  - Phase 1 registry contains only `kokoro`; CosyVoice2 registration is deferred to Phase 2

### 1.2 Backend — Schema Updates

**File: `src/models/schemas.py`**

  - **`GenerateRequest`** — add field:

  ```python
  model: str = Field(default="kokoro", description="TTS model ID")
  ```

  - **`GenerateRequest`** — remove fields:
    - `speed` (controlled at playback)
    - `quality` (SD is universal)
    - `remove_square_bracket_numbers` (Docling handles this)
    - `remove_paren_numbers` (Docling handles this)

  - **`ReconvertChapterRequest`** — add field:

  ```python
  model: Optional[str] = Field(default=None)
  ```

  Remove: `speed`, `quality`, `format` (use metadata defaults)

  - **`VoiceInfo`** — add field:

  ```python
  model: str  # Which model this voice belongs to
  ```

  - **`BookInfo`** — add fields so the frontend can reconvert using stored settings:

  ```python
  model: Optional[str] = None
  voice: Optional[str] = None
  ```

### 1.3 Backend — Library Metadata

**File: `src/core/library.py`**

  - **`BookMetadata`** dataclass — add field:

  ```python
  model: Optional[str] = None  # "kokoro" or "cosyvoice2"
  ```

  - **Migration logic:** When loading a book where `model` is `None`, auto-assign `"kokoro"` (legacy behavior)

### 1.4 Backend — Pipeline Updates

**File: `src/core/pipeline.py`**

  - Replace `get_tts_engine()` calls with `get_tts_manager().get_active_model()`
  - Remove the legacy audio-settings plumbing (`speed`, `quality`, `remove_square_bracket_numbers`, `remove_paren_numbers`)
  - Remove footnote stripping logic (`strip_square`, `strip_paren`)
  - Remove `speed` from `generate_speech()` calls (Kokoro's speed param, default 1.0)
  - Store `model` in book metadata when saving
  - Remove `quality` from encoder settings (hardcode SD)

### 1.5 Backend — Chapter Reconvert

**File: `src/core/chapter_reconvert.py`**

  - Read `model` from book metadata
  - On reconvert, ensure the correct model is active (switch if needed)
  - Use model + voice from metadata

### 1.6 Backend — API Routes

**File: `src/api/routes.py`**

  - **`GET /voices`** — accept query param `?model=kokoro`, return voices filtered by model
  - **`GET /models`** — new endpoint returning list of available model names
  - **`POST /models/switch`** — new endpoint to switch active model (unload current, load new)
  - **`GET /voice-sample/{voice_id}`** — use active model's generate_sample
  - **`POST /generate`** — validate voice against selected model's voice list
  - **`AVAILABLE_VOICES`** — replace static list with dynamic lookup from active model
  - In Phase 1, `GET /models` returns only `kokoro`; the registry-backed route shape lands before the second model does

### 1.7 Frontend — Upload Page

**File: `static/js/views/upload.js`**

  - Add `<select>` dropdown below "Select Narrator Voice" heading:
    - Options fetched from `GET /api/models`
    - Default: blank (empty string, selection required)
    - On change: call `POST /api/models/switch`, then re-call `loadVoices()` with model param
    - In Phase 1, this list contains only `kokoro`

  - **`loadVoices()`** — update to accept model param:

  ```js
  async function loadVoices(model) {
      const data = await api.getVoices(model);
      // ... render voice cards
  }
  ```

  - **Remove entire "Audio Settings" section** (speed slider, quality buttons, footnote toggles)

  - Enable/disable convert button based on: file selected AND model selected AND voice selected

### 1.8 Frontend — State Management

**File: `static/js/app.js`**

  - Add to `state`:

  ```js
  selectedModel: null,  // null means not yet selected
  ```

  - Reset `selectedVoice` default to `null` so the user must select a voice after selecting a model

  - Remove from `state.audioSettings`:
    - `speed`
    - `quality`
    - `removeSquareBracketNumbers`
    - `removeParenNumbers`

  - Update `api.generate()` payload to include `model`

### 1.9 Frontend — Player / Reconvert

**File: `static/js/views/player.js`**

  - When triggering chapter reconvert, send `model` from book metadata
  - Ensure model is switched (if needed) before reconversion starts

### 1.10 Config File (New)

**New file: `config.yaml`** (or `config.json`)

Centralized configuration loaded at startup:

```yaml
tts:
  default_model: "kokoro"
  models:
    kokoro:
      enabled: true
      voices_file: "static/voices/kokoro_voices.json"
      repo_id: "hexgrad/Kokoro-82M"
```

  - Single source of truth for model/voice configuration
  - Phase 1 config contains only `kokoro`; Phase 2 extends the file with `cosyvoice2`
  - Allows enabling/disabling models without code changes

### 1.11 Install Script

**File: `install.bat`**

  - Update Kokoro preload to use new manager API
  - Load config file at startup
  - Preload default model at startup
  - Do **not** add CosyVoice2 download/install work until Phase 2

---

## Phase 2: Add CosyVoice2-0.5B

### Goal

Integrate CosyVoice2-0.5B as a second selectable model with reference voices.

### Changes Required

### 2.1 Dependencies

**File: `requirements.txt`**

Add under a new `# TTS Model - CosyVoice2` section:

```markdown
# TTS Model - CosyVoice2
cosyvoice>=0.1.0
funasr>=1.1.0
modelscope>=1.18.0
WeTextProcessing>=1.0.4
```

**Note:** CosyVoice2 installs alongside Kokoro via `install.bat` (not optional).

**Validation gate:** Confirm these dependencies work in the project's Windows embedded Python runtime before merging the install changes.

### 2.2 CosyVoice2 Reference Voice Research

**Key Finding:** CosyVoice2 has **no built-in English voice catalog** — it is a pure zero-shot system. Any clean audio clip (10-30 seconds) can serve as a reference voice. The model extracts a speaker embedding at inference time — no predefined speaker registry is needed.

**Kokoro compatibility note:** Kokoro voice IDs and `.pt` voice files cannot be passed directly into CosyVoice2 as equivalent voices. CosyVoice2 expects prompt audio, matching prompt text for zero-shot registration, or a previously saved speaker profile. A Kokoro-generated sample clip could be used experimentally as synthetic prompt audio, but that would only approximate a new CosyVoice2 preset and would not be treated as "the same voice" in this plan.

**Only provided reference audio files:**

  - `zero_shot_prompt.wav` — Chinese voice sample (default demo prompt)
  - `cross_lingual_prompt.wav` — Cross-lingual inference prompt

**Download URLs:**

  - `https://github.com/FunAudioLLM/CosyVoice/raw/main/asset/zero_shot_prompt.wav`
  - `https://github.com/FunAudioLLM/CosyVoice/raw/main/asset/cross_lingual_prompt.wav`

---

### 2.2.1 Recommended English Reference Voice Sources

**Preferred order of acquisition:**

1. First-party recorded prompt clips curated specifically for SimplyNarrated
2. Openly licensed speech corpora with clear redistribution terms
3. User-supplied prompt audio in Phase 3 voice-cloning flows

**Primary source: VCTK Corpus** (110 English speakers, diverse accents, CC BY 4.0)

  - Download: `https://datashare.ed.ac.uk/handle/10283/3443`
  - Format: Individual .flac files per speaker, 48kHz/24-bit
  - Contains: ~400 sentences per speaker, speaker IDs (p22xx–p43xx), gender/accent metadata
  - **Best choice:** Labelled with gender, accent, and region — easy to select specific voice characteristics

**Secondary source: LibriTTS** (~2,851 speakers, CC BY 4.0)

  - Download: `https://openslr.org/60/`
  - Format: Individual .wav files per utterance, 24kHz
  - Quality tiers: `train-clean-100` (highest), `train-clean-360`, `train-other-500`
  - **Best choice:** Highest-quality book readings (LibriVox-derived), ~585 hours total

---

### 2.2.2 Proposed Reference Voice Selection (10 voices)

**Target:** 5 female, 5 male, mix of American/British accents

**Suggested VCTK speakers** (British accent diversity):

| Voice ID | Speaker | Gender | Accent | Notes |
| -------- | ------- | ------ | ------ | ----- |
| `cv_vctk_p225` | p225 | 🚺 | British (Southern England) | Clear, warm |
| `cv_vctk_p239` | p239 | 🚺 | British | Professional tone |
| `cv_vctk_p251` | p251 | 🚺 | British (Scottish) | Distinct accent |
| `cv_vctk_p264` | p264 | 🚺 | British | Soft, gentle |
| `cv_vctk_p277` | p277 | 🚺 | British | Narration-style |
| `cv_vctk_p230` | p230 | 🚹 | British (Southern England) | Deep, authoritative |
| `cv_vctk_p237` | p237 | 🚹 | British | Clear, confident |
| `cv_vctk_p257` | p257 | 🚹 | British | Smooth, calm |
| `cv_vctk_p272` | p272 | 🚹 | British | Storytelling tone |
| `cv_vctk_p282` | p282 | 🚹 | British | Warm, friendly |

**Alternative: LibriTTS speakers** (for American accent):

  - Download `train-clean-100` subset (~428 speakers, ~100 hours)
  - Pick individual speaker folders, extract a few clean utterances (10-30 sec each)
  - Speaker IDs are UUIDs (e.g., `100`, `1080`, `1612`, `3047`, `5027`)

**Recommended approach:**

1. Prefer first-party recorded prompt clips when available
2. Use **VCTK** for British voices (pre-labelled, easy to select)
3. Use **LibriTTS train-clean-100** for American voices if licensing/distribution review passes
4. Extract 10-30 second clean clips from each speaker
5. Capture and store the exact prompt transcript for each reference clip
6. Store as `.wav` in `static/voices/cosyvoice2/references/`
7. Define voice metadata in `static/voices/cosyvoice2/cosyvoice2_voices.json`

**Reference storage structure:**

```tree
static/voices/cosyvoice2/
├── cosyvoice2_voices.json      # Voice metadata (id, name, gender, description, ref_path, prompt_text)
└── references/
    ├── cv_vctk_p225.wav
    ├── cv_vctk_p239.wav
    ├── cv_vctk_p251.wav
    ├── cv_vctk_p264.wav
    ├── cv_vctk_p277.wav
    ├── cv_vctk_p230.wav
    ├── cv_vctk_p237.wav
    ├── cv_vctk_p257.wav
    ├── cv_vctk_p272.wav
    └── cv_vctk_p282.wav
```

---

### 2.3 CosyVoice Model Implementation

**New file: `src/core/cosyvoice_engine.py`**

```python
class CosyVoice2Model(BaseTTSModel):
    name = "cosyvoice2"
    
    def load(self) -> None:
      # Download/init CosyVoice2-0.5B from HuggingFace
        # Load reference voice list
        
    def unload(self) -> None:
        # Release model from memory/VRAM
        
    def get_voices(self) -> List[VoiceConfig]:
      # Return project-curated CosyVoice reference voices
        
    def generate_speech(self, text, voice_id) -> Tuple[np.ndarray, int]:
        # Use CosyVoice2 inference with reference voice
        
    def generate_sample(self, voice_id) -> Tuple[np.ndarray, int]:
        # Generate preview sample
```

### 2.4 Model Registry

**File: `src/core/tts_engine.py`**

Register CosyVoice2:

```python
_available_models = {
    "kokoro": KokoroTTSModel,
    "cosyvoice2": CosyVoice2Model,
}
```

### 2.5 Reference Voices

  - Store CosyVoice2 reference audio clips in `static/voices/cosyvoice2/`
  - Each reference: short `.wav` file + metadata (name, gender, description, prompt_text)
  - Map voice IDs to reference audio paths

### 2.6 Install Script

**File: `install.bat`**

  - Update to include CosyVoice2 model download (~2GB)
  - Install CosyVoice2 Python dependencies
  - Download reference voice clips
  - Preload both Kokoro and CosyVoice2 at startup (configurable via config file)

### 2.6 Frontend Updates

  - CosyVoice2 voices appear in dropdown when model selected
  - Voice cards render with CosyVoice-specific info

---

## Phase 3: Voice Cloning

### Goal

Add zero-shot voice cloning for models that support it (CosyVoice2).

### Changes Required

### 3.1 UI — Voice Cloning Modal

**File: `static/js/views/upload.js`** (or new `voice-cloning.html` modal)

  - Trigger: button in voice selection area "Clone a Voice"
  - Modal content:
    - Upload reference audio (10-30 seconds, .wav/.mp3)
    - Enter voice name
    - Preview cloned voice
    - Save to book's cloned voices

### 3.2 Backend — Cloning API

**File: `src/api/routes.py`**

  - `POST /voice-clone/preview` — generate sample with cloned voice
  - `POST /voice-clone/save` — persist cloned voice reference

### 3.3 Backend — CosyVoice Cloning

**File: `src/core/cosyvoice_engine.py`**

  - `generate_speech(text, voice_id, reference_audio_path)` — use zero-shot cloning
  - Store cloned voice references in `data/library/{book_id}/cloned-voices/`

---

## Target Architecture (Post-Phase 2)

```markdown
┌─────────────────────────────────────────────────────┐
│  Frontend (upload.js)                               │
│  - Model dropdown (kokoro | cosyvoice2)             │
│  - Voice cards (loaded per selected model)          │
│  - No audio settings section                        │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  API Routes                                         │
│  - GET  /models → ["kokoro", "cosyvoice2"]          │
│  - POST /models/switch → switch active model        │
│  - GET  /voices?model=kokoro → filtered voices      │
│  - POST /generate → includes model field            │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  TTSModelManager (singleton)                        │
│  - _active_model: BaseTTSModel                      │
│  - switch_model(name) → unload + load               │
│  - get_active_model() → current model               │
├─────────────────────────────────────────────────────┤
│  BaseTTSModel (ABC)                                 │
│  ├── KokoroTTSModel (kokoro.KPipeline)              │
│  └── CosyVoice2Model (CosyVoice2-0.5B)              │
└─────────────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  Book Metadata (metadata.json)                      │
│  - model: "kokoro" | "cosyvoice2"                   │
│  - voice: voice_id                                  │
│  - (used for reconvert to restore correct model)    │
└─────────────────────────────────────────────────────┘
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| CosyVoice2 deps conflict with Kokoro | Medium | Test dependency overlap; use lazy imports |
| VRAM pressure during model switch | Low | Single model active; unload before load |
| Legacy books missing model field | Low | Auto-assign "kokoro" on load |
| CosyVoice2 install size (~2GB) | Low | Both models install via `install.bat` |
| Voice preview caching per model | Low | Cache key includes model name in subdirectory |
| Phase 1 removal of legacy audio settings touches frontend, API, pipeline, and tests | Medium | Remove the entire settings surface in one pass and update tests/fixtures in the same PR |
| Attempting to reuse Kokoro voices directly in CosyVoice2 | Medium | Treat CosyVoice2 presets as a separate curated reference-audio library; do not map Kokoro `.pt` voices directly |
| Config file migration | Low | Auto-generate `config.yaml` on first run if missing |

---

## Open Questions (Resolved)

| # | Question | Resolution |
| --- | -------- | ---------- |
| 1 | CosyVoice2 reference voice count | 10 voices (5F, 5M). Source: VCTK corpus for British voices (pre-labelled with gender/accent). LibriTTS available for American accent expansion. Specific speaker IDs selected (see section 2.2.2). |
| 2 | Model switch timing | Switching models preserves file selection but resets voice selection (voice may not exist in new model). |
| 3 | CosyVoice2 install approach | All models via `install.bat` — no separate script. |
| 4 | Voice preview caching | Yes — cache per model in `static/voices/audio/{model_name}/{voice_id}.mp3`. |
| 5 | Can Kokoro voices be reused directly in CosyVoice2? | No. Kokoro `.pt` voices are model-specific assets, while CosyVoice2 needs reference audio plus prompt text or a saved speaker profile. Synthetic Kokoro-generated prompt audio is an optional experiment, not part of the planned preset strategy. |
