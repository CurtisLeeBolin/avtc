avtc
====
avtc is a GPLv2 licensed batch x264/Vorbis/Matroska transcoder written in Python3 that uses FFmpeg.
Copyright 2013-2014 Curtis lee Bolin <CurtisLeeBolin@gmail.com>

Documentation
-------------

###Getting Started and Example Run

* Download avtc.py wherever you like. I stored it in `~/Projects/github/avtc/`.

* Put a symbolic link somewhere in your $PATH and make it executable.  I chose `~/.local/bin/`.
```
ln -s ~/Projects/github/avtc/avtc.py ~/.local/bin/avtc
chmod +x ~/.local/bin/avtc
```

* View Help
```
 $ avtc --help
usage: avtc.py [-h] [-f FILELIST] [-d DIRECTORY] [--deinterlace] [--scale720p]

Audio Video Transcoder

optional arguments:
  -h, --help            show this help message and exit
  -f FILELIST, --filelist FILELIST
                        A comma separated list of files in the current
                        directory
  -d DIRECTORY, --directory DIRECTORY
                        A directory
  --deinterlace         Deinterlace Videos.
  --scale720p           Scale Videos to 720p.

Copyright 2013-2014 Curtis lee Bolin <CurtisLeeBolin@gmail.com>
```

* Change to the videos directory you want to transcode.

* Run `avtc`.
```
$ avtc
19:17:07 Cropdetect started on '2012 Vacation: Beach'
19:17:07 Cropdetect completed in 0:00:00
         Duration: 00:03:00.07
         Resolution: 720x480
         Transcoding Started
19:20:04 Transcoding completed in 0:02:57
```
```
19:20:04 Cropdetect started on '2012 Vacation: Volcano'
19:20:05 Cropdetect completed in 0:00:01
         Duration: 00:05:00.06
         Resolution: 720x480
         Transcoding Started
19:25:07 Transcoding completed in 0:05:02
```

* Input files and logs will be stored in directory `0in`
```
$ ls -1sh 0in/
total 50M
4.0K 0transcode.log
 19M 2012 Vacation: Beach.mkv
 60K 2012 Vacation: Beach.mkv.crop
 36K 2012 Vacation: Beach.mkv.transcode
 32M 2012 Vacation: Volcano.mkv
 88K 2012 Vacation: Volcano.mkv.crop
 52K 2012 Vacation: Volcano.mkv.transcode
```

* Transcoded files will be stored in directory `0out`
```
$ ls -1sh 0out/
total 41M
15M 2012 Vacation: Beach.mkv
27M 2012 Vacation: Volcano.mkv
```

###Output Format
* Video is h264 (High).
 * Quality is set to 23.
* Audio is Vorbis.
 * Quality is set to 3.
* Container is Matroska.
* Metadata `title` will be set to the filename minus the file extention.
