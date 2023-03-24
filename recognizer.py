import requests
import json
import logging
from dataclasses import dataclass, field

# api
HOST = "http://2.56.240.213:4000"
API_LINK = HOST + "/api/v1"

def ping_host():
    r = requests.get(HOST)
    return r.status_code == 200


def get_shazam_data(music_bytes: bytes):
    r = requests.post(API_LINK, files={"b_data": music_bytes})
    if r.status_code == 200:
        return r.text
    else:
        raise Exception(f"API status code {r.status_code}")

@staticmethod
def recognize_API(music_bytes: bytes):
    try:
        shazam_data = get_shazam_data(music_bytes)
        song_data = json.loads(shazam_data)["data"]
        song = Song(song_data[1]["track"]["title"],
                    song_data[1]["track"]["subtitle"],
                    f"{song_data[1]['track']['title']} - {song_data[1]['track']['subtitle']}",
                    song_data[1]["track"]["share"].get("image"),
                    song_data[1]["track"]["url"])
        return song
    except Exception as e:
        logging.error(f"recognizer error {e}")
        return None

@dataclass
class Song:
    title: str
    author: str
    full_title: str
    thumbnail_url: str = field(default=None)
    shazam_url: str = field(default=None)

# this code was ripped off of https://github.com/NerdSmith/MusicRecognizer
