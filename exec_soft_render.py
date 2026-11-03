import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["SOFT_RENDER"] = "True"

from src.enties import agr
from src.utils import handle_input, txt


BASE_DIR = Path(__file__).resolve().parent
PIPELINE_FILE = BASE_DIR / "exec.py"
spec = importlib.util.spec_from_file_location("pipeline_exec", PIPELINE_FILE)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load pipeline helpers from {PIPELINE_FILE}")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

STAGES = (
    "s1_transcribe.py",
    "s2_translates.py",
    "s3_Google_speech.py",
    "s6_video_complex.py",
)


def get_mixed_audio(video: str, language: str) -> Path:
    media = Path(video).resolve()
    return media.parent / media.stem / f"{media.stem}_G.{language}_mixed.mp3"


def make_soft_render_config(video: str, language: str, path: Path) -> Path:
    mixed_audio = get_mixed_audio(video, language)
    if not mixed_audio.is_file() or mixed_audio.stat().st_size == 0:
        raise FileNotFoundError(f"Mixed audio not found: {mixed_audio}")

    config = json.loads(Path(pipeline.RENDER_CONFIG).read_text(encoding="utf-8"))
    config["base_audio"] = {"volume": 0.0}
    config["new_vocal"] = None
    config["new_audios"] = []
    config["audios"] = [
        {
            "volume": 1.0,
            "tempo": 1.0,
            "pitch": 1.0,
            "repeat": False,
            "source": {"path": str(mixed_audio)},
        }
    ]
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_stage_command(script: str, video: str) -> list[str]:
    if not getattr(sys, "frozen", False):
        return pipeline.build_cmd(script, video)
    executable = Path(sys.executable).resolve().parent / f"{Path(script).stem}.exe"
    command = [str(executable), "-i", video]
    for flag, value in pipeline.DEFAULT_DATA.get(script, []):
        command.extend([flag, str(value)])
    return command


def main() -> None:
    args = handle_input(agr(default=None, name_or_flags=("-i", "--input")))
    videos = pipeline.collect_video_paths(args.input)
    if not videos:
        txt.red("No valid video files selected or found.")
        raise SystemExit(1)

    total = len(videos) * len(STAGES)
    current = 0
    for video in videos:
        txt.yellow(f'Processing: "{video}"')
        for script in STAGES:
            current += 1
            if script == "s6_video_complex.py":
                language = pipeline.TAR_LANG
                media = Path(video).resolve()
                expected = [media.parent / f"{media.stem}_{language}_soft_render_final.mp4"]
            else:
                language = None
                expected = pipeline.get_expected_outputs(script, video)
            if pipeline.check_outputs_exist(expected):
                for output in expected:
                    txt.magenta(f'[PASS] "{output}"')
                continue

            command = build_stage_command(script, video)
            txt.cyan(f"[{current}/{total}] {script} (SOFT_RENDER=True)")
            if script == "s6_video_complex.py":
                with tempfile.TemporaryDirectory(prefix="soft-render-") as temp_dir:
                    config_path = make_soft_render_config(video, language, Path(temp_dir) / "render_config.json")
                    command.extend(["-o", str(expected[0])])
                    command[command.index("-c") + 1] = str(config_path)
                    exit_code = subprocess.run(command, cwd=BASE_DIR, env=os.environ.copy()).returncode
            else:
                exit_code = subprocess.run(command, cwd=BASE_DIR, env=os.environ.copy()).returncode
            if exit_code != 0:
                txt.red(f"{script} failed with exit code {exit_code}.")
                raise SystemExit(exit_code)
            if expected and not pipeline.check_outputs_exist(expected):
                txt.red(f"{script} completed without producing the expected output.")
                raise SystemExit(1)
            for output in expected:
                txt.green(f'[DONE] "{output}"')

    txt.cyan("Soft-render pipeline completed successfully.")


if __name__ == "__main__":
    main()