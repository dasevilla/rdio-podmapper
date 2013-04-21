import collections
import glob
import httplib
import logging
import os
import os.path
import shutil
import subprocess
import tempfile
import time
import wave

from pyechonest import config as echo_nest_config, catalog as echo_nest_catalog
from requests.auth import AuthBase
import requests

import config


echo_nest_config.ECHO_NEST_API_KEY = config.ECHO_NEST_API_KEY


class BearerAuth(AuthBase):
    """Adds a HTTP Bearer token to the given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer %s' % self.token
        return r


def download_podcast(src_url, dst_dir):
    """Download the MP3 file at `src_url`"""

    logger = logging.getLogger('downloader')

    r = requests.get(src_url, stream=True)
    r.raise_for_status()

    fp, dst_path = tempfile.mkstemp(prefix='episode-', suffix='.mp3', dir=dst_dir)
    os.close(fp)

    logger.info('Saving podcast to %s', dst_path)

    with open(dst_path, 'wb') as fp:
        for chunk in r.iter_content(config.DOWNLOAD_CHUNK_SIZE):
            fp.write(chunk)

    return dst_path


def convert_podcast(src_path, dst_dir):
    """Convert the MP3 found at ``src_path`` to a WAV file.

    Assumes the ``lame`` encoder can be found in $PATH."""

    logger = logging.getLogger('converter')

    root, ext = os.path.splitext(os.path.basename(src_path))
    dst_path = os.path.join(dst_dir, '%s.wav' % root)

    logger.info('Saving WAV file to %s', dst_path)

    return_code = subprocess.call([
        'lame', '--decode',
        '--mp3input', src_path,
        dst_path
    ])

    if return_code != 0:
        raise Exception('Decoder returned non-zero status code %s' % return_code)
    else:
        return dst_path


def split_wave_file(src_path, dst_dir):
    """Split the WAV file found at ``src_path`` into multiple WAV files."""

    logger = logging.getLogger('spliter')

    src_path_root, ext = os.path.splitext(os.path.basename(src_path))
    slice_base_name = '%s-slice' % src_path_root

    orig_track = wave.open(src_path, 'r')
    frame_rate = orig_track.getframerate()  # number of frames per second
    num_chanels = orig_track.getnchannels()
    sample_width = orig_track.getsampwidth()
    num_frames = orig_track.getnframes()
    total_length = num_frames / frame_rate

    logger.info('Splitting %s into multiple WAV files', src_path)
    logger.info('sample width %s', sample_width)
    logger.info('number channels %s', num_chanels)
    logger.info('frame rate %s', frame_rate)
    logger.info('number frames %s', num_frames)
    logger.info('total_length %s', total_length)

    start_position = float(0)
    while start_position < total_length:
        end_position = float(start_position + config.WAVE_SAMPLE_SIZE)

        if end_position > total_length:
            end_position = total_length

        logger.debug('start_position %s', start_position)
        logger.debug('end_position %s', end_position)

        orig_track.setpos(start_position * frame_rate)
        chunk_length = int((end_position - start_position) * frame_rate)
        logger.debug('chunk_length %s', chunk_length)
        chunk_data = orig_track.readframes(chunk_length)

        track_slice_path = os.path.join(dst_dir, '%s-%05d_%05d.wav' % (
            slice_base_name, start_position, end_position))

        track_slice = wave.open(track_slice_path, 'w')
        track_slice.setnchannels(num_chanels)
        track_slice.setsampwidth(sample_width)
        track_slice.setframerate(frame_rate)
        track_slice.writeframes(chunk_data)
        track_slice.close()

        logger.debug('tell %s', (orig_track.tell() / frame_rate))
        start_position = end_position

    orig_track.close()


def fingerprint_file(src_path):
    """Fingerprints the WAV file found at ``src_path``."""

    logger = logging.getLogger('fingerprint')
    matched_track = None

    output = subprocess.check_output([
        'gnfingerprint',
        config.GRACENOTE_CLIENT_ID,
        config.GRACENOTE_CLIENT_TAG,
        config.GRACENOTE_LICENCE_PATH,
        src_path,
    ], stderr=subprocess.STDOUT)

    if 'No tracks found for the input' in output:
        logger.info('No tracks found for the input %s', src_path)
    elif 'Item not found' in output:
        logger.info('Item not found %s', src_path)
    else:
        lines = output.split('\n')
        try:
            matched_track = (
                lines[1].split(':')[1].strip(),  # artist
                lines[2].split(':')[1].strip(),  # album
                lines[3].split(':')[1].strip(),  # track
            )
            logger.info('Identified %s as %s', src_path, ' - '.join(matched_track))
        except IndexError:
            logger.error('IndexError %s', output)

    return matched_track


def fingerprint_directory(src_dir):
    found_tracks = []
    for slice_path in glob.glob(os.path.join(src_dir, '*.wav')):
        found_track = fingerprint_file(slice_path)
        if found_track is not None:
            found_tracks.append(found_track)
    return found_tracks


def trim_tracks(found_tracks):
    """Only include results of they appear more than once"""
    results = [record for (record, count) in collections.Counter(found_tracks).most_common() if count > config.FILTER_COUNT]
    for record in results:
        print ' - '.join(record)
    return results


def update_catalog(catalog_name, tracks):
    """Adds the ``tracks`` to the Echo Nest catalog named ``catalog_name``."""

    logger = logging.getLogger('catalog-updater')

    catalog = echo_nest_catalog.Catalog(catalog_name, type='song')

    items = []
    for artist, album, title in tracks:
        items.append({
            'action': 'update',
            'item': {
                'item_id': '%s%s' % (title, artist),  # TODO: Better hash
                'song_name': title,
                'artist_name': artist,
            }
        })

    catalog_ticket = catalog.update(items)
    logger.info('Updated catalog named "%s" and got ticket "%s"', catalog_name,
                catalog_ticket)

    return catalog_ticket


def check_catalog_status(catalog_name, catalog_ticket):
    """Polls catalog ticket and blocks until it's finished."""
    logger = logging.getLogger('catalog-check')

    catalog = echo_nest_catalog.Catalog(catalog_name, type='song')

    completed = False
    while not completed:
        time.sleep(config.ECHO_NEST_SLEEP)
        catalog_status = catalog.status(catalog_ticket)
        completed = catalog_status['ticket_status'] == 'complete'
        logger.info('Catalog %s, ticket %s, status %s', catalog_name,
                    catalog_ticket, catalog_status['ticket_status'])


