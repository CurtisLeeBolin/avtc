avtc
====
avtc is a GPLv2 licensed batch x264/vorbis/matroska transcoder written in python3 that uses libav's avconv.

Documentation
-------------

###Getting Started and Example Run
1. Download avtc.py wherever you like. I stored it in `~/Projects/avtc/`.
2. Put a symbolic link somewhere in your $PATH and make it executable.  I chose `~/bin/`.
```
ln -s ~/Projects/avtc/avtc.py ~/bin/avtc
chmod +x ~/bin/avtc
```

3. Change to the videos directory you want to transcode.
4. Run `avtc`.
```
$ avtc 
13:38:43 Cropdetect started on 'My Family Vacation: Beach'
13:38:55 Cropdetect completed in 0:00:12
         Video Duration: 00:03:00.00
         Video output 1280x720 at 1333kb/s
         Audio output stereo at 112kb/s
         Estimated output size of 32MB at 1445kb/s
         Pass1 Started
13:45:18 Pass1 completed in 0:06:23
         Pass2 Started
13:52:13 Pass2 completed in 0:06:55
         Completed transcoding in 0:13:30
```
```
13:52:13 Cropdetect started on 'My Family Vacation: Volcano'
13:52:24 Cropdetect completed in 0:00:11
         Video Duration: 00:03:00.00
         Video output 1280x720 at 1333kb/s
         Audio output stereo at 112kb/s
         Estimated output size of 32MB at 1445kb/s
         Pass1 Started
13:58:11 Pass1 completed in 0:05:47
         Pass2 Started
14:05:01 Pass2 completed in 0:06:50
         Completed transcoding in 0:12:48
```

5. Input files and logs will be stored in directory `0in`
```
$ ls -1 0in
0pass-0.log
0pass-0.log.mbtree
0transcode.log
My Family Vacation: Beach.mkv
My Family Vacation: Beach.mkv.crop
My Family Vacation: Beach.mkv.pass1
My Family Vacation: Beach.mkv.pass2
My Family Vacation: Volcano.mkv
My Family Vacation: Volcano.mkv.crop
My Family Vacation: Volcano.mkv.pass1
My Family Vacation: Volcano.mkv.pass2
```

6. Transcoded files will be stored in directory `0out`
```
$ ls -1 0out
My Family Vacation: Beach.mkv
My Family Vacation: Volcano.mkv
```


###Output Format
* Video is 2pass x264.
 * Bitrate is calculated by a formula in avtc.
* Audio is Vorbis.
 * Quality is set to 3.
* Container is Matroska.
* Metadata `title` will be set to the file name minus the file extention.


TODO
----
* Clean Up/Re-Order `try` `except` so it has less duplicate code and doesn't run `printLog` in `try` if an exception is thrown.
* Add a lot of comments to the code.
