@echo off

setlocal enabledelayedexpansion

set PYTHON3=python

set SCRIPT_DIR=%~dp0
set ACTIVATE=%SCRIPT_DIR%.venv\Scripts\activate.bat
set REQUIREMENTS=%SCRIPT_DIR%src\requirements.txt
set SCRIPT=%SCRIPT_DIR%src\nicocc.py

if not exist "%ACTIVATE%" (
  where "%PYTHON3%" >nul 2>&1
  if not "%ERRORLEVEL%" == "0" (
    echo nicocc requires Python 3.4 or higher
    goto ABORT
  )
  "%PYTHON3%" -c "import sys; sys.exit(0) if sys.version_info[0] == 3 and sys.version_info[1] > 3 else sys.exit(1)" >nul
  if "!ERRORLEVEL!" == "0" (
    call :VENV
  ) else (
    echo nicocc requires Python 3.4 or higher
    goto ABORT
  )
)

if not exist "%ACTIVATE%" call :VENV

call "%ACTIVATE%" >nul 2>&1

pip install -r "%REQUIREMENTS%" >nul 2>&1

if "%~1" == "" (
  python "%SCRIPT%"
) else if "%~2" == "" (
  python "%SCRIPT%" "%~1"
) else if "%~3" == "" (
  python "%SCRIPT%" "%~1" "%~2"
) else if "%~4" == "" (
  python "%SCRIPT%" "%~1" "%~2" "%~3"
) else if "%~5" == "" (
  python "%SCRIPT%" "%~1" "%~2" "%~3" "%~4"
) else if "%~6" == "" (
  python "%SCRIPT%" "%~1" "%~2" "%~3" "%~4" "%~5"
) else if "%~7" == "" (
  python "%SCRIPT%" "%~1" "%~2" "%~3" "%~4" "%~5" "%~6"
) else if "%~8" == "" (
  python "%SCRIPT%" "%~1" "%~2" "%~3" "%~4" "%~5" "%~6" "%~7"
) else if "%~9" == "" (
  python "%SCRIPT%" "%~1" "%~2" "%~3" "%~4" "%~5" "%~6" "%~7" "%~8"
) else (
  python "%SCRIPT%" "%~1" "%~2" "%~3" "%~4" "%~5" "%~6" "%~7" "%~8" "%~9"
)

goto EXIT

:VENV
pushd %SCRIPT_DIR%
"%PYTHON3%" -m venv .venv >nul 2>&1
if not "%ERRORLEVEL%" == "0" (
  echo failed to create virtual environment >&2
  goto ABORT
)
popd
exit /b

:ABORT
endlocal
exit /b 1

:EXIT
endlocal
exit /b 0
