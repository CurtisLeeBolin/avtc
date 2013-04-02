#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  avtc.py
#
#  Copyright 2013 Curtis Lee Bolin <curtlee2002@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

import os, shlex, subprocess, time, datetime, re

fileType=['avi', 'flv', 'mov', 'mp4', 'mpeg', 'mpg', 'ogg', 'ogm',
    'ogv', 'wmv', 'm2ts', 'mkv', 'rmvb', 'rm', '3gp', 'm4a', '3g2',
    'mj2', 'asf', 'divx', 'vob']
inputDir = '0in'
outputDir = '0out'
audioBitrateDict = {
    'mono' : 72,
    'stereo' : 112,
    '5.1' : 276,
    '7.1' : 640}

def checkFileType(fileExtension):
    fileExtension = fileExtension[1:].lower()
    result = False
    for ext in fileType:
        if (ext == fileExtension):
            result = True
            break
    return result

def run(args):
    p = subprocess.Popen(args, stderr=subprocess.PIPE)
    stdoutData, stderrData = p.communicate()
    stderrData = stderrData.decode()
    return stderrData

def printLog(s):
    with open(inputDir + '/0transcode.log', 'a') as f:
        f.write(s + '\n')
    print(s)

def main():
    for dir in [inputDir, outputDir]:
        if not os.path.exists(dir):
            os.mkdir(dir, 0o0755)
    cwd = os.getcwd()
    fileList = os.listdir(cwd)
    fileList.sort()
    for f in fileList:
        if os.path.isfile(f):
            fileName, fileExtension = os.path.splitext(f)
            if checkFileType(fileExtension):
                inputFile  = inputDir + '/' + f
                outputFile = outputDir + '/' + fileName + '.mkv'
                outputFilePart = outputFile + '.part'
                os.rename(f, inputFile)
                printLog('Started transcoding ' + fileName.__repr__() + ' at ' + time.strftime('%X'))
                timeStarted = int(time.time())

                try:
                    args = shlex.split('avconv -i ' + inputFile.__repr__() + ' -ss 00:02:00 -t 48 -vf cropdetect -an -sn -f rawvideo -y /dev/null')
                    stderrData = run(args)
                    timeCompletedCrop = int(time.time()) - timeStarted
                    printLog('Cropdetect completed in ' + str(datetime.timedelta(seconds=timeCompletedCrop)) + ' at ' + time.strftime('%X'))
                    with open(inputFile + '.crop', 'w') as f:
                        f.write(stderrData)
                    durationLine = stderrData.split('Duration: ')[-1]
                    duration = durationLine.split(',')[0]
                    printLog('Video Duration: ' + duration)
                    cropLine = stderrData.split('cropdetect')[-1]
                    cropLine = cropLine.split('\n')[0]
                    crop = cropLine.split('crop')[1]
                except:
                    args = shlex.split('avconv -i ' + inputFile.__repr__() + ' -ss 00:00:03 -t 5 -vf cropdetect -an -sn -f rawvideo -y /dev/null')
                    stderrData = run(args)
                    timeCompletedCrop = int(time.time()) - timeStarted
                    printLog('Cropdetect completed in ' + str(datetime.timedelta(seconds=timeCompletedCrop)) + ' at ' + time.strftime('%X'))
                    with open(inputFile + '.crop', 'w') as f:
                        f.write(stderrData)
                    durationLine = stderrData.split('Duration: ')[-1]
                    duration = durationLine.split(',')[0]
                    printLog('Video Duration: ' + duration)
                    cropLine = stderrData.split('cropdetect')[-1]
                    cropLine = cropLine.split('\n')[0]
                    crop = cropLine.split('crop')[1]

                w = cropLine.split('w:')[1]
                w = int(w.split(' ')[0])
                h = cropLine.split('h:')[1]
                h = int(h.split(' ')[0])
                videoBitrate = (((w*h)**0.5)*25/18).__round__()
                printLog('Video output %dx%d at %dkb/s' % (w, h, videoBitrate))
                audioLine = stderrData.split('Audio: ')[-1]
                audioLine = stderrData.split('Hz, ')[-1]
                audioCh = audioLine.split(',')[0]
                audioBitrate = audioBitrateDict.get(audioCh,'unknown')
                if duration != 'N/A':
                    timeList = list(map(int, re.split(r"[:.]", duration)))
                    durationSec = (timeList[0]*3600+timeList[1]*60+timeList[2]+timeList[3]/1000.)
                    if audioBitrate != 'unknown':
                        printLog('Audio output %s at %skb/s' % (audioCh, audioBitrate))
                        printLog('Estimated output size of %dMB at %dkb/s' % ((((videoBitrate + audioBitrate) * durationSec)/(1024 * 8)), (videoBitrate + audioBitrate)))
                    else:
                        printLog('Audio ' +  audioCh + ' is unknown')
                        printLog('Extimated output size of %dMB at %dkb/s (audio not included)' % (((videoBitrate * durationSec)/(1024 * 8)), videoBitrate))
                else:
                    printLog('Estimated file size can\'t be calculated since the duration is unknown.')
                timeStartPass1 = int(time.time())
                args = shlex.split('avconv -i ' + inputFile.__repr__() + ' -pass 1 -passlogfile ' + inputDir + '/0pass -vf crop' + crop + ' -c:v libx264 -preset veryslow -b:v ' +  videoBitrate.__str__() + 'k -an -sn -f rawvideo -y /dev/null')
                stderrData = run(args)
                timeCompletedPass1 = int(time.time()) - timeStartPass1
                printLog('Pass1 completed in ' + str(datetime.timedelta(seconds=timeCompletedPass1)) + ' at ' + time.strftime('%X'))
                with open(inputFile + '.pass1', 'w') as f:
                    f.write(stderrData)
                timeStartPass2 = int(time.time())
                args = shlex.split('avconv -i ' + inputFile.__repr__() + ' -pass 2 -passlogfile ' + inputDir + '/0pass -vf crop' + crop + ' -c:v libx264 -preset veryslow -b:v ' +  videoBitrate.__str__() + 'k -c:a libvorbis -q:a 3 -sn -f matroska -metadata title="' + fileName + '" ' + outputFilePart.__repr__())
                stderrData = run(args)
                timeCompletedPass2 = int(time.time()) - timeStartPass2
                printLog('Pass2 completed in ' + str(datetime.timedelta(seconds=timeCompletedPass2)) + ' at ' + time.strftime('%X'))
                with open(inputFile + '.pass2', 'w') as f:
                    f.write(stderrData)
                os.rename(outputFilePart, outputFile)
                timeCompleted = int(time.time())
                timeJobSeconds = timeCompleted - timeStarted
                timeJob = str(datetime.timedelta(seconds=timeJobSeconds))
                printLog('Completed transcoding in ' + timeJob + ' at ' + time.strftime('%X') + '\n')
    return 0

if __name__ == '__main__':
    main()
