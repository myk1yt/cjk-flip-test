@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
pushd "%~dp0"

echo ================================================================================
echo  Zoo Code Custom Mode - CJK-Flip 1-클릭 채점 실행기 (한국어 모드)
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
        echo [ERROR] score_results.py 파일을 찾을 수 없습니다.
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
    echo [ERROR] 시스템 PATH 또는 표준 디렉터리에서 Python 3을 찾을 수 없습니다.
    echo Python 3.8 이상을 설치하고 "Add python.exe to PATH" 옵션을 활성화하십시오.
    echo.
    if "%NESTED%"=="1" popd
    popd
    pause
    exit /b 1
)

echo [INFO] %PY_CMD% (한국어 모드)로 채점을 실행합니다...
echo.
%PY_CMD% score_results.py --lang ko %*
set "EXIT_CODE=%errorlevel%"

if "%NESTED%"=="1" popd
popd

echo.
echo ================================================================================
if exist "%REPORT_PATH%" (
    echo [INFO] 시각화 대시보드를 브라우저에서 실행합니다: %REPORT_PATH%
    start "" "%REPORT_PATH%"
)
echo ================================================================================
echo.
pause
exit /b %EXIT_CODE%
