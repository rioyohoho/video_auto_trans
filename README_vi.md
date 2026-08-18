# Multimedia Processing Tools Suite

Bộ công cụ này bao gồm 4 ứng dụng giao diện trực quan (GUI) được phát triển bằng ngôn ngữ Python, thư viện đồ họa **PyQt6** và bộ công cụ xử lý đa phương tiện **FFmpeg**. Các công cụ này được thiết kế để hỗ trợ các tác vụ chuyên biệt như: kiểm thử giọng nói nhân tạo (TTS), tạo vùng làm mờ xóa phụ đề (De-subtitles), trộn âm thanh đa băng tần (Audio Mixing) và thay đổi kích thước video hàng loạt (Batch Video Resizing).

---

## Danh sách các công cụ

### 1. `s3_1_ui_G_test_audio.py` (Speaker Voice Tester)
Ứng dụng hỗ trợ kiểm thử và tinh chỉnh cấu hình giọng nói nhân tạo sử dụng thư viện Google Text-to-Speech (gTTS) kết hợp với các bộ lọc tần số và tốc độ của FFmpeg.

*   **Chức năng chính:**
    *   Chuyển đổi văn bản thành giọng nói (TTS) với tùy chọn đa ngôn ngữ (Tiếng Việt, Tiếng Anh, Tiếng Trung, Tiếng Nhật, Tiếng Hàn...).
    *   Tinh chỉnh cao độ (Pitch - thay đổi tần số lấy mẫu) và tốc độ (Atempo) cho từng phân đoạn hoặc áp dụng hàng loạt.
    *   Quản lý danh sách người nói (Speakers) thông qua định dạng cấu hình `diarization.json`.
    *   Hỗ trợ nhập (Import) tệp văn bản thô hoặc tệp JSON chứa danh sách câu thoại để tạo âm thanh thử nghiệm.
    *   Xuất (Export) hàng loạt tệp âm thanh định dạng `.wav` đã được gán cấu hình tương ứng.

---

### 2. `s4_1_ui_markers.py` (Pro Canvas Editor & Timeline)
Hệ thống biên tập phụ đề nâng cao và tự động phát hiện vùng văn bản để tạo mặt nạ làm mờ (blur mask). Công cụ này tích hợp thư viện EasyOCR để tự động hóa quá trình định vị phụ đề cũ trên video.

*   **Chức năng chính:**
    *   **Trình phát Video & Timeline:** Xem trực quan luồng video kèm theo một thanh dòng thời gian (Timeline) đa rãnh hỗ trợ cắt phân đoạn (phím `Ctrl+B` hoặc chế độ `B`), di chuyển (`G`) và kéo giãn độ dài rãnh.
    *   **Tự động xóa phụ đề (De-subtitles):** Nhập dữ liệu thời gian (`transcribe.json`), chọn khu vực cần quét (Trên, Dưới, Giữa, Trái, Phải) và sử dụng EasyOCR để nhận diện vùng chữ, tự động tạo các khung chữ nhật bao quanh văn bản theo mốc thời gian để lưu thành tệp `blurs.json`.
    *   **Biên tập phụ đề (Subtitles):** Tạo, nhập (`data.json`) và chỉnh sửa các dòng phụ đề trực tiếp trên màn hình xem trước. Hỗ trợ đầy đủ các thuộc tính của định dạng phụ đề `.ass` như: Font chữ, cỡ chữ, màu sắc (Primary, Outline, Shadow, Background Box), căn lề, viền chữ, khoảng cách ký tự, góc quay và độ co giãn tỷ lệ (Scale).
    *   **Xuất bản phụ đề:** Hỗ trợ xuất tệp phụ đề tiêu chuẩn định dạng `.ass` hoặc tệp lưu trữ trung gian định dạng `.json`.

---

### 3. `ui_combine_audio.py` (FFmpeg Audio Editor & Mixer)
Trình biên tập và trộn âm thanh đa rãnh trực quan, cho phép người dùng sắp xếp các đoạn âm thanh khác nhau trên dòng thời gian và xử lý đầu ra thông qua FFmpeg.

*   **Chức năng chính:**
    *   **Giao diện kéo thả (Drag and Drop):** Hỗ trợ kéo thả trực tiếp các tệp âm thanh (`.mp3`, `.wav`, `.aac`, `.flac`, `.m4a`, `.ogg`) vào dòng thời gian.
    *   **Tương tác trực tiếp trên Timeline:** Di chuyển vị trí bắt đầu của clip giữa các rãnh khác nhau, cắt ngắn/kéo dài (trim) điểm bắt đầu hoặc điểm kết thúc của phân đoạn trực tiếp bằng chuột hoặc phím tắt (`Q` để cắt đầu, `E` để cắt đuôi tại vị trí con trỏ phát nhạc).
    *   **Cắt clip (Split):** Cắt đôi một clip âm thanh tại vị trí hiện tại của con trỏ phát nhạc bằng tổ hợp phím `Ctrl+B`.
    *   **Bộ lọc thuộc tính riêng lẻ:** Tinh chỉnh thời gian bắt đầu, cắt xén bên trong, thay đổi tốc độ phát (Atempo), cao độ (Pitch dịch chuyển bán âm - semitones) và âm lượng cho riêng từng clip.
    *   **Trình trộn âm (Mixer Render):** Xuất bản bản phối tổng hợp ra các định dạng phổ biến như MP3, WAV, FLAC, AAC, M4A bằng cách sử dụng bộ lọc `amix` của FFmpeg.

