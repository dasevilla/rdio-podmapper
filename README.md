# Podmapper


## Problem

You don't have enough time to listen to every episode of every music podcast. It would be great if you could just get a playlist that contains the tracks played in the episode.


## Method

1. Download a podcast as MP3
2. Transcode MP3 to WAV
3. Split WAV into sample files (30 seconds?)
4. Fingerprint each sample using Gracenote API
6. Remove tracks that only appear once
7. Upload track metadata to an Echo Nest Taste Profile
8. Wait for bulk identification to complete
9. Use Rdio bucket to retrieve Rdio track IDs
0. Create a playlist in Rdio using track IDs from The Echo Nest



## Usage

Copy `config-sample.py` to `config.py` and add your API keys. The program assumes you have `lame` and `gnfingerprint`.

    python podmapper.py

`gnfingerprint` is C program based on the `musicid_stream` sample code included in the GNSDK. To build it:

1. Replace `$GNSDK/samples/musicid_stream/main.c` with the `main.c` included in this repository
2. Run `make`
3. Once built, rename `sample` to `gnfingerprint`
4. Place `gnfingerprint` it in your `$PATH`

Built at [Music Hack Day Paris 2013](http://paris.musichackday.org/2013/)
