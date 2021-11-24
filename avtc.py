#!/usr/bin/env python3
#
#  avtc.py
#
#  Copyright 2013-2021 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
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

import os
import subprocess
import time
import datetime
import re
import threading
import queue


class AvtcCommon:
    # list of file extentions to find
    fileExtList = [ '3g2', '3gp', 'asf', 'avi', 'divx', 'flv', 'm2ts', 'm4a',
                    'm4v', 'mj2', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts',
                    'nuv', 'ogg', 'ogm', 'ogv', 'rm', 'rmvb', 'vob', 'webm',
                    'wmv']
    imageTypeList = ['mjpeg', 'png']
    inputDir = '0in'
    outputDir = '0out'

    def __init__(self, fileList, workingDir, deinterlace=False,
                 scale=None, transcode_force=False):
        self.mkIODirs(workingDir)
        for f in fileList:
            if os.path.isfile(f):
                fileName, fileExtension = os.path.splitext(f)
                if self.checkFileType(fileExtension):
                    self.transcode(f, fileName, deinterlace, scale,
                                   transcode_force)

    def checkFileType(self, fileExtension):
        fileExtension = fileExtension[1:].lower()
        result = False
        for ext in self.fileExtList:
            if (ext == fileExtension):
                result = True
                break
        return result

    def checkForImage(self, videoString):
        for each in self.imageTypeList:
            if each in videoString:
                return True
        return False

    def runSubprocess(self, args):
        p = subprocess.Popen(args, stderr=subprocess.PIPE)
        stdoutData, stderrData = p.communicate()
        if stdoutData is not None:
            stdoutData = stdoutData.decode(encoding='utf-8', errors='ignore')
        if stderrData is not None:
            stderrData = stderrData.decode(encoding='utf-8', errors='ignore')
        return {'stdoutData': stdoutData, 'stderrData': stderrData,
                'returncode': p.returncode}

    def mkIODirs(self, workingDir):
        for dir in [self.inputDir, self.outputDir]:
            if not os.path.exists(dir):
                os.mkdir('{}/{}'.format(workingDir, dir), 0o0755)

    def transcode(self, f, fileName, deinterlace, scale, transcode_force):
        inputFile = '{}/{}'.format(self.inputDir, f)
        outputFile = '{}/{}.mkv'.format(self.outputDir, fileName)
        outputFilePart = '{}.part'.format(outputFile)
        errorFile = '{}.error'.format(outputFile)
        timeSpace = '        '
        os.rename(f, inputFile)

        print(time.strftime('%X'), ' Analyzing \'', fileName, '\'', sep='')
        timeStarted = int(time.time())

        transcodeArgs = ['ffmpeg', '-i', inputFile]
        subprocessDict = self.runSubprocess(transcodeArgs)
        stderrData = subprocessDict['stderrData']

        videoCopy = False
        streamList = re.findall('Stream #0:(.*?)\n', stderrData)
        mapList = []
        videoList = []
        audioList = []
        subtitleList = []
        videoStreamNumber = 0
        audioStreamNumber = 0
        subtitleStreamNumber = 0
        for stream in streamList:
            if 'Video' in stream:
                if not self.checkForImage(stream):
                    result = re.findall('^\d*', stream)
                    mapList.extend(['-map', '0:{}'.format(result[0])])
                    if not transcode_force and re.search('(h265|hevc)',
                                                         stream) is not None:
                        videoList.extend(['-c:v:{}'.format(videoStreamNumber),
                                         'copy'])
                        videoCopy = True
                    else:
                        videoList.extend(['-c:v:{}'.format(videoStreamNumber),
                                         'libx265'])
                    videoStreamNumber = videoStreamNumber + 1
            elif 'Audio' in stream:
                result = re.findall('^\d*', stream)
                mapList.extend(['-map', '0:{}'.format(result[0])])
                if 'opus' in stream:
                    audioList.extend(['-c:a:{}'.format(audioStreamNumber), 'copy'])
                else:
                    audioBitRate = '256k'
                    if re.search('mono', stream) is not None:
                        audioBitRate = '48k'
                    elif re.search('(stereo|downmix)', stream) is not None:
                        audioBitRate = '96k'
                    elif re.search('(2.1|3.0|4.0|quad|5.0|4.1|5.1|6.0|hexagonal)',
                                   stream) is not None:
                        audioBitRate = '128k'
                    elif re.search('(6.1,7.0,7.1,octagonal,'
                                   'hexadecagonal)', stream) is not None:
                        audioBitRate = '256k'
                    audioList.extend(['-filter:a:{}'.format(audioStreamNumber),
                                    'aformat=channel_layouts=7.1|5.1|stereo|mono',
                                    '-c:a:{}'.format(audioStreamNumber),
                                    'libopus', '-b:a:{}'.format(audioStreamNumber), audioBitRate])
                audioStreamNumber = audioStreamNumber + 1
            elif 'Subtitle' in stream:
                result = re.findall('^\d*', stream)
                mapList.extend(['-map', '0:{}'.format(result[0])])
                if re.search('(srt|ssa|subrip|mov_text)', stream) is not None:
                    subtitleList.extend(['-c:s:{}'.format(subtitleStreamNumber), 'ass'])
                else:
                    subtitleList.extend(['-c:s:{}'.format(subtitleStreamNumber), 'copy'])
                subtitleStreamNumber = subtitleStreamNumber + 1

        if not videoCopy:
            durationList = re.findall('Duration: (.*?),', stderrData)
            duration = 'N/A'
            durationSplitList = None
            if durationList:
                duration = durationList[-1]
                durationSplitList = duration.split(':')

            resolution = re.findall('Video: .*? (\d\d+x\d+)', stderrData)[0]
            if resolution[-1] == ',':
                resolution = resolution[:-1]
            resolutionList = resolution.split('x')
            input_w = int(resolutionList[0])
            input_h = int(resolutionList[1])

            videoFilterList = ['-filter:v']
            if deinterlace:
                videoFilterList.append('bwdif')
            if scale == '720p':
                if input_w > 1280 or input_h > 720:
                    videoFilterList.append('scale=1280:-2')
                    print(timeSpace, 'Above 720p: Scaling Enabled')
                else:
                    print(timeSpace, 'Not Above 720p: Scaling Disabled')
            if scale == '1080p':
                if input_w > 1920 or input_h > 1080:
                    videoFilterList.append('scale=1920:-2')
                    print(timeSpace, 'Above 1080p: Scaling Enabled')
                else:
                    print(timeSpace, 'Not Above 1080p: Scaling Disabled')

            if duration != 'N/A':
                durationSec = (60 * 60 * int(durationSplitList[0]) + 60 *
                               int(durationSplitList[1]) +
                               float(durationSplitList[2]))
                cropDetectStart = str(datetime.timedelta(
                                      seconds=(durationSec / 10)))
                cropDetectDuration = str(datetime.timedelta(
                                         seconds=(durationSec / 100)))
            else:
                cropDetectStart = '0'
                cropDetectDuration = '60'

            cropDetectVideoFilterList = list(videoFilterList)
            cropDetectVideoFilterList.append('cropdetect')

            transcodeArgs = [
                'ffmpeg', '-i', inputFile, '-ss', cropDetectStart,
                '-t', cropDetectDuration
            ]
            transcodeArgs.extend(cropDetectVideoFilterList)
            transcodeArgs.extend([
                '-an', '-sn', '-f', 'rawvideo', '-y', os.devnull
            ])
            transcodeArgs = list(filter(None, transcodeArgs))

            subprocessDict = self.runSubprocess(transcodeArgs)
            stderrData = subprocessDict['stderrData']

            timeCompletedCrop = int(time.time()) - timeStarted

            print(time.strftime('%X'), 'Analysis completed in',
                datetime.timedelta(seconds=timeCompletedCrop))
            print(timeSpace, 'Duration:', duration)

            crop = re.findall('crop=(.*?)\n', stderrData)[-1]
            cropList = crop.split(':')
            w = int(cropList[0])
            h = int(cropList[1])

            print(timeSpace, ' Input  Resolution: ', input_w, 'x', input_h,
                sep='')
            print(timeSpace, ' Output Resolution: ', w, 'x', h, sep='')

            videoFilterList.append('crop={}'.format(crop))
        else:
            videoFilterList = []

        timeStartTranscoding = int(time.time())
        print(timeSpace, 'Transcoding Started')

        transcodeArgs = ['ffmpeg', '-v', 'error', '-stats', '-i', inputFile]
        transcodeArgs.extend(videoFilterList)
        transcodeArgs.extend(mapList)
        transcodeArgs.extend(videoList)
        transcodeArgs.extend(audioList)
        transcodeArgs.extend(subtitleList)
        transcodeArgs.extend([
            '-map_metadata', '-1', '-metadata', 'title={}'.format(fileName),
            '-max_muxing_queue_size', '1024', '-y', '-f',
            'matroska', outputFilePart
        ])
        transcodeArgs = list(filter(None, transcodeArgs))

        def enqueue_output(out, queue):
            for line in iter(out.readline, b''):
                queue.put(line)
            out.close()

        p = subprocess.Popen(transcodeArgs, stderr=subprocess.PIPE,
            universal_newlines=True)
        q = queue.Queue()
        t = threading.Thread(target=enqueue_output, args=(p.stderr, q))
        t.daemon = True
        t.start()

        stderrList = []
        while True:
            try:
                line = q.get(timeout=5)
                line_str = line[:-1]  # removes newline character at end
                print(line_str, end='\r', flush=True)
                stderrList.append(line)
            except:
                pass
            poll = p.poll()
            if poll is not None:
                print()
                if p.returncode != 0:
                    with open(errorFile, 'w', encoding='utf-8') as f:
                        f.write('{}\n\n{}'.format(transcodeArgs,
                            ''.join(stderrList)))
                break


        timeCompletedTranscoding = int(time.time()) - timeStartTranscoding
        print(time.strftime('%X'), 'Transcoding completed in',
            datetime.timedelta(seconds=timeCompletedTranscoding), '\n')
        os.rename(outputFilePart, outputFile)

