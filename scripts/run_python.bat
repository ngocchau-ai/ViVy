@echo off
REM [ISOLATED 26/09/2026] BAN NAY TRUNG BYTE VOI py_runner.bat (MD5 07-FE-BD).
REM Ban song la py_runner.bat — duoc vivy_call.bat, vivy_health_check.bat
REM va scripts/sync_2brain_dd.py goi. Redirect sang do de khong vo caller.
REM Giu lai lam tai lieu so sanh, khong xoa (Quy tac 4).
call "%~dp0py_runner.bat" %*
