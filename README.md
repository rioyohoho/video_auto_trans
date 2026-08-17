# video_auto_trans
This project utilizes AI models to develop various functionalities including audio, text-to-speech, speech-to-text, and translation.


## Requirements
 - Python +3.10
### 1. Update pip & wheel
```
pip install --upgrade pip setuptools wheel
```
### 2. Install libraries
```
pip install pydub
pip install faster-whisper
pip install gTTS
pip install google-genai, deep_translator

pip install pyannote.audio==3.3.2 --no-deps #REPAIR onnxruntime for CUDA
pip install praat-parselmouth

pip install easyocr                             
pip install python-dotenv colorama, tabulate
pip install omegaconf semver speechbrain tensorboardx "click>=8.4.2"
```

## Use Torch: CPU
```
pip install "audio-separator"
py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-cache-dir
```
## Use Torch(cuda): GPU
```
pip install "audio-separator[gpu]"
py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall --no-cache-dir
```
`REPAIR`
```
py -m pip uninstall onnxruntime-gpu onnxruntime -y
py -m pip install onnxruntime-gpu==1.19.0
```

## Examples
__[configuration](src/configuration.py)__ -
__[enviroments](.env)__ <br>
Default --input folder **[.env:PATH_DIR](.env#1)** *or* **[src/configuration.py:P_DIR](src/configuration.py#9)** <br>
Default --language **[.env:LANGS](.env#24)** *or* **[src/configuration.py:LANGS](src/configuration.py#33)**

### Demucs audios
<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td style="width: 300px; min-width: 300px; vertical-align: top;">
            <a href="https://youtube.com/shorts/aYZv6VuAA9U"><img src="https://github.com/user-attachments/assets/4802c163-bd40-4556-868c-9d5a9069a7d6" height="300px" style="display: block;"></a>
        </td>
        <td style="vertical-align: top; padding-left: 15px;">
            <table style="width: 100%; margin-bottom: 10px;"><tr><th>Name</th><th>Cmd</th></tr><tr><td><b>Default</b></td><td><code>python s0_demucs.py</code></td></tr></table>
            <table style="width: 100%; margin-bottom: 10px;"><tr><th>& Params</th><th>short</th><th>name</th><th>EX</th></tr><tr><td>input</td><td>-i</td><td>--input</td><td>-i "D:/videos"</td></tr><tr><td>output</td><td>-o</td><td>--output</td><td>-o "D:/videos/test"</td></tr></table>
            <pre style="white-space: pre-wrap; word-break: break-all; background: #f6f8fa; padding: 10px; border-radius: 6px;"><code>python s0_demucs.py -i "D:/test.mp4"</code></pre>
        </td>
    </tr>
</table>

### Transcribe
<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td style="width: 300px; min-width: 300px; vertical-align: top;">
            <a href="https://youtube.com/shorts/UN9BrWDKwx4"><img src="https://github.com/user-attachments/assets/5dbf008a-d6a7-46d9-b26a-a6c8f33715de" height="300px" style="display: block;"></a>
        </td>
        <td style="vertical-align: top; padding-left: 15px;">
            <table style="width: 100%; margin-bottom: 10px;"><tr><th>Name</th><th>Cmd</th></tr><tr><td><b>Default</b></td><td><code>python s1_transcribe.py</code></td></tr></table>
            <table style="width: 100%; margin-bottom: 10px;"><tr><th>& Params</th><th>short</th><th>name</th><th>EX</th></tr><tr><td>input</td><td>-i</td><td>--input</td><td>-i "D:/videos"</td></tr><tr><td>beam</td><td>-c-bs</td><td>--beam_size</td><td>-c-bs 5</td></tr><tr><td>vad</td><td>-c-vf</td><td>--vad_filter</td><td>-c-vf True</td></tr></table>
            <pre style="white-space: pre-wrap; word-break: break-all; background: #f6f8fa; padding: 10px; border-radius: 6px;"><code>python s1_transcribe.py -i "D:/test.mp4"</code></pre>
        </td>
    </tr>
</table>

### Translate text/subtitles
<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td style="width: 300px; min-width: 300px; vertical-align: top;">
            <a href="https://youtube.com/shorts/REFQ3Kc4JwI"><img src="https://github.com/user-attachments/assets/1adf5781-6236-4c71-b241-5bcc99bbad72" height="300px" style="display: block;"></a>
        </td>
        <td style="vertical-align: top; padding-left: 15px;">
            <table style="width: 100%; margin-bottom: 10px;"><tr><th>Name</th><th>Cmd</th></tr><tr><td><b>Default</b></td><td><code>python s2_translate.py</code></td></tr></table>
            <table style="width: 100%; margin-bottom: 10px;"><tr><th>& Params</th><th>short</th><th>name</th><th>EX</th></tr><tr><td>input</td><td>-i</td><td>--input</td><td>-i "D:/data.json"</td></tr><tr><td>lang</td><td>-l</td><td>--language</td><td>-l "vi"</td></tr></table>
            <pre style="white-space: pre-wrap; word-break: break-all; background: #f6f8fa; padding: 10px; border-radius: 6px;"><code>python s2_translates.py -i "D:/test/test.json"</code></pre>
        </td>
    </tr>
</table>

### Text to AI Speech (XTTS)
<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td style="width: 300px; min-width: 300px; vertical-align: top;">
            <a href="https://youtube.com/shorts/ezabDkk0pxs">
                <img src="https://github.com/user-attachments/assets/04fde322-4991-4ba7-af98-b4aa21e88498" height="300px" style="display: block;" />
            </a>
        </td>
        <td style="vertical-align: top; padding-left: 15px;">
            <table style="width: 100%; margin-bottom: 10px;">
                <tr><th>Name</th><th>Cmd</th></tr>
                <tr><td><b>Default</b></td><td><code>python s3.1_AI_speechs.py</code></td></tr>
            </table>
            <table style="width: 100%; margin-bottom: 10px;">
                <tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
                <tr><td>input path / text</td><td>-i</td><td>--input</td><td>-i "D:/data.json" <i>or</i> -i "Xin chào bạn"</td></tr>
                <tr><td>output path</td><td>-o</td><td>--output</td><td>-o "./output.wav"</td></tr>
                <tr><td>template voice</td><td>-t</td><td>--temple</td><td>-t "D:/samples/voice.wav"</td></tr>
                <tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi" <i>or</i> -l "en"</td></tr>
            </table>
            <pre style="white-space: pre-wrap; word-break: break-all; background: #f6f8fa; padding: 10px; border-radius: 6px;"><code>python s3.1_AI_speechs.py -l "vi" -o "./test.wav" -t "assets/tmp_voices/Adam.mp3" -i "Xin chào, đây là giọng nói AI thử nghiệm."</code></pre>
        </td>
    </tr>
</table>

### Transcribe & Generate SRT by word count
<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td style="width: 300px; min-width: 300px; vertical-align: top;">
            <a href="https://youtube.com/shorts/YeSD_WHbpSg">
                <img src="https://github.com/user-attachments/assets/c44706bd-4c47-481f-81e7-1859644e8763" height="300px" style="display: block;" />
            </a>
        </td>
        <td style="vertical-align: top; padding-left: 15px;">
            <table style="width: 100%; margin-bottom: 10px;">
                <tr><th>Name</th><th>Cmd</th></tr>
                <tr><td><b>Default</b></td><td><code>python s4_transcribe.py</code></td></tr>
            </table>
            <table style="width: 100%; margin-bottom: 10px;">
                <tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
                <tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/audio.mp3"</td></tr>
                <tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>or</i> -l "vi"</td></tr>
                <tr><td>words</td><td>-w</td><td>--words</td><td>-w 1 <i>or</i> -w 10</td></tr>
                <tr><td>beam size</td><td>-c-bs</td><td>--beam_size</td><td>-c-bs 5</td></tr>
                <tr><td>word timestamps</td><td>-c-wt</td><td>--word_timestamps</td><td>-c-wt True</td></tr>
                <tr><td>condition on previous text</td><td>-c-copt</td><td>--condition_on_previous_text</td><td>-c-copt False</td></tr>
                <tr><td>vad filter</td><td>-c-vf</td><td>--vad_filter</td><td>-c-vf True</td></tr>
            </table>
            <pre style="white-space: pre-wrap; word-break: break-all; background: #f6f8fa; padding: 10px; border-radius: 6px;"><code>python s3.2_srt.py -i "D:\test\test.vi.mp3" -w 1 -c-vf 0</code></pre>
        </td>
    </tr>
</table>

### Video Rendering & Complex Processing
<table style="table-layout: fixed; width: 100%; border: none;">
    <tr>
        <td style="width: 300px; min-width: 300px; vertical-align: top;">
            <video src="./assets/demo_s5_video_complex.mp4" width="100%" controls style="display: block;"></video>
        </td>
        <td style="vertical-align: top; padding-left: 15px;">
            <table style="width: 100%; margin-bottom: 10px;">
                <tr><th>Name</th><th>Cmd</th></tr>
                <tr><td><b>Default</b></td><td><code>python s5_video_complex.py</code></td></tr>
            </table>
            <table style="width: 100%; margin-bottom: 10px;">
                <tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
                <tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/videos/test.mp4"</td></tr>
                <tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>or</i> -l "vi"</td></tr>
            </table>
            <pre style="white-space: pre-wrap; word-break: break-all; background: #f6f8fa; padding: 10px; border-radius: 6px;"><code>python D:\dev\py\video_h_complex.py -i "D:\test.mp4"</code></pre>
        </td>
    </tr>
</table>