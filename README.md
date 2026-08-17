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
<table>
  <tr>
    <td width="30%" valign="top">
      <a href="https://youtube.com/shorts/aYZv6VuAA9U" target="_blank">
        <img src="https://github.com/user-attachments/assets/5e4e8a44-1774-4a5a-a48b-965f63104cc7" height="300px" />
      </a>
    </td>
    <td width="70%" valign="top">
      <table>
        <tr><th>Name</th><th>Cmd</th></tr>
        <tr><td><b>Default</b></td><td><code>python s0_demucs.py</code></td></tr>
      </table>
      <table>
        <tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
        <tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/videos/test.mp4"</td></tr>
        <tr><td>output path</td><td>-o</td><td>--output</td><td>-o "D:/videos/test"</td></tr>
      </table>
      <pre><code>python s0_demucs.py -i "D:/test.mp4" #"D:/test.mp3"</code></pre>
    </td>
  </tr>
</table>

### Transcribe
<table>
	<tr>
		<td width="30%" valign="top">
			<video src="./assets/demo_s1_transcribe.mp4" width="100%" controls></video>
		</td>
		<td width="70%" valign="top">
			<table>
				<tr><th>Name</th><th>Cmd</th></tr>
				<tr><td><b>Default</b></td><td><code>python s1_transcribe.py</code></td></tr>
			</table>
			<table>
				<tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
				<tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/videos/test.mp4"</td></tr>
				<tr><td>output path</td><td>-o</td><td>--output</td><td>-o "D:/videos/test"</td></tr>
				<tr><td>beam size</td><td>-c-bs</td><td>--beam_size</td><td>-c-bs 5</td></tr>
				<tr><td>word timestamps</td><td>-c-wt</td><td>--word_timestamps</td><td>-c-wt True</td></tr>
				<tr><td>condition on previous text</td><td>-c-copt</td><td>--condition_on_previous_text</td><td>-c-copt False</td></tr>
				<tr><td>vad filter</td><td>-c-vf</td><td>--vad_filter</td><td>-c-vf True</td></tr>
			</table>
			<pre><code>python s1_transcribe.py -i "D:/test.mp4"</code></pre>
		</td>
	</tr>
</table>

### Translate text/subtitles
<table>
	<tr>
		<td width="30%" valign="top">
			<video src="./assets/demo_s2_translate.mp4" width="100%" controls></video>
		</td>
		<td width="70%" valign="top">
			<table>
				<tr><th>Name</th><th>Cmd</th></tr>
				<tr><td><b>Default</b></td><td><code>python s2_translate.py</code></td></tr>
			</table>
			<table>
				<tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
				<tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/data.json"</td></tr>
				<tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>or</i> -l "vi"</td></tr>
				<tr><td>srt generation</td><td>-s</td><td>--srt</td><td>-s True <i>or</i> -s False</td></tr>
			</table>
			<pre><code>python s2_translates.py -i "D:/test/test.json"</code></pre>
		</td>
	</tr>
</table>

### Text to Speech & Audio Mixing
<table>
	<tr>
		<td width="30%" valign="top">
			<video src="./assets/demo_s3_audio.mp4" width="100%" controls></video>
		</td>
		<td width="70%" valign="top">
			<table>
				<tr><th>Name</th><th>Cmd</th></tr>
				<tr><td><b>Default</b></td><td><code>python s3_audio.py</code></td></tr>
			</table>
			<table>
				<tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
				<tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/data.json"</td></tr>
				<tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>or</i> -l "vi"</td></tr>
				<tr><td>pitch</td><td>-p</td><td>--pitch</td><td>-p 1.39</td></tr>
				<tr><td>atempo</td><td>-a</td><td>--atempo</td><td>-a 1.25</td></tr>
				<tr><td>volume</td><td>-v</td><td>--volume</td><td>-v 2.0</td></tr>
			</table>
			<pre><code>python s3_audio.py -i "D:/test/test.vi.json"</code></pre>
		</td>
	</tr>
</table>

### Text to AI Speech (XTTS)
<table>
	<tr>
		<td width="30%" valign="top">
			<video src="./assets/demo_s3.1_AI_speechs.mp4" width="100%" controls></video>
		</td>
		<td width="70%" valign="top">
			<table>
				<tr><th>Name</th><th>Cmd</th></tr>
				<tr><td><b>Default</b></td><td><code>python s3.1_AI_speechs.py</code></td></tr>
			</table>
			<table>
				<tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
				<tr><td>input path / text</td><td>-i</td><td>--input</td><td>-i "D:/data.json" <i>or</i> -i "Xin chào bạn"</td></tr>
				<tr><td>output path</td><td>-o</td><td>--output</td><td>-o "./output.wav"</td></tr>
				<tr><td>template voice</td><td>-t</td><td>--temple</td><td>-t "D:/samples/voice.wav"</td></tr>
				<tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi" <i>or</i> -l "en"</td></tr>
			</table>
			<pre><code>python s3.1_AI_speechs.py -l "vi" -o "./test.wav" -t "assets/tmp_voices/Adam.mp3" -i "Xin chào, đây là giọng nói AI thử nghiệm."</code></pre>
		</td>
	</tr>
</table>

### Transcribe Audio & Length
<table>
	<tr>
		<td width="30%" valign="top">
			<video src="./assets/demo_s4_transcribe.mp4" width="100%" controls></video>
		</td>
		<td width="70%" valign="top">
			<table>
				<tr><th>Name</th><th>Cmd</th></tr>
				<tr><td><b>Default</b></td><td><code>python s4_transcribe.py</code></td></tr>
			</table>
			<table>
				<tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
				<tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/audio.mp3"</td></tr>
				<tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>or</i> -l "vi"</td></tr>
				<tr><td>words</td><td>-w</td><td>--words</td><td>-w 1 <i>or</i> -w 10</td></tr>
				<tr><td>beam size</td><td>-c-bs</td><td>--beam_size</td><td>-c-bs 5</td></tr>
				<tr><td>word timestamps</td><td>-c-wt</td><td>--word_timestamps</td><td>-c-wt True</td></tr>
				<tr><td>condition on previous text</td><td>-c-copt</td><td>--condition_on_previous_text</td><td>-c-copt False</td></tr>
				<tr><td>vad filter</td><td>-c-vf</td><td>--vad_filter</td><td>-c-vf True</td></tr>
			</table>
			<pre><code>python s3.2_srt.py -i "D:\test\test.vi.mp3" -w 1 -c-vf 0</code></pre>
		</td>
	</tr>
</table>

### Video Rendering & Complex Processing
<table>
	<tr>
		<td width="30%" valign="top">
			<video src="./assets/demo_s5_video_complex.mp4" width="100%" controls></video>
		</td>
		<td width="70%" valign="top">
			<table>
				<tr><th>Name</th><th>Cmd</th></tr>
				<tr><td><b>Default</b></td><td><code>python s5_video_complex.py</code></td></tr>
			</table>
			<table>
				<tr><th>&amp; Params</th><th>short</th><th>name</th><th>EX</th></tr>
				<tr><td>input path</td><td>-i</td><td>--input</td><td>-i "D:/videos" <i>or</i> -i "D:/videos/test.mp4"</td></tr>
				<tr><td>language</td><td>-l</td><td>--language</td><td>-l "vi,en" <i>or</i> -l "vi"</td></tr>
			</table>
			<pre><code>python D:\dev\py\video_h_complex.py -i "D:\test.mp4"</code></pre>
		</td>
	</tr>
</table>