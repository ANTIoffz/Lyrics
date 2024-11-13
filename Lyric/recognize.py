from shazamio import Shazam
import sounddevice as sd
from scipy.io import wavfile
import io
from config import Config
from pprint import pprint, pformat
import time
import json
import syncedlyrics
import os
import urllib.parse


class Recognizer:
    def __init__(self):
        self.shazam = Shazam()
        self.change_counter = 0
        self.last_data = None
        self.stop_counter = 0
        

    async def _convert_to_bytes(self, audio):
        bytes_wav = bytes()
        byte_io = io.BytesIO(bytes_wav)
        wavfile.write(byte_io, Config.RECORD_FREQUENCY, audio)
        result_bytes = byte_io.read()
        return result_bytes
        
    
    async def _record_audio(self):
        # if Config.RECORD_DEVICE:
        #     sd.default.channels = 2,0
        #     sd.default.device = Config.RECORD_DEVICE

        recorded_audio = sd.rec(
            int(Config.RECORD_SECONDS * Config.RECORD_FREQUENCY),
            samplerate=Config.RECORD_FREQUENCY,
            channels=2,
            device=Config.RECORD_DEVICE
        )
        sd.wait()

        return recorded_audio
        
    async def _add_counter(self, stop=False):
        if not stop:
            self.change_counter+=1
            print(f"[CHANGE] Change counter: {self.change_counter} / {Config.CHANGE_COUNTER}")
            if self.change_counter < Config.CHANGE_COUNTER:
                return False
        else:
            self.stop_counter+=1
            print(f"[CHANGE] Stop counter: {self.stop_counter} / {Config.STOP_COUNTER}")
            if self.stop_counter < Config.STOP_COUNTER:
                return False
        
            if not Config.DEBUG_DO_NOT_DELETE_DATA:
                if os.path.exists(Config.DATA_FILENAME):
                    with open(Config.DATA_FILENAME, 'w+', encoding='utf-8') as file:
                        file.write('{}')
        
        print("[CHANGE] Changing")
        self.change_counter = 0
        self.stop_counter = 0
        self.last_data = None
        return True
        
    

    async def _check(self, old_data, new_data):
        if not old_data:
            return True
        
        if new_data['track_id'] != old_data['track_id']:
            print(f"[CHANGE] NEW TRACK: {new_data['track_id']} : {old_data['track_id']}")
            return await self._add_counter()
        
        if abs((time.time() - new_data['start_time']) - (time.time() - old_data['start_time'])) >= Config.MAX_OFFSET_DIFFERENCE:
            print(f"[CHANGE] NEW OFFSET: {abs((time.time() - new_data['start_time']) - (time.time() - old_data['start_time']))}")
            return await self._add_counter()
        
        self.change_counter = 0
        return False
    

    async def _dump_data(self, data):
        with open(Config.DATA_FILENAME, 'w+', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        self.last_data = data

    # Searching
    async def search_songs(self):
        recorded_audio = await self._record_audio()
        recorded_bytes = await self._convert_to_bytes(recorded_audio)

        matches = await self.shazam.recognize(recorded_bytes)
        return matches
    

    async def search_text(self, title):
        print(f'[SEARCH] Searching text for {title}')
        text = syncedlyrics.search(
            title, 
            providers=Config.PROVIDERS, 
            use_musixmatch_best=Config.USE_MUSIXMATCH_BEST_IF_NOT_FOUND, 
            search_without_artist=Config.SEARCH_WITHOUT_ARTIST_IF_NOT_FOUND
        )
        print(f"[SEARCH] Searching with: {Config.PROVIDERS}")
        if text:
            pprint(text.split('\n')[:5])
        return text
    
    # Start
    async def start_recognize(self):
        start_time = time.time()
        matches = await self.search_songs()
        
        if not matches.get('matches', False):
            print("[SEARCH] Music not found")
            if Config.STOP_COUNTER:
                await self._add_counter(stop=True)
                return
            
            await self._add_counter()
            
        track_title = matches['track']['title']
        track_subtitle = matches['track']['subtitle']
        track_offset = matches['matches'][0]['offset']
        track_id = matches['matches'][0]['id']
        start_time -= track_offset + Config.OFFSET_FIX

        self.track_data = {
            'track_id': track_id,
            'track_title': track_title,
            'track_subtitle': track_subtitle,
            'start_time': start_time,
            'track_offset': track_offset,
            'not_exactly': False
        }

        print(f"[SEARCH] Recognized: {track_title} - {track_subtitle}")
        print(f"[SEARCH] Offset = {track_offset}")
        if_change = await self._check(self.last_data, self.track_data)

        if if_change:
            track_text = await self.search_text(f"{track_title} - {track_subtitle}") # - {track_subtitle}

            # try:
            #     track_text = await self.search_text(f"{track_title} - {track_subtitle}") # - {track_subtitle}
            # except TypeError as err:
            #     print(err)
            #     print("[SEARCH] Error, removing Musixmatch TOKEN")
            #     os.remove('.syncedlyrics/musixmatch_token.json')
            #     return
            
            self.track_data['track_text'] = track_text
            await self._dump_data(self.track_data)


    async def start(self):
        while True:
            print("[SEARCH] Recognizing...")
            await self.start_recognize()
            time.sleep(Config.RECOGNIZE_SLEEP)
