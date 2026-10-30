@echo off
setlocal EnableExtensions
title Video Auto Translation Setup

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

set "PYTHON_HOME=%LOCALAPPDATA%\Programs\Python\Python31210"
set "FFMPEG_BIN=%LOCALAPPDATA%\VideoAutoTrans\ffmpeg\bin"
set "DOWNLOAD_DIR=%TEMP%\video_auto_trans_setup_%RANDOM%_%RANDOM%"
set "PYTHON_INSTALLER=%DOWNLOAD_DIR%\python-3.12.10-amd64.exe"
set "FFMPEG_ZIP=%DOWNLOAD_DIR%\ffmpeg.zip"

if not exist "%PROJECT_DIR%\requirements.txt" goto RequirementsMissing

echo.
echo [1/3] Checking Python...
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto PythonReady
)

py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    goto PythonReady
)

if exist "%PYTHON_HOME%\python.exe" (
    set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
    goto PythonReady
)

:InstallPython
mkdir "%DOWNLOAD_DIR%" 2>nul
echo Downloading Python 3.12.10...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 goto DownloadFailed

echo Installing Python...
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 Include_pip=1 Include_launcher=1 Include_test=0 PrependPath=1 TargetDir="%PYTHON_HOME%"
if errorlevel 1 goto PythonInstallFailed
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
if not exist "%PYTHON_EXE%" goto PythonInstallFailed

:PythonReady
"%PYTHON_EXE%" -m ensurepip --upgrade >nul 2>&1
"%PYTHON_EXE%" -m pip install --upgrade pip >nul 2>&1

echo.
echo [2/3] Checking FFmpeg...
ffmpeg -version >nul 2>&1
if not errorlevel 1 goto StepRequirements

if exist "%FFMPEG_BIN%\ffmpeg.exe" (
    set "PATH=%FFMPEG_BIN%;%PATH%"
    goto StepRequirements
)

mkdir "%DOWNLOAD_DIR%" 2>nul
echo Downloading FFmpeg...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%FFMPEG_ZIP%'; Expand-Archive -LiteralPath '%FFMPEG_ZIP%' -DestinationPath '%DOWNLOAD_DIR%\ffmpeg' -Force; $exe=Get-ChildItem -LiteralPath '%DOWNLOAD_DIR%\ffmpeg' -Filter ffmpeg.exe -Recurse | Select-Object -First 1; if(-not $exe){throw 'ffmpeg.exe was not found'}; New-Item -ItemType Directory -Force -Path '%FFMPEG_BIN%' | Out-Null; Copy-Item -Path (Join-Path $exe.DirectoryName '*') -Destination '%FFMPEG_BIN%' -Recurse -Force"
if errorlevel 1 goto FfmpegFailed
if not exist "%FFMPEG_BIN%\ffmpeg.exe" goto FfmpegFailed

set "PATH=%FFMPEG_BIN%;%PATH%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ffmpeg='%FFMPEG_BIN%'; $old=[Environment]::GetEnvironmentVariable('Path','User'); $parts=@($old -split ';' | Where-Object {$_}); if($parts -notcontains $ffmpeg){[Environment]::SetEnvironmentVariable('Path',(($parts+@($ffmpeg)) -join ';'),'User')}" >nul 2>&1

ffmpeg -version >nul 2>&1
if errorlevel 1 goto FfmpegFailed

:StepRequirements
echo.
echo [3/3] Installing project requirements...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto RequirementsInstallFailed

echo.
echo Setup completed.
echo Project: %PROJECT_DIR%
echo Python: %PYTHON_EXE%
echo.
choice /C YN /N /M "Run exec.py now? [Y/N] "
if errorlevel 2 goto SetupDone
set "VIDEO_INPUT="
set /p "VIDEO_INPUT=Enter a video file or folder path (without surrounding quotes): "
if not defined VIDEO_INPUT goto NoInput
"%PYTHON_EXE%" exec.py -i "%VIDEO_INPUT%"
goto SetupDone

:DownloadFailed
echo Failed to download the Python installer. Check your internet connection.
goto SetupFailed

:PythonInstallFailed
echo Python installation failed.
goto SetupFailed

:FfmpegFailed
echo FFmpeg download or setup failed.
goto SetupFailed

:RequirementsMissing
echo File requirements.txt not found in %PROJECT_DIR%
goto SetupFailed

:RequirementsInstallFailed
echo Installing requirements.txt failed.
goto SetupFailed

:NoInput
echo No input path was entered. Setup is complete; exec.py was not started.
goto SetupDone

:SetupFailed
if exist "%DOWNLOAD_DIR%" powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath '%DOWNLOAD_DIR%' -Recurse -Force -ErrorAction SilentlyContinue"
echo.
echo Setup stopped. Review the message above and try again.
pause
goto :eof

:SetupDone
if exist "%DOWNLOAD_DIR%" powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath '%DOWNLOAD_DIR%' -Recurse -Force -ErrorAction SilentlyContinue"
echo.
echo Done.
pause
endlocal