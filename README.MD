# Video Auto Translation & Processing | [TIẾNG VIỆT](./README_vn.MD)

Automated pipeline for video translation, vocal/music separation, voice cloning (TTS), subtitle generation, subtitle watermark removal (delogo), and video re-rendering.

## 1. Installation
**Prerequisites**
- Python and pip.
- FFmpeg and ffprobe installed and available on `PATH`.

Install the cross-platform baseline from the project root:
```powershell
python -m pip install -r requirements.txt
```
The requirements file uses the CPU ONNX Runtime extra by default. Install only one `audio-separator` backend; do not combine CPU, GPU, and DirectML ONNX Runtime packages in the same environment.

**Optional GPU backends**

NVIDIA: replace the default audio-separator CPU backend with its GPU extra, and install a PyTorch build matching the CUDA version supported by your driver:
```powershell
python -m pip uninstall -y audio-separator onnxruntime
python -m pip install "audio-separator[gpu]"
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

AMD on Windows: use DirectML instead of the NVIDIA/CUDA packages:
```powershell
python -m pip uninstall -y audio-separator onnxruntime onnxruntime-gpu onnxruntime-directml
python -m pip install "audio-separator[dml]"
```
For AMD on Linux, install a PyTorch/ROCm build supported by the GPU and OS. Whisper through CTranslate2 currently uses CPU on AMD.

**Automatic hardware selection**
- Demucs uses CUDA or DirectML when the matching Torch and ONNX Runtime providers are available; otherwise it uses CPU.
- Whisper uses CUDA only when CTranslate2 reports a usable CUDA device. It falls back to CPU `int8` if GPU model initialization fails.
- XTTS and EasyOCR use the supported PyTorch GPU runtime; XTTS falls back to CPU when unavailable.
- Rendering selects a compatible NVIDIA or Windows AMD encoder when available. If hardware encoding fails, it retries with a software CPU encoder.

**Soft render**
Set `SOFT_RENDER=True` in `.env` to copy the original video stream without re-encoding, subtitles, delogo, images, or overlays, while still mixing and re-encoding audio. It preserves the full source duration, so `-st` and `-en` are ignored. Set `SOFT_RENDER=False` for normal video rendering.

**Configuration**
- API key: [assets/_curren_key](assets/_curren_key)
- FFmpeg: [assets/ffmpeg_config.json](assets/ffmpeg_config.json)
- Render style and audio tracks: [assets/render_config.json](assets/render_config.json)
- Environment settings: [.env](.env)
- Source configuration: [src/configuration.py](src/configuration.py)

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
