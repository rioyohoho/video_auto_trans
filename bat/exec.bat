@echo off
chcp 65001 > nul

:: Find system Python path
for /f "delims=" %%i in ('where python') do (
    set "PYTHON_PATH=%%i"
    goto :found
)

:found
if "%PYTHON_PATH%"=="" (
    echo [ERROR] Python was not found on your system! Please install Python.
    pause
    exit /b
)

:: Get the project root directory (one level up from this 'bat' folder)
for %%A in ("%~dp0..") do set "PROJECT_ROOT=%%~fA"

set PYTHONPATH=%PROJECT_ROOT%

:: Run the Python menu script
"%PYTHON_PATH%" "%PROJECT_ROOT%\menu.py" %*

exit /b