@echo off
setlocal

echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Проверка и установка зависимостей...

pip show fastapi >nul 2>&1
IF ERRORLEVEL 1 (
    echo FastAPI не найден. Устанавливаю...
    pip install fastapi
) ELSE (
    echo FastAPI уже установлен.
)

pip show uvicorn >nul 2>&1
IF ERRORLEVEL 1 (
    echo Uvicorn не найден. Устанавливаю...
    pip install uvicorn
) ELSE (
    echo Uvicorn уже установлен.
)

echo Запуск FastAPI-сервера...
start http://localhost:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
endlocal
