avtc
====
avtc is a GPLv2 licensed batch x264/vorbis/matroska transcoder written in python3 that uses libav's avconv.

Documentation
-------------

###Getting Started and Example Run
1. Download avtc.py where ever you like. I stored it in `~/Projects/avtc/`.
2. Put a symbolic link somewhere in your $PATH and make it executable.  I chose `~/bin/`.
```
ln -s ~/Projects/avtc/avtc.py ~/bin/avtc
chmod +x ~/bin/avtc
```

3. Change to the videos directory want to transcode.
4. Then run `avtc`.
```
$ avtc
12:50:59 Cropdetect started on 'My Family Vacation-001'
12:51:10 Cropdetect completed in 0:00:11
         Video Duration: 00:03:00.00
         Video output 1280x720 at 1333kb/s
         Audio output stereo at 112kb/s
         Estimated output size of 32MB at 1445kb/s
         Pass1 Started
12:57:36 Pass1 completed in 0:06:26
         Pass2 Started
13:04:43 Pass2 completed in 0:07:07
13:04:43 Completed transcoding in 0:13:44
```
```
13:04:43 Cropdetect started on 'My Family Vacation-002'
13:04:54 Cropdetect completed in 0:00:11
         Video Duration: 00:03:00.00
         Video output 1280x720 at 1333kb/s
         Audio output stereo at 112kb/s
         Estimated output size of 32MB at 1445kb/s
         Pass1 Started
13:10:53 Pass1 completed in 0:05:59
         Pass2 Started
13:17:43 Pass2 completed in 0:06:50
13:17:43 Completed transcoding in 0:13:00
```

5. Input files and logs will be stored in directory `0in`
6. Transcoded file will be stored in directory `0out`

###Output Format
* Vidoe is 2pass x264.
 * Bitrate is calculated by a formula in avtc.
* Audio is Vorbis.
 * Quality is set to 3.
* Container is Matroska.
* Metadata `title` will be set to the file name minus the file extention.


TODO
----
* Clean Up/Re-Order `try` `except` so it has less duplicate code and doesn't run `printLog` in `try` if an exception is thrown.
* Add a lot of comments to the code.
