@echo off
setlocal
call "%~dp0py_runner.bat" "D:\91s_Vivy\.agents\skills\hoh-vivy-default\scripts\vivy_call.py" %*
exit /b %ERRORLEVEL%
