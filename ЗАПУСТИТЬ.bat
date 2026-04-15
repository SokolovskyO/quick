@echo off
title Текстовый помощник

echo ============================================
echo   Текстовый помощник с Claude AI
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Скачайте Python с https://python.org/downloads/
    echo При установке поставьте галку "Add Python to PATH"
    pause
    exit /b 1
)

:: Install dependencies if needed
echo Проверяю зависимости...
pip show anthropic >nul 2>&1
if errorlevel 1 (
    echo Устанавливаю библиотеки (один раз)...
    pip install -r requirements.txt
    echo.
)

echo Запускаю помощник...
echo.
echo  Горячая клавиша: Ctrl + Shift + A
echo  (выделите текст в любом приложении, затем нажмите)
echo.
echo  Иконка появится в трее (правый нижний угол)
echo  Для настройки API-ключа: клик по иконке -> Настройки
echo.

python text_assistant.py

pause
