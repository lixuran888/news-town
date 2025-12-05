@echo off
setlocal

echo [1/3] 终止相关进程...
REM Stop Django and Reverie processes started by run_project.py using PowerShell process query
powershell -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { $_.CommandLine -match 'run_project.py' -or $_.CommandLine -match 'manage.py runserver' -or $_.CommandLine -match 'reverie\\backend_server\\reverie.py' } ^| ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }"

echo [2/3] 清理端口 8000 (Django)...
REM Kill any process using port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo [3/3] 清理端口 8080 (备用)...
REM Kill any process using port 8080
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo 完成！已终止进程并清理端口 8000/8080。
endlocal
