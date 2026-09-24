@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
pushd "%~dp0"

echo ================================================================================
echo  Zoo Code Custom Mode - CJK-Flip Multi-Run Evaluation Runner (--runs)
echo ================================================================================
echo.

rem Always run the scorer from flip-test-pack so every output lands next to the pack
set "NESTED=0"
set "REPORT_PATH=%~dp0report.html"
if not exist "score_results.py" (
    if exist "flip-test-pack\score_results.py" (
        pushd "flip-test-pack"
        set "NESTED=1"
        set "REPORT_PATH=%~dp0flip-test-pack\report.html"
    ) else (
        echo [ERROR] score_results.py was not found.
        echo.
        popd
        pause
        exit /b 1
    )
)

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
    if "%NESTED%"=="1" popd
    popd
    pause
    exit /b 1
)

echo [INFO] Running multi-run evaluation (--runs) with %PY_CMD%...
echo.
%PY_CMD% score_results.py --runs %*
set "EXIT_CODE=%errorlevel%"

if "%NESTED%"=="1" popd
popd

echo.
echo ================================================================================
if exist "%REPORT_PATH%" (
    echo [INFO] Launching visual HTML dashboard: %REPORT_PATH%
    start "" "%REPORT_PATH%"
)
echo ================================================================================
echo.
pause
exit /b %EXIT_CODE%
