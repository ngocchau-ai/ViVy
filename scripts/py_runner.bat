@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if exist "D:\91s_Vivy\.venv\Scripts\python.exe" (
    set "PY_EXE=D:\91s_Vivy\.venv\Scripts\python.exe"
) else if defined PYTHON_EXE (
    set "PY_EXE=%PYTHON_EXE%"
) else if exist "C:\Users\LENOVO\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PY_EXE=C:\Users\LENOVO\AppData\Local\Programs\Python\Python311\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" %*
exit /b %ERRORLEVEL%
