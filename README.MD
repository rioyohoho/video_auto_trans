# Video Auto Translation & Processing | [TIẾNG VIỆT](./README_vn.MD)

Automated pipeline for video translation, vocal/music separation, voice cloning (TTS), subtitle generation, subtitle watermark removal (delogo), and video re-rendering.

## 1. Installation
**System Requirement**

**FFmpeg** must be installed and added to system `PATH`.

**Configuration**
- API key: [assets/_curren_key](assets/_curren_key)
- FFmpeg: [assets/ffmpeg_config.json](assets/ffmpeg_config.json)
- Style: [assets/render_config.json](assets/render_config.json)
- Enviroment: [.env](.env)
- Source config: [src/configuration.py](src/configuration.py)


### Step 1: Base Libraries (Common for CPU & GPU)
1. **Dependencies**
    ```
    pip install colorama pydub scipy numpy pyperclip python-dotenv PyQt6 textual deep-translator translators gTTS google-genai coqui-tts
    ```
### Step 2: Hardware-Specific Libraries
1. **Option A: CPU Only**
    ```
    # PyTorch CPU & ONNX Runtime CPU
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    pip install onnxruntime
    # AI Models (Demucs, Whisper, OCR)
    pip install easyocr audio-separator faster-whisper
    ```
2. **Option B: NVIDIA GPU**
    ```
    # PyTorch for CUDA 12.1
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    # ONNX Runtime GPU (CUDA 12 compatible version)
    pip install "onnxruntime-gpu==1.20.0" nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12
    # AI Pipeline Models
    pip install easyocr audio-separator faster-whisper
    ```
## 2. Usage & Parameter Reference
**Quick Commands**
  - Interactive UI Menu: python menu.py -i <video_or_folder>
  - Batch Pipeline Runner: python exec.py -i <video_or_folder>
  - Manual Delogo GUI: python s5.1_ocr_delogo_gui.py -i <video_file>

**Quick Examples**
1. Directory path
    ```
    cd [PROJECT_PATH]
    ```
2. Open Terminal UI
    ```
    python menu.py -i "[VIDEO_OR_FOLDER_PATH]"
    ```
3. Run full pipeline for all videos in a folder
    ```
    python exec.py -i "[VIDEO_OR_FOLDER_PATH]"
    ```

**Parameters Table**
| Index  | Command / Script         | Caption (Purpose)                       | Key Parameters                                                                                                                                                                                                                                |
| :----: | :----------------------- | :-------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ALL`  | `exec.py`                | Run entire pipeline sequentially        | `-i` Video or directory<br>`-s0` to `-s6` Enable/disable step (`1`/`0`)<br>`-nw` Run tasks in new console window (`True`/`False`)                                                                                                             |
| `UI`  | `menu.py`                | Interactive Terminal UI dashboard       | `-i` Video or directory path                                                                                                                                                                                                                  |
| `s0`   | `s0_demucs.py`           | Separate vocal & music                  | `-i` Input path<br>`-m` Model mode (`voc` or `inst`)                                                                                                                                                                                          |
| `s1`   | `s1_transcribe.py`       | Audio to text (Whisper)                 | `-i` Input path<br>`-l` Language (`auto` or language code)<br>`-c` Mode (`transcribe`, `transcribe_length`, `transcribe_range`)<br>`-c-bs` Beam size (`5`)<br>`-c-wt` Word timestamps (`True`/`False`)<br>`-c-vf` VAD filter (`True`/`False`) |
| `s2`   | `s2_translates.py`       | Translate subtitles                     | `-i` Input path<br>`-l` Target languages (`vi`, `en`, ...)<br>`-m` Engine (`0`: Auto, `1`: Google, `2`: Gemini AI, `3`: Local)<br>`-s` Export `.srt` (`True`/`False`)                                                                         |
| `s3`   | `s3_Google_speech.py`    | Text to speech via Google TTS           | `-i` Input path<br>`-l` Target languages<br>`-p` Pitch (`1.39`)<br>`-a` Tempo/speed (`1.25`)<br>`-v` Volume multiplier (`2.0`)                                                                                                                |
| `s3.1` | `s3_AI_speech.py`        | Voice clone TTS via XTTS-v2             | `-i` Input path<br>`-t` Reference voice sample audio<br>`-l` Language code                                                                                                                                                                    |
| `s4`   | `s4_srt.py`              | Word-level / Karaoke SRT                | `-i` Input path<br>`-l` Target languages<br>`-w` Words per chunk (`1`)<br>`-k` Active word color hex (`#00aaff`)                                                                                                                              |
| `s5`   | `s5_ocr_delogo.py`       | Auto-detect hardsub blur box            | `-i` Input video path<br>`-a` ROI area enum (`123`: Bottom, `789`: Top, ...)<br>`-am` Subtitle max length mode (`True`/`False`)<br>`-tm` Full-length timeline blur (`True`/`False`)                                                           |
| `s5.1` | `s5.1_ocr_delogo_gui.py` | GUI editor for delogo bounding box      | `-i` Video path<br>`-a` Initial area code<br>`-am` Subtitle max mode (`True`/`False`)<br>`-tm` Timestamp max mode (`True`/`False`)                                                                                                            |
| `s6`   | `s6_video_complex.py`    | Render final video | `-i` Input path<br>`-o` Output path<br>`-l` Target language<br>`-c` Config JSON path<br>`-st` Start trim (seconds)<br>`-en` End trim (seconds)                                                                                                |
