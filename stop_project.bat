@echo off
setlocal

REM Stop Django and Reverie processes started by run_project.py using PowerShell process query
powershell -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { $_.CommandLine -match 'run_project.py' -or $_.CommandLine -match 'manage.py runserver' -or $_.CommandLine -match 'reverie\\backend_server\\reverie.py' } ^| ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }"

echo 已尝试终止相关进程。
endlocal
