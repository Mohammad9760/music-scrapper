import re
import asyncio
from ytmusicapi import YTMusic
import download

ytmusic = YTMusic()

def query(prompt, search_filter):
    """returns search results from youtube as a dict"""
    result_dict = {}
    search_results = ytmusic.search(prompt, search_filter)

    blocked_words = ['sound effect', 'asmr', 'ear licking', 'finger licking']
    words_re = re.compile("|".join(blocked_words), re.IGNORECASE)
    if len(search_results) == 0 or words_re.search(prompt):
        result_dict['No Results Found!'] = '...'
        return result_dict

    match search_filter:
        case 'songs':
            for result in search_results:
                try:
                    song = ytmusic.get_song(result['videoId'])
                    if words_re.search(song['videoDetails']['author']) or words_re.search(song['videoDetails']['title']):
                        continue
                    result_dict['"{}" - {}'.format(song['videoDetails']['title'], song['videoDetails']
                                                   ['author'])] = 'dl_' + song['videoDetails']['videoId']
                except Exception as exception:
                    print(exception)
                    continue

        case 'albums':
            for result in search_results:
                try:
                    album = result
                    if result['type'] == 'Single':
                        continue
                    result_dict['"{}" - {}'.format(album['title'], album['artists'][0].get(
                        'name'))] = 'album_' + result['browseId']
                except Exception as exception:
                    print(exception)
                    continue

        case 'artists':
            for result in search_results:
                print(result)
                try:
                    if not result['resultType'] == 'artist':
                        continue
                    result_dict[result['artist']] = 'artist_' + \
                        result['browseId']
                except Exception as exception:
                    print(exception)
                    continue

    return result_dict


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

    #print(album['audioPlaylistId'])
    songs = {}
    for track in album['tracks']:
        songs[track['title']] = 'dl_' + track['videoId']
    
    return album['thumbnails'][0].get('url')[:-15], songs, caption


def get_artist(browse_id, info='profile'):
    """returns either the artist's photo and about info
    or the albums and singles"""
    artist = ytmusic.get_artist(browse_id)
    if info == 'profile':
        about = artist['description']
        picture = artist['thumbnails'][2].get('url')
        return about, picture
    elif info == 'description':
        return artist[info], []
    elif info == 'albums' or 'singles':
        result_dict = {}
        try:
            for result in artist[info]['results']:
                try:
                    result_dict['"{}"'.format(
                        result['title'])] = 'album_' + result['browseId']
                except Exception:
                    continue
        except KeyError:
            return 'No {} Found for {}'.format(info, artist['name']), result_dict
        return '{}\'s {}: '.format(artist['name'], info), result_dict
