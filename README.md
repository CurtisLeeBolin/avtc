avtc
====

**A**udio **V**ideo **T**rans**C**oder - Batch transcodes Audio Video files to AV1/Opus/WebVTT/WebM.

Copyright 2013-2025 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>

Documentation
-------------

### Getting Started and Example Run

#### There are currently no releases
#### To install directly from GitHub

```
$ python -m pip install git+https://github.com/CurtisLeeBolin/avtc.git
```

#### Or download, extract, and install

```
$ cd avtc
$ python -m pip install .
```

#### Dependencies
  - ffmpeg

#### To view help

```
$ avtc --help
usage: avtc.py [-h] [--crop] [--deinterlace] [-d DIRECTORY] [-f [FILELIST ...]] [-t]

Audio Video TransCoder

options:
  -h, --help            show this help message and exit
  --crop                Auto Crop Videos
  --deinterlace         Deinterlace Videos
  -d DIRECTORY, --directory DIRECTORY
                        A directory
  -f [FILELIST ...], --filelist [FILELIST ...]
                        File list in the current directory
  -t, --transcode       Force file/s to be transcoded

Copyright 2013-2024 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
```

#### Change to a directory with videos you want to transcode
#### To run `avtc`

```
$ avtc
01:21:25 Analyzing '2012 Vacation: Volcano'
01:22:14 Analysis completed in 0:00:00
         Duration: 02:01:36.75
         Input  Resolution: 1920x800
         Output Resolution: 1920x800
         Transcoding Started
encoded 173625 frames in 4940.02s (35.14 fps), 356.72 kb/s, Avg QP:35.31
02:43:42 Transcoding completed in 1:21:28
```

#### To run `avtc` with auto crop

```
$ avtc --crop
00:05:27 Analyzing '2012 Vacation: Beach'
00:06:13 Analysis completed in 0:00:46
         Duration: 01:30:31.26
         Input  Resolution: 1916x796
         Output Resolution: 1904x784
         Transcoding Started
encoded 130219 frames in 4511.67s (28.86 fps), 390.06 kb/s, Avg QP:32.91
01:21:24 Transcoding completed in 1:15:11
```

### Output Format

* Video: AV1 (AOMedia Video 1)
* Audio: Opus
* Subtitles: WebVTT (Web Video Text Tracks)
* Metadata: `title` is set to the filename minus the file extension
* Container: WebM
