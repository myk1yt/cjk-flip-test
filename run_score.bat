@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "%~dp0"

echo ================================================================================
echo  Zoo Code Custom Mode - CJK-Flip 1-Click Evaluation Runner
echo ================================================================================
echo.

set "PY_CMD="
where py >nul 2>nul && set "PY_CMD=py -3"
if "%PY_CMD%"=="" where python >nul 2>nul && set "PY_CMD=python"
if "%PY_CMD%"=="" where python3 >nul 2>nul && set "PY_CMD=python3"

rem Check standard Windows installation directories if not in PATH
if "%PY_CMD%"=="" (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%D\python.exe" set "PY_CMD=%%D\python.exe"
    )
)
if "%PY_CMD%"=="" (
    for /d %%D in ("%ProgramFiles%\Python3*") do (
        if exist "%%D\python.exe" set "PY_CMD=%%D\python.exe"
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python 3 was not found on your system PATH or standard folders.
    echo Please install Python 3.8+ and enable "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

set "TARGET_SCRIPT="
if exist "flip-test-pack\score_results.py" (
    set "TARGET_SCRIPT=flip-test-pack\score_results.py"
) else if exist "score_results.py" (
    set "TARGET_SCRIPT=score_results.py"
) else (
    echo [ERROR] score_results.py was not found.
    echo.
    pause
    exit /b 1
)

echo [INFO] Running evaluation with %PY_CMD%...
echo.
%PY_CMD% "%TARGET_SCRIPT%" %*
set "EXIT_CODE=%errorlevel%"

set "LAUNCH_TARGET="
if exist "report.html" set "LAUNCH_TARGET=report.html"
if "%LAUNCH_TARGET%"=="" if exist "flip-test-pack\report.html" set "LAUNCH_TARGET=flip-test-pack\report.html"

echo.
echo ================================================================================
if not "%LAUNCH_TARGET%"=="" (
    echo [INFO] Launching visual HTML dashboard: %LAUNCH_TARGET%
    start "" "%LAUNCH_TARGET%"
)
echo ================================================================================
echo.
pause
exit /b %EXIT_CODE%
