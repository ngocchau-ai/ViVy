@echo off
REM [ISOLATED 26/09/2026] BAN NAY TRUNG BYTE VOI py_runner.bat (MD5 07-FE-BD).
REM Ban song la py_runner.bat. Khong co script nao goi run_python.bat:
REM   vivy_call.bat / vivy_health_check.bat goi truc tiep py_runner.bat
REM   (call "%~dp0py_runner.bat"), khong di qua day. sync_2brain_dd.py
REM   chi TEN py_runner.bat trong noi dung DD, khong phai caller.
REM Redirect nay la lop phong thu de khong vo caller ngoai repo.
REM Giu lai lam tai lieu so sanh, khong xoa (Quy tac 4).
call "%~dp0py_runner.bat" %*
