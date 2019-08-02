#!/usr/bin/env python3
#
#  avtc.py
#
#  Copyright 2013-2019 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
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
import shlex
import subprocess
import time
import datetime
import re


class AvtcCommon:
    # list of file extentions to find
    fileExtList = [
        '3g2', '3gp', 'asf', 'avi', 'divx', 'flv', 'm2ts', 'm4a', 'm4v', 'mj2',
        'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nuv', 'ogg', 'ogm', 'ogv',
        'rm', 'rmvb', 'vob', 'webm', 'wmv'
        ]

    inputDir = '0in'
    outputDir = '0out'
    logDir = '0log'

    def __init__(self, fileList, workingDir, deinterlace=False,
                 scale720p=False, transcode_force=False):
        self.mkIODirs(workingDir)
        for f in fileList:
            if os.path.isfile(f):
                fileName, fileExtension = os.path.splitext(f)
                if self.checkFileType(fileExtension):
                    self.transcode(f, fileName, deinterlace, scale720p, transcode_force)

    def checkFileType(self, fileExtension):
        fileExtension = fileExtension[1:].lower()
        result = False
        for ext in self.fileExtList:
            if (ext == fileExtension):
                result = True
                break
        return result

    def runSubprocess(self, args):
        p = subprocess.Popen(shlex.split(args), stderr=subprocess.PIPE)
        stdoutData, stderrData = p.communicate()
        if stdoutData is not None:
            stdoutData = stdoutData.decode(encoding='utf-8', errors='ignore')
        if stderrData is not None:
            stderrData = stderrData.decode(encoding='utf-8', errors='ignore')
        return {'stdoutData': stdoutData, 'stderrData': stderrData,
                'returncode': p.returncode}

    def printLog(self, s):
        with open('{}/0transcode.log'.format(self.logDir),
                  'a', encoding='utf-8') as f:
            f.write('{}\n'.format(s))
        print(s)

    def mkIODirs(self, workingDir):
        for dir in [self.inputDir, self.outputDir, self.logDir]:
            if not os.path.exists(dir):
                os.mkdir('{}/{}'.format(workingDir, dir), 0o0755)

    def transcode(self, f, fileName, deinterlace, scale720p, transcode_force):
        inputFile = '{}/{}'.format(self.inputDir, f)
        outputFile = '{}/{}.mkv'.format(self.outputDir, fileName)
        outputFilePart = '{}.part'.format(outputFile)
        logFile = '{}/{}'.format(self.logDir, f)
        timeSpace = '        '
        os.rename(f, inputFile)

        self.printLog('{} Analyzing {}'.format(time.strftime('%X'),
                                               fileName.__repr__()))
        timeStarted = int(time.time())

        transcodeArgs = 'ffmpeg -i {}'.format(inputFile.__repr__())
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
                if not 'mjpeg' in stream:
                    result = re.findall('^\d*', stream)
                    mapList.append('-map 0:{}'.format(result[0]))
                    if not transcode_force and re.search('(h265|hevc)', stream) != None and re.search('(yuv420p10le|yuv420p12le)', stream) == None:
                        videoList.append('-c:v:{} '
                                         'copy'.format(videoStreamNumber))
                        videoCopy = True
                    else:
                        videoList.append('-c:v:{0} '
                                         'libx265 -profile:v:{0} main -pix_fmt:v:{0} yuv420p'.format(videoStreamNumber))
                    videoStreamNumber = videoStreamNumber + 1
            elif 'Audio' in stream:
                result = re.findall('^\d*', stream)
                mapList.append('-map 0:{}'.format(result[0]))
                if 'opus' in stream:
                    audioList.append('-c:a:{} copy'.format(audioStreamNumber))
                else:
                    audioBitRate = '256k'
                    if re.search('mono', stream) != None:
                        audioBitRate = '48k'
                    elif re.search('(stereo|downmix)', stream) != None:
                        audioBitRate = '96k'
                    elif re.search('(2.1|3.0|4.0|quad|5.0|4.1|5.1|6.0|hexagonal)',
                                   stream) != None:
                        audioBitRate = '128k'
                    elif re.search('(6.1,7.0,7.1,octagonal,'
                                   'hexadecagonal)', stream) != None:
                        audioBitRate = '256k'
                    audioList.append('-filter:a:{0} aformat=channel_layouts="'
                                     '7.1|5.1|stereo|mono" -c:a:{0} libopus '
                                     '-b:a:{0} {1}'.format(audioStreamNumber,
                                                           audioBitRate))
                audioStreamNumber = audioStreamNumber + 1
            elif 'Subtitle' in stream:
                result = re.findall('^\d*', stream)
                mapList.append('-map 0:{}'.format(result[0]))
                if re.search('(srt|ssa|subrip|mov_text)', stream) != None:
                    subtitleList.append('-c:s:{} '
                                        'ass'.format(subtitleStreamNumber))
                else:
                    subtitleList.append('-c:s:{} '
                                        'copy'.format(subtitleStreamNumber))
                subtitleStreamNumber = subtitleStreamNumber + 1
        mapArgs = ' '.join(mapList)
        videoArgs = ' '.join(videoList)
        audioArgs = ' '.join(audioList)
        subtitleArgs = ' '.join(subtitleList)

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

            videoFilterList = []
            if deinterlace:
                videoFilterList.append('bwdif')
            if scale720p:
                if input_w > 1280 or input_h > 720:
                    videoFilterList.append('scale=1280:-2')
                    self.printLog(('{} Above 720p: Scaling '
                                   'Enabled').format(timeSpace))
                else:
                    self.printLog(('{} Not Above 720p: Scaling '
                                   'Disabled').format(timeSpace))

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

            cropDetectVideoFilterArgs = '-filter:v ' + ','.join(cropDetectVideoFilterList)

            transcodeArgs = ('ffmpeg -i {} -ss {} -t {} {} -an -sn -f rawvideo '
                    '-y {}').format(inputFile.__repr__(), cropDetectStart,
                                    cropDetectDuration,
                                    cropDetectVideoFilterArgs,
                                    os.devnull)
            subprocessDict = self.runSubprocess(transcodeArgs)
            stderrData = subprocessDict['stderrData']

            timeCompletedCrop = int(time.time()) - timeStarted
            self.printLog('{} Analysis completed in {}'.format(time.strftime('%X'),
                          datetime.timedelta(seconds=timeCompletedCrop)))

            with open('{}.crop'.format(logFile), 'w', encoding='utf-8') as f:
                f.write('{}\n\n{}'.format(transcodeArgs, stderrData))
            self.printLog('{} Duration: {}'.format(timeSpace, duration))
            crop = re.findall('crop=(.*?)\n', stderrData)[-1]
            cropList = crop.split(':')
            w = int(cropList[0])
            h = int(cropList[1])

            self.printLog('{} Input  Resolution: {}x{}'.format(timeSpace,
                          input_w, input_h))
            self.printLog('{} Output Resolution: {}x{}'.format(timeSpace, w, h))

            videoFilterList.append('crop={}'.format(crop))
            videoFilterArgs = '-filter:v ' + ','.join(videoFilterList)
        else:
            videoFilterArgs = ''

        timeStartTranscoding = int(time.time())
        self.printLog('{} Transcoding Started'.format(timeSpace))

        transcodeArgs = ('ffmpeg -i {} {} {} {} {} {} '
                '-metadata title={} -y -f matroska '
                '-max_muxing_queue_size 1024 '
                '{}').format(inputFile.__repr__(), videoFilterArgs,
                              mapArgs, videoArgs, audioArgs, subtitleArgs,
                              fileName.__repr__(), outputFilePart.__repr__())
        subprocessDict = self.runSubprocess(transcodeArgs)
        stderrData = subprocessDict['stderrData']
        if subprocessDict['returncode'] != 0:
            with open('{}.error'.format(logFile), 'w', encoding='utf-8') as f:
                f.write('{}\n\n{}'.format(transcodeArgs, stderrData))
        else:
            with open('{}.transcode'.format(logFile), 'w',
                      encoding='utf-8') as f:
                f.write('{}\n\n{}'.format(transcodeArgs, stderrData))
        timeCompletedTranscoding = int(time.time()) - timeStartTranscoding
        self.printLog(('{} Transcoding completed in '
                       '{}\n').format(time.strftime('%X'),
                                      datetime.timedelta(
                                          seconds=timeCompletedTranscoding)))
        os.rename(outputFilePart, outputFile)

if __name__ == '__main__':

    import argparse

    if os.name == 'posix':
        os.nice(19)

    parser = argparse.ArgumentParser(
        prog='avtc.py',
        description='Audio Video TransCoder',
        epilog=(
            'Copyright 2013-2019 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>'))
    parser.add_argument(
        '--deinterlace', help='Deinterlace Videos.', action='store_true')
    parser.add_argument(
        '-d', '--directory', dest='directory', help='A directory')
    parser.add_argument(
        '-f', '--filelist', dest='fileList', help=(
            'A comma separated list of files in the current directory'))
    parser.add_argument(
        '--scale720p', help='Scale Videos to 720p.', action='store_true')
    parser.add_argument(
        '-t', '--transcode-force', help='Force file/s to be transcoded.',
        action='store_true')
    args = parser.parse_args()

    if (args.fileList and args.directory):
        print(('Arguments -f (--filelist) and -d (--directory) can not be '
            'used together.'))
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

    AvtcCommon(fileList, workingDir, args.deinterlace, args.scale720p, args.transcode_force)
