@echo off
setlocal

REM Run project in foreground (visible console) so errors are shown directly
set ROOT=%~dp0
set SCRIPT=%ROOT%run_project.py
set PYEXE=C:\Users\Lenovo\anaconda3\envs\newstown\python.exe

REM Pre-launch: open browser tabs after a short delay in the background
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'; Start-Sleep -Seconds 1; Start-Process 'http://127.0.0.1:8000/simulator_home'"

"%PYEXE%" "%SCRIPT%" --port 8000 %*

echo. 
echo 进程已退出。如需查看上方报错信息，请按任意键关闭窗口...
pause >nul
endlocal
