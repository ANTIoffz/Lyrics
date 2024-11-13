import json
import datetime
import time
import os
import asyncio
import pylrc
from config import Config
from nicegui import ui, app
import random

class Main:
    def __init__(self):
        self.track_text = None
        self.output_lyric_text = ''

    async def _read_config(self):
        if os.path.exists(Config.DATA_FILENAME):
            with open(Config.DATA_FILENAME, 'r') as file:
                try:
                    return json.load(file)
                except json.decoder.JSONDecodeError:
                    return None
        return None


    async def _read_text(self):
        self.track_data = await self._read_config()
        if not self.track_data or not self.track_data.get('track_text', False):
            return None
        return pylrc.parse(self.track_data['track_text'])


    async def _check_for_new(self):
        return await self._read_config() != self.track_data


    @staticmethod
    async def _clear_cmd():
        os.system('cls')


    async def _draw_lyric(self, id):
        self.output_lyric_text = ""
        for number in reversed(list(range(Config.PREVIOUS_LINES_COUNT))):
            if id - number - 1 < 0:
                self.output_lyric_text += "<p class='previous_line hidden_line'>...</p>"
                continue

            try: 
                assert self.track_text[id-number-1].text.strip() != ''
                self.output_lyric_text += f"<p class='previous_line'>{self.track_text[id-number-1].text.strip()}</p>"
            except: 
                self.output_lyric_text += "<p class='previous_line hidden_line'>...</p>"
        

        if not self.track_text[id].text.strip() == '':
            self.output_lyric_text += f"<p class='current_line'>{self.track_text[id].text.strip()}</p>"
        else:
            self.output_lyric_text += f"<p class='current_line hidden_line'>...</p>"


        for number in range(Config.NEXT_LINES_COUNT):
            try:
                assert self.track_text[id+number+1].text.strip() != ''
                self.output_lyric_text += f"<p class='next_line'>{self.track_text[id+number+1].text.strip()}</p>"
            except: 
                self.output_lyric_text += "<p class='next_line hidden_line'>...</p>"

        
        self.output_lyric_text += ''
        self.lyric_html.set_content(self.output_lyric_text)


    async def _remove_data(self):
        if os.path.exists(Config.DATA_FILENAME):
            try:
                os.remove(Config.DATA_FILENAME)
            except PermissionError:
                with open(Config.DATA_FILENAME, 'w', encoding='utf-8') as file:
                    file.write('{}')

    async def _set_title(self, text):
        self.title_html.set_content(f"<p class='title'>{text}</p>")


    async def _check_text(self):
        self.track_text = await self._read_text()
        
        if self.track_data:
            await self._set_title(f"{self.track_data['track_title']} - {self.track_data['track_subtitle']}")

        if not self.track_text:
            self.lyric_html.set_content("<p>Не найдено :(</p>" if random.randint(0, 1000) != 1000 else "<p>Недостаточно маны...</p>")
            return

        await self._draw_lyric(0)
        for id, line in enumerate(self.track_text):
            while True: 
                if await self._check_for_new(): return
                if (time.time() - self.track_data['start_time']) >= line.time:
                    await self._draw_lyric(id)
                    break
                await asyncio.sleep(0.1)

        if Config.DELETE_DATA_ON_FINISH and not Config.DEBUG_DO_NOT_DELETE_DATA:
            await self._remove_data()
    
    async def _start_loop(self):
        while True:
            self.title_html.set_content('')
            self.lyric_html.set_content('')

            await self._check_text()
            await asyncio.sleep(0.1)

    async def start(self):
        app.add_static_files('/static', 'static')
        ui.add_head_html('<link rel="stylesheet" type="text/css" href="/static/styles.css">')

        with ui.element('div').classes('title-box') :
            self.title_html = ui.html()


        with ui.element('div').classes('outer') :
            with ui.element('div').classes('lyric-box') :
                self.lyric_html = ui.html()
                ui.element('div').classes('vignette')

        await self._start_loop()


def start():
    main = Main()
    app.on_startup(main.start)
    ui.run(reload=False, dark=True, show=Config.AUTO_SHOW)
