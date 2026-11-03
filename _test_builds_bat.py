import subprocess
from pathlib import Path


result = subprocess.run(
    ["cmd.exe", "/c", "builds.bat"],
    cwd=Path(__file__).resolve().parent,
    input="6\r\n\r\n0\r\n",
    text=True,
    capture_output=True,
)
print("EXIT:", result.returncode)
print(result.stdout[-12000:])
print(result.stderr[-3000:])
raise SystemExit(result.returncode)
