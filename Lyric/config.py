from abc import ABC
from typing import Final


class Config:
    DATA_FILENAME: Final = 'data.json'

    RECORD_FREQUENCY: Final = 48000
    RECORD_SECONDS: Final = 3

    MAX_OFFSET_DIFFERENCE: Final = 1
    CHANGE_COUNTER: Final = -1
    STOP_COUNTER: Final = 2
    OFFSET_FIX: Final = 0
    PROVIDERS = ["Deezer", "Lrclib", "Musixmatch"]

    PREVIOUS_LINES_COUNT: Final = 3
    NEXT_LINES_COUNT: Final = 3

    RECORD_DEVICE = 1
    RECOGNIZE_SLEEP = 1

    USE_MUSIXMATCH_BEST_IF_NOT_FOUND: Final = False
    SEARCH_WITHOUT_ARTIST_IF_NOT_FOUND: Final = True

    DELETE_DATA_ON_FINISH: Final = False
    DEBUG_DO_NOT_DELETE_DATA: Final = False
    DEBUG_LOG: Final = False
    AUTO_SHOW: Final = True
