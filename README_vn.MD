# Tự động Dịch & Xử lý Video

Quy trình tự động hóa dùng để dịch video, tách giọng nói/nhạc nền, nhân bản giọng nói (TTS), tạo phụ đề, xóa hình mờ phụ đề (delogo) và render lại video.

## 1. Cài đặt
**Yêu cầu hệ thống**

**FFmpeg** bắt buộc phải được cài đặt và thêm vào biến môi trường `PATH` của hệ thống.

**Cấu hình**
- Khóa API: [assets/_curren_key](assets/_curren_key)
- FFmpeg: [assets/ffmpeg_config.json](assets/ffmpeg_config.json)
- Giao diện/Phong cách: [assets/render_config.json](assets/render_config.json)
- Biến môi trường: [.env](.env)
- Cấu hình nguồn: [src/configuration.py](src/configuration.py)


### Bước 1: Thư viện cơ bản (Dùng chung cho cả CPU và GPU)
1. **Các phụ thuộc (Dependencies)**
    ```
    pip install colorama pydub scipy numpy pyperclip python-dotenv PyQt6 textual deep-translator translators gTTS google-genai
    ```
### Bước 2: Thư viện theo phần cứng
1. **Tùy chọn A: Chỉ dùng CPU**
    ```
    # PyTorch CPU
    pip install torch torchaudio --index-url [https://download.pytorch.org/whl/cpu](https://download.pytorch.org/whl/cpu)
    # ONNX Runtime CPU
    pip install onnxruntime
    # Các mô hình AI (Demucs, Whisper, OCR, XTTS)
    pip install easyocr audio-separator faster-whisper TTS
    ```
2. **Tùy chọn B: GPU NVIDIA (CUDA 12.1)**
    ```
    # PyTorch CUDA
    pip install torch torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
    # ONNX Runtime GPU
    pip install onnxruntime-gpu
    # Các mô hình AI (Demucs, Whisper, OCR, XTTS)
    pip install easyocr audio-separator faster-whisper TTS
    ```
## 2. Hướng dẫn sử dụng & Tham số
**Lệnh nhanh**
  - Giao diện Terminal tương tác: python menu.py -i 
  - Chạy toàn bộ quy trình hàng loạt: python exec.py -i 
  - Giao diện chỉnh sửa xóa logo thủ công: python s5.1_ocr_delogo_gui.py -i 

**Ví dụ nhanh**
1. Đường dẫn thư mục
    ```
    cd [ĐƯỜNG_DẪN_DỰ_ÁN]
    ```
2. Mở giao diện Terminal UI
    ```
    python menu.py -i "[ĐƯỜNG_DẪN_VIDEO_HOẶC_THƯ_MỤC]"
    ```
3. Chạy toàn bộ quy trình cho tất cả video trong một thư mục
    ```
    python exec.py -i "[ĐƯỜNG_DẪN_VIDEO_HOẶC_THƯ_MỤC]"
    ```

**Bảng tham số**
| Chỉ mục | Lệnh / Script | Mô tả (Mục đích) | Tham số chính |
| :----: | :----------------------- | :-------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ALL`  | `exec.py`                | Chạy toàn bộ quy trình tuần tự        | `-i` Video or directory<br>`-s0` to `-s6` Enable/disable step (`1`/`0`)<br>`-nw` Run tasks in new console window (`True`/`False`)                                                                                                             |
| `UI`  | `menu.py`                | Bảng điều khiển giao diện Terminal       | `-i` Video or directory path                                                                                                                                                                                                                  |
| `s0`   | `s0_demucs.py`           | Tách giọng nói và nhạc nền                  | `-i` Input path<br>`-m` Model mode (`voc` or `inst`)                                                                                                                                                                                          |
| `s1`   | `s1_transcribe.py`       | giọng nói -> chữ (Whisper)                 | `-i` Input path<br>`-l` Language (`auto` or language code)<br>`-c` Mode (`transcribe`, `transcribe_length`, `transcribe_range`)<br>`-c-bs` Beam size (`5`)<br>`-c-wt` Word timestamps (`True`/`False`)<br>`-c-vf` VAD filter (`True`/`False`) |
| `s2`   | `s2_translates.py`       | Dịch văn bản                     | `-i` Input path<br>`-l` Target languages (`vi`, `en`, ...)<br>`-m` Engine (`0`: Auto, `1`: Google, `2`: Gemini AI, `3`: Local)<br>`-s` Export `.srt` (`True`/`False`)                                                                         |
| `s3`   | `s3_Google_speech.py`    | chữ -> giọng nói qua Google TTS           | `-i` Input path<br>`-l` Target languages<br>`-p` Pitch (`1.39`)<br>`-a` Tempo/speed (`1.25`)<br>`-v` Volume multiplier (`2.0`)                                                                                                                |
| `s3.1` | `s3_AI_speech.py`        | chữ -> giọng AI TTS qua XTTS-v2             | `-i` Input path<br>`-t` Reference voice sample audio<br>`-l` Language code                                                                                                                                                                    |
| `s4`   | `s4_srt.py`              | SRT theo cấp độ từ / Karaoke                | `-i` Input path<br>`-l` Target languages<br>`-w` Words per chunk (`1`)<br>`-k` Active word color hex (`#00aaff`)                                                                                                                              |
| `s5`   | `s5_ocr_delogo.py`       | Tự động tạo vùng làm mờ hardsub            | `-i` Input video path<br>`-a` ROI area enum (`123`: Bottom, `789`: Top, ...)<br>`-am` Subtitle max length mode (`True`/`False`)<br>`-tm` Full-length timeline blur (`True`/`False`)                                                           |
| `s5.1` | `s5.1_ocr_delogo_gui.py` | GUI chỉnh sửa cần làm mờ      | `-i` Video path<br>`-a` Initial area code<br>`-am` Subtitle max mode (`True`/`False`)<br>`-tm` Timestamp max mode (`True`/`False`)                                                                                                            |
| `s6`   | `s6_video_complex.py`    | Xuất bản lại video | `-i` Input path<br>`-o` Output path<br>`-l` Target language<br>`-c` Config JSON path<br>`-st` Start trim (seconds)<br>`-en` End trim (seconds)                                                                                                |