---

### 4. `ui_resize-video.py` (Batch Video Resizer)
Ứng dụng hỗ trợ thay đổi độ phân giải và tốc độ khung hình (FPS) của video hàng loạt, được tối ưu hóa hiệu suất thông qua công nghệ tăng tốc phần cứng card đồ họa NVIDIA (CUDA/NVENC).

*   **Chức năng chính:**
    *   **Quản lý danh sách hàng đợi:** Nhập nhiều video cùng lúc bằng tính năng kéo thả hoặc chọn tệp.
    *   **Xem trước tiện lợi:** Tích hợp trình phát video cơ bản để kiểm tra nội dung trước khi xuất.
    *   **Thiết lập thông số linh hoạt:** Tùy chỉnh độ rộng (W), chiều cao (H), FPS và tỷ lệ thu phóng (Scale Ratio) cho từng video một cách độc lập. Hệ thống tự động tính toán giữ nguyên tỷ lệ khung hình khi thay đổi kích thước.
    *   **Tăng tốc phần cứng (Hardware Acceleration):** Sử dụng các tham số tối ưu hóa của FFmpeg dành cho GPU NVIDIA như bộ lọc `scale_cuda` và bộ mã hóa `h264_nvenc` để rút ngắn thời gian xử lý video.

---

## Yêu cầu hệ thống và cài đặt

### 1. Yêu cầu phần mềm bên ngoài
Tất cả các công cụ này đều phụ thuộc vào bộ thư viện **FFmpeg** để xử lý tệp. Bạn cần tải xuống và cấu hình FFmpeg vào biến môi trường (Environment Variables) của hệ thống:
*   Đảm bảo lệnh `ffmpeg` và `ffprobe` có thể chạy được từ cửa sổ dòng lệnh (Terminal/Command Prompt).

### 2. Cài đặt các thư viện Python
Cài đặt các gói thư viện cần thiết bằng lệnh dưới đây:

```bash
pip install PyQt6 pydub gtts easyocr numpy Pillow
```

*Lưu ý:* 
*   Thư viện `easyocr` sẽ tự động tải các mô hình ngôn ngữ (như mô hình tiếng Trung, tiếng Anh hoặc tiếng Việt tùy thuộc vào cấu hình của bạn) trong lần chạy đầu tiên.
*   Đối với công cụ `ui_resize-video.py`, nếu muốn sử dụng tính năng tăng tốc CUDA, hệ thống của bạn cần trang bị GPU của NVIDIA và đã cài đặt đầy đủ CUDA Toolkit tương thích.

---

## Hướng dẫn sử dụng cơ bản

### Chạy các công cụ
Mỗi công cụ hoạt động độc lập dưới dạng một tập lệnh Python riêng lẻ. Bạn có thể khởi chạy bằng cách mở terminal tại thư mục chứa tệp tin và thực hiện lệnh:

```bash
# Khởi chạy công cụ thử nghiệm giọng nói
python s3_1_ui_G_test_audio.py

# Khởi chạy trình tạo vùng làm mờ và biên tập phụ đề
python s4_1_ui_markers.py

# Khởi chạy trình trộn âm thanh đa kênh
python ui_combine_audio.py

# Khởi chạy trình thay đổi kích thước video hàng loạt
python ui_resize-video.py
```

### Các phím tắt thông dụng trong trình biên tập phụ đề (`s4_1_ui_markers.py`)
*   `V`: Chuyển sang công cụ chọn/tương tác mặc định.
*   `G`: Chuyển sang công cụ di chuyển các điểm mốc đồ họa.
*   `B`: Chuyển sang công cụ cắt phân đoạn (Double-click trên timeline rãnh hộp chữ nhật để cắt tại điểm đó).
*   `Ctrl + B`: Cắt hộp chữ nhật đang chọn tại vị trí con trỏ phát thời gian hiện tại.
*   `Delete`: Xóa các phân đoạn chữ nhật hoặc dòng phụ đề đang được chọn.
*   `I`: Tạo một khung khóa (Keyframe) định vị tại vị trí con trỏ thời gian hiện tại.
*   `Shift + I`: Xóa khung khóa gần với vị trí con trỏ thời gian hiện tại.
*   `Space`: Tạm dừng hoặc tiếp tục phát video (khi con trỏ chuột nằm trong phân vùng trình phát hoặc dòng thời gian).
*   `Ctrl + Z` / `Ctrl + Shift + Z`: Hoàn tác (Undo) hoặc Làm lại (Redo) thao tác chỉnh sửa hình học.