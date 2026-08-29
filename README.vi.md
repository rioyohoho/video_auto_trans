## [ENGLISH INSTRUCTIONS](./README.md)

# video_auto_trans
Dự án này ứng dụng các mô hình Trí tuệ Nhân tạo (AI) để cung cấp các giải pháp tự động hóa video và âm thanh toàn diện, bao gồm: tách giọng/nhạc, chuyển văn bản thành giọng nói (Text-to-Speech), nhận diện giọng nói thành văn bản (Speech-to-Text) và dịch thuật tự động.

---

## Yêu cầu hệ thống
 - Python phiên bản **3.10 trở lên**

### 1. Cập nhật pip & wheel
```
pip install --upgrade pip setuptools wheel
```

### 2. Cài đặt các thư viện cần thiết
```
pip install pydub
pip install faster-whisper
pip install gTTS
pip install google-genai deep_translator

pip install pyannote.audio==3.3.2 --no-deps # Sửa lỗi onnxruntime cho CUDA
pip install praat-parselmouth

pip install easyocr                             
pip install python-dotenv colorama tabulate
pip install omegaconf semver speechbrain tensorboardx "click>=8.4.2"
```

---

## Cài đặt PyTorch

### Dành cho máy chạy CPU:
```
pip install "audio-separator"
py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-cache-dir
```

### Dành cho máy chạy GPU (NVIDIA CUDA):
```
pip install "audio-separator[gpu]"
py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall --no-cache-dir
```

> **Khắc phục sự cố onnxruntime GPU:**
> ```
> py -m pip uninstall onnxruntime-gpu onnxruntime -y
> py -m pip install onnxruntime-gpu==1.19.0
> ```

---

## Cấu hình mặc định
* Tệp cấu hình: **[configuration](src/configuration.py)**
* Biến môi trường: **[enviroments](.env)**

