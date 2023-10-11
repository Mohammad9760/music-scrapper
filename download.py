import os
import re
import urllib.request  # for saving the song cover file
import requests
from bs4 import BeautifulSoup
from collections import Counter
from yt_dlp import YoutubeDL
import music_tag  # for adding meta data
from ytmusicapi import YTMusic  # for finding the song

DL_PATH = "./downloaded/"
FILE_EXT = '.webm'
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': DL_PATH + '%(id)s.%(ext)s',
}

# youtube music api instance
ytmusic = YTMusic()

def get_covert_art(song):
    """ downloads the cover art in full resolution"""
    try:
        # get the music cover from youtube
        cover = song["videoDetails"]["thumbnail"]["thumbnails"][0]
        url = cover.get('url')[:-15]

        # return cover art
        path_name = DL_PATH + "/" + re.sub('/', '', song["videoDetails"]["title"]) + " cover.png"
        urllib.request.urlretrieve(url, path_name)
    except urllib.request.HTTPError:
        return None, None
    with open(path_name, 'rb') as img_in:
        art_work = img_in.read()
    return art_work, path_name


def get_lyrics(video_id):
    "finds the songs lyrics from youtube"
    try:
        playlist = ytmusic.get_watch_playlist(str(video_id))
        lyrics = ytmusic.get_lyrics(playlist["lyrics"])
        return str(lyrics.get('lyrics'))
    except Exception: # don't try to catch the particular exception this is fine
        return "t.me/musicscrappybot"


def get_year_album(video_id):
    """returns songs release year and album info"""
    watch = ytmusic.get_watch_playlist(video_id)
    try:
        album = ytmusic.get_album(watch['tracks'][0]['album']['id'])
        return (str(album['year']),
                    str(album['title']))
    except KeyError:
        return None, None


def download_song(video_id):
    """ pass the videoId to download the video as mp3 """
    out_file = ''
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://music.youtube.com/watch?v=" + str(video_id), download=True)
        info_with_audio_extension = dict(info)
        out_file = DL_PATH + info_with_audio_extension['id'] + FILE_EXT

    # check for file size limit
    if os.path.getsize(str(out_file)) > 40000000:
        os.remove(out_file)
        return 'File Too Large'
    # convert with encoding
    name, _ = os.path.splitext(out_file)
    if os.path.exists(name + '.mp3'):
        # if a file already exists with the same name delete it
        os.remove(name + '.mp3')
    os.system('./ffmpeg -i "' + out_file + '" -vn "' + name + '.mp3"')
    new_file = name + '.mp3'
    if not os.path.isfile(new_file):
        raise FileNotFoundError
    os.remove(out_file)

    watch = ytmusic.get_watch_playlist(video_id)
    song = ytmusic.get_song(watch['tracks'][0].get('videoId'))
    file = music_tag.load_file(new_file)
    file['title'] = song['videoDetails']['title']
    file['artist'] = song['videoDetails']['author']
    file['genre'] = get_song_genre(song['videoDetails']['title'], song['videoDetails']['author'])
    print(get_song_genre(song['videoDetails']['title'], song['videoDetails']['author']))
    del file['artwork']
    file['year'], file['album'] = get_year_album(video_id)
    file['artwork'], cover_path = get_covert_art(song)
    if cover_path:
        os.remove(cover_path)
    file['lyrics'] = get_lyrics(video_id)
    file.save()
    return new_file

Genres = {
    'rock': 0,
    'pop': 0,
    'jazz': 0,
    'hip hop': 0,
    'country': 0,
    'classical': 0,
    'blues': 0,
    'metal': 0,
    'electronic': 0,
    'folk': 0,
    'reggae': 0,
    'latin': 0,
    'soul': 0,
    'punk': 0,
    'r&b': 0,
    'world music': 0,
    'new age': 0,
    'instrumental': 0,
    'rap': 0,
    'house': 0
}

def get_song_genre(song_name ,artist_name):
    """
    function to get the genre of the song from the web
    """
    # build the URL
    query = 'what genre is {} by {}'.format(song_name, artist_name)
    url = 'https://google.com/search?q=' + query.replace(" ", "+")
    # make the HTTP request and get the HTML content
    response = requests.get(url, timeout= 5000)
    content = response.content
    genres = Genres.copy()
    # parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")
    for genre in genres:
        genres[genre] = soup.get_text().lower().count(genre)
        # genres[genre] = len(soup.body.findAll(text=re.compile(genre)))
    print(genres)
    return max(genres, key=genres.get)
