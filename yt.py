from yt_dlp import YoutubeDL

# Global cache to avoid multiple yt-dlp calls per song
_audio_info_cache = {}

ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'skip_download': True,
    'audioquality': 1,
    'forceurl': True,
    'forcejson': True,
    'nocheckcertificate': True,
    'default_search': 'ytsearch1',
}

def get_audio_info(query):
    if query in _audio_info_cache:
        return _audio_info_cache[query]
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        result = info['entries'][0] if 'entries' in info else info
        _audio_info_cache[query] = result
        return result

def get_audio_url(query):
    return get_audio_info(query)['url']

def get_audio_title(query):
    return get_audio_info(query).get('title', 'Unknown Title')