if __name__ == '__main__':

    import argparse

    if os.name == 'posix':
        os.nice(19)

    parser = argparse.ArgumentParser(
        prog='avtc.py',
        description='Audio Video TransCoder',
        epilog=(
            'Copyright 2013-2021 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>'))
    parser.add_argument(
        '--deinterlace', help='Deinterlace Videos.', action='store_true')
    parser.add_argument(
        '-d', '--directory', dest='directory', help='A directory')
    parser.add_argument(
        '-f', '--filelist', dest='fileList', help=(
            'A comma separated list of files in the current directory'))
    parser.add_argument(
        '--scale', dest='scale', help='Scale Videos to 720p or 1080p.')
    parser.add_argument(
        '-t', '--transcode-force', help='Force file/s to be transcoded.',
        action='store_true')
    args = parser.parse_args()

    if (args.fileList and args.directory):
        print(('Arguments -f (--filelist) and -d (--directory) can not be '
               'used together.'))
        exit(1)
    elif (args.scale not in [None, '720p', '1080p']):
        print(('Argument --scale only accepts strings 720p or 1080p'))
        exit(1)
    elif (args.fileList):
        workingDir = os.getcwd()
        fileList = args.fileList.split(',')
    elif (args.directory):
        workingDir = args.directory
        fileList = os.listdir(workingDir)
        fileList.sort()
    else:
        workingDir = os.getcwd()
        fileList = os.listdir(workingDir)
        fileList.sort()

    if (args.scale in ['720p', '1080p']):
        args.transcode_force = True

    AvtcCommon(fileList, workingDir, args.deinterlace, args.scale,
               args.transcode_force)