* Thư mục đầu vào mặc định (`--input`): **[.env:PATH_DIR](.env#1)** *hoặc* **[src/configuration.py:P_DIR](src/configuration.py#9)**
* Ngôn ngữ mặc định (`--language`): **[.env:LANGS](.env#24)** *hoặc* **[src/configuration.py:LANGS](src/configuration.py#33)**

---

## Hướng dẫn sử dụng & Ví dụ

### 1. Tách âm thanh (Demucs)
Tách giọng nói (vocal) và nhạc nền (instrumental/noise) từ video hoặc âm thanh.

<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td>
            <table><tr><th>Loại</th><th>Lệnh thực thi</th></tr><tr><td><b>Mặc định</b></td><td><code>python s0_demucs.py</code></td></tr></table>
            <table><tr><th>Tham số</th><th>Viết tắt</th><th>Tên đầy đủ</th><th>Ví dụ</th></tr><tr><td>Đầu vào (input)</td><td>-i</td><td>--input</td><td>-i "D:/videos"</td></tr><tr><td>Đầu ra (output)</td><td>-o</td><td>--output</td><td>-o "D:/videos/test"</td></tr></table>
        </td>
        <td>
            <img src="https://github.com/user-attachments/assets/4802c163-bd40-4556-868c-9d5a9069a7d6" height="300px" style="display: block;" />
        </td>
    </tr>
</table>

```
python s0_demucs.py -i "D:/test.mp4"
```

---

### 2. Chuyển giọng nói thành văn bản (Transcribe)
Sử dụng AI để bóc băng/chuyển đổi lời thoại trong video/audio thành văn bản.

<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td>
            <table><tr><th>Loại</th><th>Lệnh thực thi</th></tr><tr><td><b>Mặc định</b></td><td><code>python s1_transcribe.py</code></td></tr></table>
            <table><tr><th>Tham số</th><th>Viết tắt</th><th>Tên đầy đủ</th><th>Ví dụ</th></tr><tr><td>Đầu vào</td><td>-i</td><td>--input</td><td>-i "D:/videos"</td></tr><tr><td>Độ rộng chùm tia (beam)</td><td>-c-bs</td><td>--beam_size</td><td>-c-bs 5</td></tr><tr><td>Bộ lọc khoảng lặng (VAD)</td><td>-c-vf</td><td>--vad_filter</td><td>-c-vf True</td></tr></table>
        </td>
        <td>
            <img src="https://github.com/user-attachments/assets/5dbf008a-d6a7-46d9-b26a-a6c8f33715de" height="300px" style="display: block;" />
        </td>
    </tr>
</table>

```
python s1_transcribe.py -i "D:/test.mp4"
```

---

### 3. Dịch văn bản / Phụ đề (Translate)
Dịch nội dung văn bản hoặc phụ đề đã tạo sang ngôn ngữ mong muốn.

<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td>
            <table><tr><th>Loại</th><th>Lệnh thực thi</th></tr><tr><td><b>Mặc định</b></td><td><code>python s2_translate.py</code></td></tr></table>
            <table><tr><th>Tham số</th><th>Viết tắt</th><th>Tên đầy đủ</th><th>Ví dụ</th></tr><tr><td>Đầu vào</td><td>-i</td><td>--input</td><td>-i "D:/data.json"</td></tr><tr><td>Ngôn ngữ đích</td><td>-l</td><td>--language</td><td>-l "vi"</td></tr></table>
        </td>
        <td>
            <img src="https://github.com/user-attachments/assets/1adf5781-6236-4c71-b241-5bcc99bbad72" height="300px" style="display: block;" />
        </td>
    </tr>
</table>

```
python s2_translates.py -i "D:/test/test.json"
```

---

### 4. Chuyển văn bản thành giọng đọc AI (XTTS)
Tạo giọng đọc AI từ văn bản hoặc sao chép/nhái giọng đọc mẫu (Voice Cloning).

<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td>
            <table>
                <tr><th>Loại</th><th>Lệnh thực thi</th></tr>
                <tr><td><b>Mặc định</b></td><td><code>python s3.1_AI_speechs.py</code></td></tr>
            </table>
            <table>
                <tr><th>Tham số</th><th>Viết tắt</th><th>Tên đầy đủ</th><th>Ví dụ</th></tr>
                <tr><td>Đường dẫn / Văn bản</td><td>-i</td><td>--input</td><td>-i "D:/data.json" <i>hoặc</i> -i "Xin chào bạn"</td></tr>
                <tr><td>Đường dẫn xuất file</td><td>-o</td><td>--output</td><td>-o "./output.wav"</td></tr>
                <tr><td>Mẫu giọng nói (template)</td><td>-t</td><td>--temple</td><td>-t "D:/samples/voice.wav"</td></tr>
                <tr><td>Ngôn ngữ</td><td>-l</td><td>--language</td><td>-l "vi" <i>hoặc</i> -l "en"</td></tr>
            </table>
        </td>
        <td>
            <img src="https://github.com/user-attachments/assets/04fde322-4991-4ba7-af98-b4aa21e88498" height="300px" style="display: block;" />
        </td>
    </tr>
</table>

```
python s3.1_AI_speechs.py -l "vi" -o "./test.wav" -t "assets/tmp_voices/Adam.mp3" -i "Xin chào, đây là giọng nói AI thử nghiệm."
```

---

### 5. Tạo phụ đề SRT ngắt theo số lượng từ (Word Count)
Tạo tệp phụ đề SRT có chia mốc thời gian chi tiết theo từng từ.

<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td>
            <table>
                <tr><th>Loại</th><th>Lệnh thực thi</th></tr>
                <tr><td><b>Mặc định</b></td><td><code>python s4_transcribe.py</code></td></tr>
            </table>
            <table>
                <tr><th>Tham số</th><th>Viết tắt</th><th>Tên đầy đủ</th><th>Ví dụ</th></tr>
                <tr><td>Đường dẫn đầu vào</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>hoặc</i> -i "D:/audio.mp3"</td></tr>
                <tr><td>Ngôn ngữ</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>hoặc</i> -l "vi"</td></tr>
                <tr><td>Số từ mỗi dòng phụ đề</td><td>-w</td><td>--words</td><td>-w 1 <i>hoặc</i> -w 10</td></tr>
                <tr><td>Kích thước beam (Beam size)</td><td>-c-bs</td><td>--beam_size</td><td>-c-bs 5</td></tr>
                <tr><td>Dấu thời gian theo từ</td><td>-c-wt</td><td>--word_timestamps</td><td>-c-wt True</td></tr>
                <tr><td>Dựa vào ngữ cảnh trước</td><td>-c-copt</td><td>--condition_on_previous_text</td><td>-c-copt False</td></tr>
                <tr><td>Bộ lọc khoảng lặng (VAD)</td><td>-c-vf</td><td>--vad_filter</td><td>-c-vf True</td></tr>
            </table>
        </td>
        <td>
            <img src="https://github.com/user-attachments/assets/c44706bd-4c47-481f-81e7-1859644e8763" height="300px" style="display: block;" />
        </td>
    </tr>
</table>

```
python s3.2_srt.py -i "D:\test\test.vi.mp3" -w 1 -c-vf 0
```

---

### 6. Xử lý & Xuất video nâng cao (Complex Processing)
Tổng hợp âm thanh, phụ đề, dịch thuật và kết xuất (render) thành video hoàn chỉnh.

<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td>
            <table>
                <tr><th>Loại</th><th>Lệnh thực thi</th></tr>
                <tr><td><b>Mặc định</b></td><td><code>python s5_video_complex.py</code></td></tr>
            </table>
            <table>
                <tr><th>Tham số</th><th>Viết tắt</th><th>Tên đầy đủ</th><th>Ví dụ</th></tr>
                <tr><td>Đường dẫn đầu vào</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>hoặc</i> -i "D:/videos/test.mp4"</td></tr>
                <tr><td>Ngôn ngữ</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>hoặc</i> -l "vi"</td></tr>
            </table>
        </td>
        <td>
            <img src="" alt="Video complex" />
        </td>
    </tr>
</table>

```
python D:\dev\py\video_h_complex.py -i "D:\test.mp4"
```