def dump_catalog(catalog_name):
    """Songs can be: Unknown, Identified, Found"""

    catalog = echo_nest_catalog.Catalog(catalog_name, type='song')

    found_rdio_tracks = []
    items = catalog.get_item_dicts(buckets=[config.ECHO_NEST_BUCKET, 'tracks'])
    for item in items:
        if 'artist_name' in item:
            print item['artist_name'], '-', item['song_name']

            rdio_track_keys = [track['foreign_id'].split(':')[2] for track in item['tracks']]
            if len(item['tracks']):
                print '\t', 'Found'
                print '\t', ', '.join(rdio_track_keys)
                found_rdio_tracks.append(rdio_track_keys[0])
            else:
                print '\t', 'Identified'
        else:
            print item['request']['artist_name'], '-', item['request']['song_name']
            print '\t', 'Unkonwn'
        print

    return found_rdio_tracks


def create_rdio_playlist(playlist_name, playlist_description, found_rdio_tracks):
    payload = {
        'method': 'createPlaylist',
        'name': playlist_name,
        'description': playlist_description,
        'tracks': ','.join(found_rdio_tracks),
        'isPublished': False,
    }
    r = requests.post(config.RDIO_API_URL, auth=BearerAuth(config.RDIO_API_TOKEN),
                      data=payload)

    r.raise_for_status()

    print r.json()


def main():
    logger = logging.getLogger(__name__)

    dest_dir_base = tempfile.mkdtemp(prefix='podmapper-')
    dest_dir_slice = tempfile.mkdtemp(prefix='slices-', dir=dest_dir_base)

    logger.info('Temp dir %s', dest_dir_base)
    logger.info('Temp slice dir %s', dest_dir_slice)

    downloaded_file_path = download_podcast(config.SRC_MP3, dest_dir_base)
    converted_file_path = convert_podcast(downloaded_file_path, dest_dir_base)
    split_wave_file(converted_file_path, dest_dir_slice)
    found_tracks = fingerprint_directory(dest_dir_slice)
    results = trim_tracks(found_tracks)

    catalog_name, _ = os.path.splitext(os.path.basename(downloaded_file_path))
    catalog_ticket = update_catalog(catalog_name, results)
    check_catalog_status(catalog_name, catalog_ticket)
    found_rdio_tracks = dump_catalog(catalog_name)

    playlist_name = catalog_name
    playlist_description = 'Created via Podmapper.\SRC_MP3=%s\nWAVE_SAMPLE_SIZE=%s\nFILTER_COUNT=%s' % (config.SRC_MP3, config.WAVE_SAMPLE_SIZE, config.FILTER_COUNT)
    create_rdio_playlist(playlist_name, playlist_description, found_rdio_tracks)

    shutil.rmtree(dest_dir_base)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Python requests logging (requests->urllib3->httplib)
    httplib.HTTPConnection.debuglevel = 0
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.WARN)
    requests_log.propagate = True

    main()
