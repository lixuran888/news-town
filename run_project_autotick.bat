@echo off
setlocal

REM Run project in foreground (visible console) so errors are shown directly
set ROOT=%~dp0
set SCRIPT=%ROOT%run_project.py
set PYEXE=C:\Users\Lenovo\anaconda3\envs\newstown\python.exe

"%PYEXE%" "%SCRIPT%" --port 8000 --origin base_the_ville_clean %*

echo. 
echo 进程已退出。如需查看上方报错信息，请按任意键关闭窗口...
pause >nul
endlocal

