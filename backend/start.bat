@echo off
setlocal
cd /d %~dp0

set PYTHON_PATH=python
where %PYTHON_PATH% >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] 未找到 python，请安装或修改 PYTHON_PATH
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" copy .env.example .env
)

echo [INFO] Competition API http://0.0.0.0:8000
%PYTHON_PATH% -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
