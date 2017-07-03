avtc
====

**A**udio **V**ideo **T**rans**C**oder - Batch transcodes Audio Video files to HEVC/Opus/ASS/Matroska.

Copyright 2013-2017 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>

Documentation
-------------

### Getting Started and Example Run

* Download avtc.py wherever you like. I stored it in `~/Projects/avtc/`.
* Put a symbolic link somewhere in your $PATH.  I chose `~/.local/bin/`.

```
ln -s ~/Projects/avtc/avtc.py ~/.local/bin/avtc
```

* View Help

```
$ avtc --help
usage: avtc.py [-h] [-f FILELIST] [-d DIRECTORY] [--deinterlace] [--scale720p]

Audio Video TransCoder

optional arguments:
  -h, --help            show this help message and exit
  -f FILELIST, --filelist FILELIST
                        A comma separated list of files in the current
                        directory
  -d DIRECTORY, --directory DIRECTORY
                        A directory
  --deinterlace         Deinterlace Videos.
  --scale720p           Scale Videos to 720p.

Copyright 2013-2017 Curtis lee Bolin <CurtisLeeBolin@gmail.com>
```

* Change to the videos directory you want to transcode.

* Run `avtc`.

```
$ avtc
19:17:07 Analyzing '2012 Vacation: Beach'
19:17:07 Analysis completed in 0:00:00
         Duration: 00:03:00.07
         Input  Resolution: 720x480
         Output Resolution: 720x480
         Transcoding Started
19:20:04 Transcoding completed in 0:02:57
```

```
19:20:04 Analyzing '2012 Vacation: Volcano'
19:20:05 Analysis completed in 0:00:01
         Duration: 00:05:00.06
         Input  Resolution: 720x480
         Output Resolution: 720x480
         Transcoding Started
19:25:07 Transcoding completed in 0:05:02
```

* Input files are stored in directory `0in`

```
$ ls -1sh 0in/
total 49M
 19M 2012 Vacation: Beach.mkv
 32M 2012 Vacation: Volcano.mkv
```

* Transcoded files are stored in directory `0out`

```
$ ls -1sh 0out/
total 41M
15M 2012 Vacation: Beach.mkv
27M 2012 Vacation: Volcano.mkv
```

* Logs files are stored in directory `0log`

```
$ ls -1sh 0log/
total 240K
4.0K 0transcode.log
 60K 2012 Vacation: Beach.mkv.crop
 36K 2012 Vacation: Beach.mkv.transcode
 88K 2012 Vacation: Volcano.mkv.crop
 52K 2012 Vacation: Volcano.mkv.transcode
```

### Output Format
* Video: HEVC (a.k.a. H.265 and MPEG-H Part 2)
* Audio: Opus
* Subtitles: ASS (text subtitles) or Copied from Source (image subtitles)
* Metadata: `title` is set to the filename minus the file extension
* Container: Matroska
