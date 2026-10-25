@echo off
setlocal EnableExtensions
 title Video Auto Translation Setup

set "PROJECT_PARENT=%~dp0"
if "%PROJECT_PARENT:~-1%"=="\" set "PROJECT_PARENT=%PROJECT_PARENT:~0,-1%"
set "TRANS_DIR=%PROJECT_PARENT%\trans"
set "PYTHON_HOME=%LOCALAPPDATA%\Programs\Python\Python31210"
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
set "FFMPEG_BIN=%LOCALAPPDATA%\VideoAutoTrans\ffmpeg\bin"
set "DOWNLOAD_DIR=%TEMP%\video_auto_trans_setup_%RANDOM%_%RANDOM%"
set "PYTHON_INSTALLER=%DOWNLOAD_DIR%\python-3.12.10-amd64.exe"
set "FFMPEG_ZIP=%DOWNLOAD_DIR%\ffmpeg.zip"
set "PROJECT_ZIP=%DOWNLOAD_DIR%\project.zip"
set "PROJECT_STAGE=%DOWNLOAD_DIR%\project"

if exist "%TRANS_DIR%" goto ExistingProject
mkdir "%DOWNLOAD_DIR%" 2>nul
if errorlevel 1 goto SetupFailed

echo.
echo [1/4] Checking Python 3.12.10...
if not exist "%PYTHON_EXE%" goto InstallPython
"%PYTHON_EXE%" -c "import sys; raise SystemExit(sys.version_info[:3] != (3,12,10))" >nul 2>&1
if not errorlevel 1 goto PythonReady

:InstallPython
echo Downloading Python 3.12.10...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 goto DownloadFailed

echo Installing Python and pip...
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 Include_pip=1 Include_launcher=0 Include_test=0 PrependPath=0 TargetDir="%PYTHON_HOME%"
if errorlevel 1 goto PythonInstallFailed
if not exist "%PYTHON_EXE%" goto PythonInstallFailed

:PythonReady
"%PYTHON_EXE%" -m ensurepip --upgrade
if errorlevel 1 goto PipFailed
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto PipFailed

echo.
echo [2/4] Installing FFmpeg...
if exist "%FFMPEG_BIN%\ffmpeg.exe" goto FfmpegReady
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%FFMPEG_ZIP%'; Expand-Archive -LiteralPath '%FFMPEG_ZIP%' -DestinationPath '%DOWNLOAD_DIR%\ffmpeg' -Force; $exe=Get-ChildItem -LiteralPath '%DOWNLOAD_DIR%\ffmpeg' -Filter ffmpeg.exe -Recurse | Select-Object -First 1; if(-not $exe){throw 'ffmpeg.exe was not found in the archive'}; New-Item -ItemType Directory -Force -Path '%FFMPEG_BIN%' | Out-Null; Copy-Item -Path (Join-Path $exe.DirectoryName '*') -Destination '%FFMPEG_BIN%' -Recurse -Force"
if errorlevel 1 goto FfmpegFailed
if not exist "%FFMPEG_BIN%\ffmpeg.exe" goto FfmpegFailed

:FfmpegReady
set "PATH=%FFMPEG_BIN%;%PATH%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ffmpeg='%FFMPEG_BIN%'; $old=[Environment]::GetEnvironmentVariable('Path','User'); $parts=@($old -split ';' | Where-Object {$_}); if($parts -notcontains $ffmpeg){[Environment]::SetEnvironmentVariable('Path',(($parts+@($ffmpeg)) -join ';'),'User')}"
if errorlevel 1 echo Warning: could not update the user PATH. FFmpeg is available in this setup window.

ffmpeg -version >nul 2>&1
if errorlevel 1 goto FfmpegFailed

echo.
echo [3/4] Downloading project ZIP (Git and WinRAR are not required)...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/rioyohoho/video_auto_trans/archive/refs/heads/master.zip' -OutFile '%PROJECT_ZIP%'; Expand-Archive -LiteralPath '%PROJECT_ZIP%' -DestinationPath '%PROJECT_STAGE%' -Force; $src=Get-ChildItem -LiteralPath '%PROJECT_STAGE%' -Directory | Select-Object -First 1; if(-not $src){throw 'Project folder was not found in the ZIP'}; Move-Item -LiteralPath $src.FullName -Destination '%TRANS_DIR%'"
if errorlevel 1 goto ProjectDownloadFailed
if not exist "%TRANS_DIR%\requirements.txt" goto RequirementsMissing

cd /d "%TRANS_DIR%"
if errorlevel 1 goto ProjectDownloadFailed

echo.
echo [4/4] Installing project requirements...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto RequirementsInstallFailed

echo.
echo Setup completed.
echo Project: %TRANS_DIR%
echo Python: %PYTHON_EXE%
echo FFmpeg: %FFMPEG_BIN%
echo.
choice /C YN /N /M "Run exec.py now? [Y/N] "
if errorlevel 2 goto SetupDone
set "VIDEO_INPUT="
set /p "VIDEO_INPUT=Enter a video file or folder path (without surrounding quotes): "
if not defined VIDEO_INPUT goto NoInput
"%PYTHON_EXE%" exec.py -i "%VIDEO_INPUT%"
goto SetupDone

:ExistingProject
echo The target folder already exists: %TRANS_DIR%
echo Move or rename it before running setup again. Nothing was overwritten.
goto SetupFailed

:DownloadFailed
echo Failed to download the Python installer. Check your internet connection.
goto SetupFailed

:PythonInstallFailed
echo Python 3.12.10 installation failed.
goto SetupFailed

:PipFailed
echo Failed to install or upgrade pip.
goto SetupFailed

:FfmpegFailed
echo FFmpeg download or setup failed.
goto SetupFailed

:ProjectDownloadFailed
echo Failed to download or extract the project ZIP.
goto SetupFailed

:RequirementsMissing
echo The downloaded project does not contain requirements.txt.
goto SetupFailed

:RequirementsInstallFailed
echo Installing requirements.txt failed.
goto SetupFailed

:NoInput
echo No input path was entered. Setup is complete; exec.py was not started.
goto SetupDone

:SetupFailed
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath '%DOWNLOAD_DIR%' -Recurse -Force -ErrorAction SilentlyContinue"
echo.
echo Setup stopped. Review the message above and try again.
pause
goto :eof

:SetupDone
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath '%DOWNLOAD_DIR%' -Recurse -Force -ErrorAction SilentlyContinue"
echo.
echo Done.
pause
endlocal
