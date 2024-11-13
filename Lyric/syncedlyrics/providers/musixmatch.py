"""Musixmatch LRC provider"""

from typing import Optional, List
import time
import json
import os
from .base import LRCProvider
from ..utils import get_best_match, format_time
from pprint import pprint

# Inspired from https://github.com/Marekkon5/onetagger/blob/0654131188c4df2b4b171ded7cdb927a4369746e/crates/onetagger-platforms/src/musixmatch.rs
# Huge part converted from Rust to Py by ChatGPT :)


class Musixmatch(LRCProvider):
    """Musixmatch provider class"""

    ROOT_URL = "https://apic-desktop.musixmatch.com/ws/1.1/"

    def __init__(self, lang: Optional[str] = None, enhanced: bool = False, use_musixmatch_best: bool = False, search_without_artist: bool = False) -> None:
        super().__init__()
        self.lang = lang
        self.enhanced = enhanced
        self.token = None
        self.use_musixmatch_best = use_musixmatch_best
        self.search_without_artist = search_without_artist

    def _get(self, action: str, query: List[tuple]):
        if action != "token.get" and self.token is None:
            self._get_token()
        query.append(("app_id", "web-desktop-app-v1.0"))
        if self.token is not None:
            query.append(("usertoken", self.token))
        t = str(int(time.time() * 1000))
        query.append(("t", t))
        url = self.ROOT_URL + action

        response = self.session.get(url, params=query)
        return response

    def _get_token(self):
        # Check if token is cached and not expired
        token_path = os.path.join(".syncedlyrics", "musixmatch_token.json")
        current_time = int(time.time())
        if os.path.exists(token_path):
            with open(token_path, "r") as token_file:
                cached_token_data = json.load(token_file)
            cached_token = cached_token_data.get("token")
            expiration_time = cached_token_data.get("expiration_time")
            if cached_token and expiration_time and current_time < expiration_time:
                self.token = cached_token
                return
        # Token not cached or expired, fetch a new token
        d = self._get("token.get", [("user_language", "en")]).json()
        if d["message"]["header"]["status_code"] == 401:
            time.sleep(10)
            return self._get_token()
        new_token = d["message"]["body"]["user_token"]
        expiration_time = current_time + 600  # 10 minutes expiration
        # Cache the new token
        self.token = new_token
        token_data = {"token": new_token, "expiration_time": expiration_time}
        os.makedirs(".syncedlyrics", exist_ok=True)
        with open(token_path, "w") as token_file:
            json.dump(token_data, token_file)

    def get_lrc_by_id(self, track_id: str) -> Optional[str]:
        r = self._get(
            "track.subtitle.get",
            [("track_id", track_id), ("subtitle_format", "lrc")],
        )
        if self.lang is not None:
            r_tr = self._get(
                "crowd.track.translations.get",
                [
                    ("track_id", track_id),
                    ("subtitle_format", "lrc"),
                    ("translation_fields_set", "minimal"),
                    ("selected_language", self.lang),
                ],
            )
            body_tr = r_tr.json()["message"]["body"]
        if not r.ok:
            return None
        body = r.json()["message"]["body"]
        if not body:
            return None
        lrc = body["subtitle"]["subtitle_body"]
        if self.lang is not None and body_tr:
            for i in body_tr["translations_list"]:
                org, tr = (
                    i["translation"]["subtitle_matched_line"],
                    i["translation"]["description"],
                )
                lrc = lrc.replace(org, org + "\n" + f"({tr})")
        return lrc

    def get_lrc_word_by_word(self, track_id: str) -> Optional[str]:
        r = self._get("track.richsync.get", [("track_id", track_id)])
        if r.ok and r.json()["message"]["header"]["status_code"] == 200:
            lrc_raw = r.json()["message"]["body"]["richsync"]["richsync_body"]
            lrc_raw = json.loads(lrc_raw)
            lrc = ""
            for i in lrc_raw:
                lrc += f"[{format_time(i['ts'])}] "
                for l in i["l"]:
                    t = format_time(float(i["ts"]) + float(l["o"]))
                    lrc += f"<{t}> {l['c']} "
                lrc += "\n"
            return lrc


    def get_lrc(self, r_search_term: str, searching_without_artist: bool = False) -> Optional[str]:
        search_term = r_search_term.replace(" -", "")

        print(f'[MUSIXMATCH] Searching: "{search_term}"')

        r = self._get(
            "macro.search",
            [
                ("q", search_term),
                ("page_size", "5"),
                ("page", "1"),
                ("s_track_rating", "desc"),
                ("quorum_factor", "1.0"),
            ],
        )
        body = r.json()["message"]["body"]

        if not body:
            if not self.search_without_artist or searching_without_artist: # Костыль мне лень функцию делать
                print('[MUSIXMATCH] Nothing found')
                return None

            print('[MUSIXMATCH] Nothing found, searching without artist')
            found = self.get_lrc(r_search_term.split('-')[0].strip(), searching_without_artist = True)
            if found: return found
            else: return None

        best_match = body["macro_result_list"]['best_match'] if self.use_musixmatch_best else None
        tracks = body["macro_result_list"]['track_list']
        cmp_key = lambda t: f"{t['track']['track_name']} {t['track']['artist_name']}"
        track = get_best_match(
            tracks, 
            search_term, 
            cmp_key
        )
        
        if not track and self.search_without_artist and not searching_without_artist:
            print('[MUSIXMATCH] Not found, searching without artist')
            found = self.get_lrc(r_search_term.split('-')[0].strip(), searching_without_artist = True) # тоже костыль, лень
            if found: return found

        if track:
            print(f"[MUSIXMATCH] Founded text for \"{track['track']['track_name']} - {track['track']['artist_name']}\"")
            track_id = track['track']["track_id"]

        elif best_match:
            print("[MUSIXMATCH] Not found, using musixmatch best match 💩")
            track_id = best_match['id']

        else:
            print("[MUSIXMATCH] Not found")
            return None
        
        if self.enhanced:
            return self.get_lrc_word_by_word(track_id)
        
        return self.get_lrc_by_id(track_id)
