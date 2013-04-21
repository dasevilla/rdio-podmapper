GRACENOTE_CLIENT_ID = "REPLACE_ME"
GRACENOTE_CLIENT_TAG = "REPLACE_ME"
GRACENOTE_LICENCE_PATH = "licence.txt"

ECHO_NEST_API_KEY = 'REPLACE_ME'
RDIO_API_TOKEN = 'REPLACE_ME'

"""Podcast episode to download, assumes it's an MP3"""
SRC_MP3 = 'http://podcastdownload.npr.org/anon.npr-podcasts/podcast/510019/88710305/npr_88710305.mp3'

# NPR: All Songs Considered
# PODCAST_URL = 'http://www.npr.org/rss/podcast.php?id=510019'
# KEXP: Music that matters
# PODCAST_URL = 'http://feeds.kexp.org/kexp/musicthatmatters'
# Coverville
# PODCAST_URL = 'http://feeds.feedburner.com/coverville'
# THe Sound Opinions
# PODCAST_URL = 'http://feeds.feedburner.com/TheSoundOpinionsPodcast'


"""Sample size in seconds to split the episode into"""
WAVE_SAMPLE_SIZE = 10  # in seconds

"""Only include a track if it is matched this many times in the episode"""
FILTER_COUNT = 1

"""Which catalog to map the identified tracks to"""
ECHO_NEST_BUCKET = 'id:rdio-US'

"""Number of seconds to wait between checking a catalog ticket status"""
ECHO_NEST_SLEEP = 1

"""Passed to requests.Response.iter_content()"""
DOWNLOAD_CHUNK_SIZE = 1024

RDIO_API_URL = 'https://www.rdio.com/api/1/'
