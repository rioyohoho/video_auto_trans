@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

:MENU
cls
echo ===================================================
echo             CHỌN CHƯƠNG TRÌNH CẦN BUILD EXE
echo      (Mở cửa sổ riêng - Cho phép chọn tiếp)
echo ===================================================
echo   [1]  exec_soft_render.py  (Soft Render Pipeline)
echo   [2]  exec.py               (Full Pipeline)
echo   [3]  menu.py               (Menu GUI)
echo   [4]  s0_demucs.py          (Demucs Separation)
echo   [5]  s1_transcribe.py      (Transcribe)
echo   [6]  s2_translates.py      (Translate Subtitles)
echo   [7]  s3_Google_speech.py   (Google Speech)
echo   [8]  s3_AI_speech.py       (AI Speech - XTTS)
echo   [9]  s4_srt.py             (Word-Level SRT)
echo   [10] s5_ocr_delogo.py      (OCR Delogo)
echo   [11] s5.1_ocr_delogo_gui.py (Delogo GUI)
echo   [12] s6_video_complex.py   (Render Video Complex)
echo ---------------------------------------------------
echo   [A]  BUILD TẤT CẢ (Mở đồng thời nhiều cửa sổ)
echo   [0]  Thoát (Exit)
echo ===================================================
echo.

set /p CHOICE="Nhập lựa chọn của bạn (0-12 hoặc A): "

if "%CHOICE%"=="0" exit /b
if /i "%CHOICE%"=="A" goto BUILD_ALL
if "%CHOICE%"=="1" call :LaunchBuild exec_soft_render.py & goto MENU
if "%CHOICE%"=="2" call :LaunchBuild exec.py & goto MENU
if "%CHOICE%"=="3" call :LaunchBuild menu.py & goto MENU
if "%CHOICE%"=="4" call :LaunchBuild s0_demucs.py & goto MENU
if "%CHOICE%"=="5" call :LaunchBuild s1_transcribe.py & goto MENU
if "%CHOICE%"=="6" call :LaunchBuild s2_translates.py & goto MENU
if "%CHOICE%"=="7" call :LaunchBuild s3_Google_speech.py & goto MENU
if "%CHOICE%"=="8" call :LaunchBuild s3_AI_speech.py & goto MENU
if "%CHOICE%"=="9" call :LaunchBuild s4_srt.py & goto MENU
if "%CHOICE%"=="10" call :LaunchBuild s5_ocr_delogo.py & goto MENU
if "%CHOICE%"=="11" call :LaunchBuild s5.1_ocr_delogo_gui.py & goto MENU
if "%CHOICE%"=="12" call :LaunchBuild s6_video_complex.py & goto MENU

echo.
echo Lựa chọn không hợp lệ! Vui lòng thử lại.
timeout /t 2 >nul
goto MENU

:BUILD_ALL
call :LaunchBuild exec_soft_render.py
call :LaunchBuild exec.py
call :LaunchBuild menu.py
call :LaunchBuild s0_demucs.py
call :LaunchBuild s1_transcribe.py
call :LaunchBuild s2_translates.py
call :LaunchBuild s3_Google_speech.py
call :LaunchBuild s3_AI_speech.py
call :LaunchBuild s4_srt.py
call :LaunchBuild s5_ocr_delogo.py
call :LaunchBuild s5.1_ocr_delogo_gui.py
call :LaunchBuild s6_video_complex.py
goto MENU

:LaunchBuild
set SCRIPT=%~1
for %%i in ("%SCRIPT%") do set NAME=%%~ni

set "EXTRA_ARGS="

if exist "%CD%\assets" (
    for %%f in ("%CD%\assets\*.json") do (
        set "EXTRA_ARGS=!EXTRA_ARGS! --add-data "%%f;assets""
    )
)

if "%SCRIPT%"=="exec_soft_render.py" (
    if exist "%CD%\exec.py" (
        set "EXTRA_ARGS=!EXTRA_ARGS! --add-data "%CD%\exec.py;.""
    )
)

:: Mở cửa sổ CMD mới độc lập chạy PyInstaller
start "Building %NAME%.exe" cmd /c "chcp 65001 >nul && echo --------------------------------------------------- && echo Đang đóng gói: %SCRIPT% --^> apps\%NAME%.exe && echo --------------------------------------------------- && python -m PyInstaller --noconfirm --clean --onefile --name "%NAME%" --distpath "%CD%\apps" --workpath "%CD%\build\pyinstaller\work\%NAME%" --specpath "%CD%\build\pyinstaller\spec" --paths "%CD%" %EXTRA_ARGS% "%CD%\%SCRIPT%" && if !errorlevel! neq 0 ( echo. && echo [LỖI NGHIÊM TRỌNG] Build %SCRIPT% thất bại! && pause ) else ( echo. && echo [THÀNH CÔNG] Đã tạo thành công apps\%NAME%.exe && timeout /t 3 >nul )"

goto :eof