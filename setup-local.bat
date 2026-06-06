@echo off
REM ============================================================
REM  Local Setup Script for Video Editing Automation (Windows)
REM ============================================================
echo.
echo ========================================
echo  Video Editing Automation - Local Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)
echo [OK] Python found

REM Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js found

REM Check ffmpeg
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] ffmpeg not found in PATH.
    echo.  Install from https://ffmpeg.org/download.html and add to PATH.
    echo.  Or use: winget install "FFmpeg (Essentials Build)"
    choice /M "Continue anyway"
)

REM Install Python dependencies
echo.
echo Installing Python dependencies...
pip install opencv-python numpy librosa moviepy
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

REM Install Node.js dependencies
echo.
echo Installing Node.js dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install Node.js packages.
    pause
    exit /b 1
)
echo [OK] Node.js dependencies installed

REM Create media folder on desktop
if not exist "%USERPROFILE%\Desktop\media" (
    mkdir "%USERPROFILE%\Desktop\media"
    echo [OK] Created desktop\media folder
) else (
    echo [OK] desktop\media folder exists
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo  NEXT STEPS:
echo  1. Place your .mp4/.mov/.jpg/.png files in:
echo     %USERPROFILE%\Desktop\media\
echo  2. Place your background music as audio.mp3 on:
echo     %USERPROFILE%\Desktop\audio.mp3
echo  3. Start the app: npm run dev
echo  4. Open http://localhost:3000
echo  5. Update paths in the form and click Generate
echo.
echo  Output video saves to your desktop - nothing stored online!
echo.
pause
