@echo off

setlocal
chcp 65001

cls
echo Установка пакетов из requirements.txt
pip install -r requirements.txt
echo Установка FFMPEG. Введите Y если попросят.
ffdl install -U --add-path
echo Готово!
pause