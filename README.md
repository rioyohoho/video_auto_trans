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
Default --language **[.env:LANGS](.env#20)** *or* **[src/configuration.py:LANGS](src/configuration.py#28)**
<div style="display: flex; gap: 20px; align-items: flex-start;">
<div style="flex: 0 0 280px; aspect-ratio: 9/18;">
<iframe src="https://drive.google.com/file/d/1jzyeufpEGw1OZX12H1qod7t-K5Vfu9wl/view?usp=sharing" width="100%" height="100%" allow="autoplay" frameborder="0" style="border-radius: 8px;"></iframe>
</div>
<div style="flex: 1;">

### Demucs audios

| Name | Cmd |
| :--- | :--- |
| **Default** | `python s0_demucs.py` |

| **& Params** | short | name | EX |
| :--- | :--- | :--- | :--- |
| input path | -i | --input | -i "D:/videos" *or* -i "D:/videos/test.mp4" |
| output path | -o | --output | -o "D:/videos/test" |

```bash
python s0_demucs.py -i "D:/test.mp4" #"D:/test.mp3"
```

</div>
</div>
### Transcribe
| Name | Cmd  |
| :--- | :--- |
| **Default** | `python s1_transcribe.py` |

| **& Params** | short | name | EX |
| :--- | :--- | :--- | :--- |
| input path | -i | --input | -i "D:/videos" *or* -i "D:/videos/test.mp4" |
| output path | -o | --output | -o "D:/videos/test" |
| beam size | -c-bs | --beam_size | -c-bs 5 |
| word timestamps | -c-wt | --word_timestamps | -c-wt True |
| condition on previous text | -c-copt | --condition_on_previous_text | -c-copt False |
| vad filter | -c-vf | --vad_filter | -c-vf True |
```
python s1_transcribe.py -i "D:/test.mp4"
```
### Translate text/subtitles
| Name | Cmd  |
| :--- | :--- |
| **Default** | `python s2_translate.py` |

| **& Params** | short | name | EX |
| :--- | :--- | :--- | :--- |
| input path | -i | --input | -i "D:/videos" *or* -i "D:/data.json" |
| language | -l | --language | -l "vi,en" *or* -l "vi" |
| srt generation | -s | --srt | -s True *or* -s False |
```
python s2_translates.py -i "D:/test/test.json"
```
### Text to Speech & Audio Mixing
| Name | Cmd  |
| :--- | :--- |
| **Default** | `python s3_audio.py` |

| **& Params** | short | name | EX |
| :--- | :--- | :--- | :--- |
| input path | -i | --input | -i "D:/videos" *or* -i "D:/data.json" |
| language | -l | --language | -l "vi,en" *or* -l "vi" |
| pitch | -p | --pitch | -p 1.39 |
| atempo | -a | --atempo | -a 1.25 |
| volume | -v | --volume | -v 2.0 |
```
python s3_audio.py -i "D:/test/test.vi.json"
```
### Text to AI Speech (XTTS)
| Name | Cmd  |
| :--- | :--- |
| **Default** | `python s3.1_AI_speechs.py` |

| **& Params** | short | name | EX |
| :--- | :--- | :--- | :--- |
| input path / text | -i | --input | -i "D:/data.json" *or* -i "Xin chào bạn" |
| output path | -o | --output | -o "./output.wav" |
| template voice | -t | --temple | -t "D:/samples/voice.wav" |
| language | -l | --language | -l "vi" *or* -l "en" |
```bash
python s3.1_AI_speechs.py -l "vi" -o "./test.wav" -t "assets/tmp_voices/Adam.mp3" -i "Xin chào, đây là giọng nói AI thử nghiệm." 
```
### Transcribe Audio & Length
| Name | Cmd  |
| :--- | :--- |
| **Default** | `python s4_transcribe.py` |

| **& Params** | short | name | EX |
| :--- | :--- | :--- | :--- |
| input path | -i | --input | -i "D:/videos" *or* -i "D:/audio.mp3" |
| language | -l | --language | -l "vi,en" *or* -l "vi" |
| words | -w | --words | -w 1 *or* -w 10 |
| beam size | -c-bs | --beam_size | -c-bs 5 |
| word timestamps | -c-wt | --word_timestamps | -c-wt True |
| condition on previous text | -c-copt | --condition_on_previous_text | -c-copt False |
| vad filter | -c-vf | --vad_filter | -c-vf True |
```
python s3.2_srt.py -i "D:\test\test.vi.mp3" -w 1 -c-vf 0
```
### Video Rendering & Complex Processing
| Name | Cmd |
| --- | --- |
| **Default** | `python s5_video_complex.py` |

| **& Params** | short | name | EX |
| --- | --- | --- | --- |
| input path | -i | --input | -i "D:/videos" *or* -i "D:/videos/test.mp4" |
| language | -l | --language | -l "vi,en" *or* -l "vi" |
```
python D:\dev\py\video_h_complex.py -i "D:\test.mp4"
```
