import threading
from recognize import Recognizer
from main import start
from config import Config
import asyncio
import os
import subprocess
import logging


def install_ffmpeg():
    os.system('pip install ffmpeg-downloader')
    process = subprocess.Popen('ffdl install -U --add-path', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=b'Y\n')

def check_ffmpeg():
    try:
        import ffmpeg_downloader as ffdl
        assert ffdl.installed()
    except:
        print("FFMPEG not found. Installing...")
        install_ffmpeg()



if __name__ in {"__main__", "__mp_main__"}:
    check_ffmpeg()

    if Config.DEBUG_LOG:
        logging.basicConfig(level = logging.DEBUG)

    recognizer = Recognizer()
    recognize_thread = threading.Thread(target=lambda: asyncio.run(recognizer.start()), daemon=True)
    recognize_thread.start()

    print("[THREADS] Started thread 'recognize'")
    print("[MAIN] Starting main function")
    start()

