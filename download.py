import os
import urllib.request  # for saving the song cover file
#from pytube import YouTube
from yt_dlp import YoutubeDL
import music_tag  # for adding meta data
from ytmusicapi import YTMusic  # for finding the song

DL_PATH = "./downloaded/"
FILE_EXT = '.webm'
ydl_opts = {
    'format': 'bestaudio',
    'outtmpl': DL_PATH + '%(title)s.%(ext)s',
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
        path_name = DL_PATH + "/" + song["videoDetails"]["title"] + " cover.png"
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
    except Exception: # no lyrics found
        return "music scrapper bot"


def get_year_album(video_id):
    """returns songs release year and album info"""
    watch = ytmusic.get_watch_playlist(video_id)
    try:
        return (str(watch['tracks'][0].get('year')),
                str(watch['tracks'][0]['album'].get('name')))
    except KeyError:
        return None, None


def download_song(video_id):
    """ pass the videoId to download the video as mp3 """
    #video = YouTube("https://music.youtube.com/watch?v=" + str(video_id))
    #audio = video.streams.filter(only_audio=True).first()
    #out_file = audio.download(output_path=DL_PATH)
    out_file = ''
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://music.youtube.com/watch?v=" + str(video_id), download=True)
        info_with_audio_extension = dict(info)
        out_file = DL_PATH + info_with_audio_extension['title'] + FILE_EXT

    # check for file size limit
    if os.path.getsize(str(out_file)) > 40000000:
        os.remove(out_file)
        return 'File Too Large'
    # convert with encoding
    name, _ = os.path.splitext(out_file)
    if os.path.exists(name + '.mp3'):
        os.remove(name + '.mp3')
        # if a file already exists with the same name delete it
    os.system('./ffmpeg -i "' + out_file + '" -vn "' + name + '.mp3"')
    new_file = name + '.mp3'
    if not os.path.isfile(new_file):
        raise FileNotFoundError
    os.remove(out_file)

    watch = ytmusic.get_watch_playlist(video_id)
    song = ytmusic.get_song(watch['tracks'][0].get('videoId'))
    path = new_file
    file = music_tag.load_file(path)
    file['title'] = song['videoDetails']['title']
    file['artist'] = song['videoDetails']['author']
    del file['artwork']
    file['year'], file['album'] = get_year_album(video_id)
    file['artwork'], cover_path = get_covert_art(song)
    if cover_path:
        os.remove(cover_path)
    file['lyrics'] = get_lyrics(video_id)
    file.save()
    return path
