import re
import asyncio
from ytmusicapi import YTMusic
import download

ytmusic = YTMusic()

def query(prompt, search_filter):
    """returns search results from youtube as a dict"""
    result_list = []
    search_results = ytmusic.search(prompt, search_filter)

    blocked_words = ['sound effect', 'asmr', 'ear licking', 'finger licking']
    words_re = re.compile("|".join(blocked_words), re.IGNORECASE)
    if len(search_results) == 0 or words_re.search(prompt):
        result_list.append(('Nothing Found!', ''))
        return result_list

    # match search_filter:
    #     case 'songs':
    #         for result in search_results:
    #             try:



    #                 if(words_re.search(result['artists']['name']) or words_re.search(result['title'])):
    #                     continue
    #                 result_list.append(('"{}" - {}'.format(result['title'], result['artists'][0]['name']) ,'dl_' + result['videoId']))

    #             except Exception as exception:
    #                 print(exception)
    #                 continue

    #     case 'albums':
    #         for result in search_results:
    #             try:
    #                 if result['resultType'] != 'album':
    #                     continue
    #                 result_list.append(('"{}" - {}'.format(result['title'], result['artists'][0]['name']), 'album_' + result['browseId']))

    #             except Exception as exception:
    #                 print(exception)
    #                 continue

    #     case 'artists':
    #         for result in search_results:
    #             try:
    #                 if result['resultType'] != 'artist':
    #                     continue
    #                 result_list.append((result['artist'], 'artist_' + result['browseId']))

    #             except Exception as exception:
    #                 print(exception)
    #                 continue

    try:
        match search_filter:
            case 'songs':
                result_list = [('"{}" - {}'.format(result['title'], result['artists'][0]['name']) ,'dl_' + result['videoId']) for result in search_results if not ((words_re.search(result['artists']['name']) or words_re.search(result['title'])))]

            case 'albums':
                result_list = [('"{}" - {}'.format(result['title'], result['artists'][0]['name']), 'album_' + result['browseId']) for result in search_results if result['resultType'] == 'album']

            case 'artists':
                result_list = [(result['artist'], 'artist_' + result['browseId']) for result in search_results if result['resultType'] == 'artist']
    except Exception as exception:
        print(exception)

    return result_list


async def get_song(data: str) -> str:
    """downloads the song asyncly"""
    return await asyncio.to_thread(download.download_song, (data[3:]))


def get_album(browse_id):
    """returns a dict containing songs in the album"""
    browse_id = browse_id[6:]
    album = ytmusic.get_album(browse_id)

    caption = '<b>{}</b>'.format(album['title'])
    if 'description' in album:
        caption = caption + \
            ('\n <i>{}</i> ...'.format(album['description'][:500]))

    songs = []
    for track in album['tracks']:
        # if the type is a music video we search again filtering for songs
        if track['videoType'] == 'MUSIC_VIDEO_TYPE_OMV':
            result = ytmusic.search(track['title'] + ' by ' + track['artists'][0]['name'], 'songs', limit=1)
            track = result[0]
        songs.append((str(track['title']), 'dl_' + track['videoId']))

    return album['thumbnails'][0].get('url')[:-15], songs, caption


def get_artist(browse_id, info='profile'):
    """returns either the artist's photo and about info
    or the albums and singles"""
    artist = ytmusic.get_artist(browse_id)
    if info == 'profile':
        about = (artist['description'] != None)
        picture = artist['thumbnails'][0].get('url')
        name = artist['name']
        return about, picture, name
    elif info == 'description':
        return artist[info], []
    elif info == 'albums' or 'singles':
        result_list = []
        try:
            result_list = [('"{}"'.format(result['title']) ,'album_' + result['browseId']) for result in artist[info]['results']]
        except KeyError:
            return 'No {} Found for {}'.format(info, artist['name']), result_list
        except Exception as exception:
            print(exception)
        return '{}\'s {}: '.format(artist['name'], info), result_list
