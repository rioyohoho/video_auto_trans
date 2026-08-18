# Multimedia Processing Tools Suite

This toolkit comprises four graphical user interface (GUI) applications developed in Python using **PyQt6** and the **FFmpeg** multimedia framework. These tools are designed to streamline specialized workflows, including Text-to-Speech (TTS) voice testing, subtitle removal mask generation (De-subtitling), multi-track audio mixing, and batch video resizing.

---

## Tool Overview

### 1. `s3_1_ui_G_test_audio.py` (Speaker Voice Tester)
A utility designed for testing and fine-tuning synthetic AI voices using Google Text-to-Speech (gTTS) in conjunction with FFmpeg frequency and tempo filters.

*   **Key Features:**
    *   **Text-to-Speech (TTS) Conversion:** Supports multiple target languages (Vietnamese, English, Chinese, Japanese, Korean, etc.).
    *   **Pitch & Speed Adjustments:** Fine-tune pitch (via sample rate adjustment) and playback tempo (`atempo`) per segment or apply them in batch.
    *   **Speaker Management:** Manage multi-speaker configurations using the `diarization.json` schema.
    *   **Data Import:** Import raw text files or structured JSON dialogue lists to generate test audio samples.
    *   **Batch Export:** Export all processed voice tracks as `.wav` files with their corresponding audio configurations.

---

### 2. `s4_1_ui_markers.py` (Pro Canvas Editor & Timeline)
An advanced subtitle editor and automated text-region detection system for generating blur masks. It integrates the EasyOCR engine to automate locating existing hardcoded subtitles on video frames.

*   **Key Features:**
    *   **Video Player & Interactive Timeline:** Visual video canvas with a multi-track timeline supporting segment slicing (`Ctrl+B` or `B` mode), repositioning (`G`), and track boundary trimming.
    *   **Automated Subtitle Eraser (De-subtitling):** Import timestamp data (`transcribe.json`), designate scan regions (Top, Bottom, Center, Left, Right), and use EasyOCR to detect text boundaries, automatically generating timed bounding boxes and exporting them into a `blurs.json` file.
    *   **Subtitle Editor:** Create, import (`data.json`), and modify subtitle lines directly on the live preview canvas. Features full support for Advanced SubStation Alpha (`.ass`) styling properties, including fonts, sizing, colors (Primary, Outline, Shadow, Background Box), alignments, margins, letter spacing, rotation angles, and scaling factors.
    *   **Export Options:** Export standard `.ass` subtitle files or intermediate `.json` workspace data.

---

### 3. `ui_combine_audio.py` (FFmpeg Audio Editor & Mixer)
A visual multi-track audio editor and mixer that lets users arrange various audio clips along a timeline and render the combined output using FFmpeg.

*   **Key Features:**
    *   **Drag-and-Drop Interface:** Directly drag and drop audio files (`.mp3`, `.wav`, `.aac`, `.flac`, `.m4a`, `.ogg`) onto the timeline tracks.
    *   **Timeline Manipulation:** Reposition clip start times across tracks, and trim in/out boundaries directly via mouse dragging or keyboard shortcuts (`Q` to trim start, `E` to trim end at the playhead position).
    *   **Clip Slicing (Split):** Split an active audio clip at the current playhead position using `Ctrl+B`.
    *   **Individual Track Filters:** Independently adjust start offsets, internal trimming, playback speed (`atempo`), pitch shifting (in semitones), and gain/volume levels per clip.
    *   **Mixer Render:** Export the combined master track into common formats such as MP3, WAV, FLAC, AAC, and M4A using FFmpeg's `amix` filter.

---

### 4. `ui_resize-video.py` (Batch Video Resizer)
A batch video resolution and framerate (FPS) conversion utility optimized for high-performance rendering via NVIDIA hardware acceleration (CUDA/NVENC).

*   **Key Features:**
    *   **Batch Queue Management:** Add multiple video files simultaneously via drag-and-drop or the file browser.
    *   **Integrated Preview:** Built-in media player to inspect footage before processing.
    *   **Flexible Parameter Tuning:** Independently configure Width (W), Height (H), Framerate (FPS), and Scaling Ratio per video item, with automatic aspect ratio preservation.
    *   **Hardware Acceleration:** Leverages NVIDIA GPU-accelerated FFmpeg filters (`scale_cuda`) and hardware encoders (`h264_nvenc`) to drastically reduce rendering times.

---

## System Requirements & Installation

### 1. External Dependencies
All tools rely on **FFmpeg** for backend media processing. Make sure FFmpeg is installed and added to your system's Environment Variables (`PATH`):
*   Verify that `ffmpeg` and `ffprobe` commands are accessible directly from your terminal/command prompt.

### 2. Python Libraries
Install the required Python packages using the following command:

```bash
pip install PyQt6 pydub gtts easyocr numpy Pillow
```

*Notes:* 
*   `easyocr` will automatically download the required language models (e.g., Chinese, English, Vietnamese) on its first run.
*   For `ui_resize-video.py`, NVIDIA CUDA hardware acceleration requires an NVIDIA GPU with up-to-date drivers and a compatible CUDA Toolkit installed.

---

## Basic Usage

### Running the Applications
Each tool functions independently as a standalone Python script. Run them from your terminal:

```bash
# Launch Speaker Voice Tester
python s3_1_ui_G_test_audio.py

# Launch Blur Mask Generator & Subtitle Editor
python s4_1_ui_markers.py

# Launch Multi-track Audio Mixer
python ui_combine_audio.py

# Launch Batch Video Resizer
python ui_resize-video.py
```

### Essential Keyboard Shortcuts for `s4_1_ui_markers.py`
*   `V`: Switch to the default Selection/Interaction tool.
*   `G`: Switch to the Move/Transform tool for canvas markers.
*   `B`: Switch to the Cut/Slice tool (Double-click on a bounding box timeline track to cut at that point).
*   `Ctrl + B`: Split the selected bounding box at the current playhead position.
*   `Delete`: Delete the selected bounding boxes or subtitle entries.
*   `I`: Insert a keyframe at the current playhead position.
*   `Shift + I`: Remove the keyframe nearest to the current playhead position.
*   `Space`: Play/Pause video playback (when focused on the player or timeline area).
*   `Ctrl + Z` / `Ctrl + Shift + Z`: Undo / Redo graphic canvas modifications.