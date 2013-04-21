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

Update API key variables and then run:

    python podmapper.py

Built at [Music Hack Day Paris 2013](http://paris.musichackday.org/2013/)
