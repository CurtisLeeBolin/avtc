#!/usr/bin/env python3
#
#  avtc.py
#
#  Copyright 2013-2022 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
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
from multiprocessing import Process, Queue


class AvtcCommon:
    # list of file extentions to find
    fileExtList = [
        '3g2', '3gp', 'asf', 'avi', 'divx', 'flv', 'm2ts', 'm4a', 'm4v', 'mj2',
        'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nuv', 'ogg', 'ogm', 'ogv',
        'rm', 'rmvb', 'vob', 'webm', 'wmv']
    imageTypeList = ['mjpeg', 'png']
    inputDir = '0in'
    outputDir = '0out'

    def __init__(
            self, fileList, workingDir, crop=False, deinterlace=False,
            transcode_force=False):
        self.mkIODirs(workingDir)
        for file in fileList:
            if os.path.isfile(file):
                fileName, fileExtension = os.path.splitext(file)
                if self.checkFileType(fileExtension):
                    self.transcode(
                        file, fileName, crop, deinterlace, transcode_force)
        return None

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
        return {
            'stdoutData': stdoutData, 'stderrData': stderrData,
            'returncode': p.returncode}

    def mkIODirs(self, workingDir):
        for dir in [self.inputDir, self.outputDir]:
            if not os.path.exists(dir):
                os.mkdir(f'{workingDir}/{dir}', 0o0755)
        return None

    def transcode(self, file, fileName, crop, deinterlace, transcode_force):
        inputFile = f'{self.inputDir}/{file}'
        outputFile = f'{self.outputDir}/{fileName}.mkv'
        outputFilePart = f'{outputFile}.part'
        errorFile = f'{outputFile}.error'
        timeSpace = '        '
        os.rename(file, inputFile)

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
        input_w = 0
        input_h = 0
        w = 0
        h = 0
        for stream in streamList:
            if 'Video' in stream:
                if not self.checkForImage(stream):
                    result = re.findall(r'^\d*', stream)
                    mapList.extend(['-map', f'0:{result[0]}'])
                    if (not transcode_force and not deinterlace
                            and re.search('(h265|hevc)', stream) is not None):
                        videoList.extend([f'-c:v:{videoStreamNumber}', 'copy'])
                        videoCopy = True
                    else:
                        videoList.extend(
                            [f'-c:v:{videoStreamNumber}', 'libx265'])
                    videoStreamNumber = videoStreamNumber + 1
                    resolution = re.findall(r'Video: .*? (\d\d+x\d+)',
                                            stream)[0]
                    if resolution[-1] == ',':
                        resolution = resolution[:-1]
                    resolutionList = resolution.split('x')
                    input_w = int(resolutionList[0])
                    input_h = int(resolutionList[1])
            elif 'Audio' in stream:
                result = re.findall(r'^\d*', stream)
                mapList.extend(['-map', f'0:{result[0]}'])
                if 'opus' in stream:
                    audioList.extend([f'-c:a:{audioStreamNumber}', 'copy'])
                else:
                    audioBitRate = '256k'
                    if re.search('mono', stream) is not None:
                        audioBitRate = '48k'
                    elif re.search('(stereo|downmix)', stream) is not None:
                        audioBitRate = '96k'
                    elif (re.search(
                            '(2.1|3.0|4.0|quad|5.0|4.1|5.1|6.0|hexagonal)',
                            stream) is not None):
                        audioBitRate = '128k'
                    elif (re.search(
                            '(6.1,7.0,7.1,octagonal,hexadecagonal)',
                            stream) is not None):
                        audioBitRate = '256k'
                    audioList.extend([
                        f'-c:a:{audioStreamNumber}', 'libopus',
                        f'-b:a:{audioStreamNumber}', audioBitRate])
                audioStreamNumber = audioStreamNumber + 1
            elif 'Subtitle' in stream:
                result = re.findall(r'^\d*', stream)
                mapList.extend(['-map', f'0:{result[0]}'])
                if re.search('(srt|ssa|subrip|mov_text)', stream) is not None:
                    subtitleList.extend(
                        [f'-c:s:{subtitleStreamNumber}', 'ass'])
                else:
                    subtitleList.extend(
                        [f'-c:s:{subtitleStreamNumber}', 'copy'])
                subtitleStreamNumber = subtitleStreamNumber + 1

        durationList = re.findall('Duration: (.*?),', stderrData)
        duration = 'N/A'
        durationSplitList = None
        if durationList:
            duration = durationList[-1]
            durationSplitList = duration.split(':')
        videoFilterList = []
        if not videoCopy:
            if deinterlace:
                videoFilterList.append('bwdif')

            if crop:
                cropDetectVideoFilterList = list(videoFilterList)
                if duration != 'N/A':
                    durationSec = (
                        60 * 60 * int(durationSplitList[0]) +
                        60 * int(durationSplitList[1]) +
                        float(durationSplitList[2]))
                    if durationSec > 60:
                        cropDetectStart = str(
                            datetime.timedelta(seconds=(durationSec / 10)))
                        cropDetectDuration = str(
                            datetime.timedelta(seconds=(durationSec / 100)))
                    else:
                        cropDetectStart = '0'
                        cropDetectDuration = '60'
                else:
                    cropDetectStart = '0'
                    cropDetectDuration = '60'

                cropDetectVideoFilterList.append('cropdetect')

                transcodeArgs = [
                    'ffmpeg', '-ss', cropDetectStart,
                    '-t', cropDetectDuration, '-i', inputFile,
                    '-filter:v', ','.join(cropDetectVideoFilterList),
                    '-an', '-sn', '-f', 'rawvideo', '-y', os.devnull]

                subprocessDict = self.runSubprocess(transcodeArgs)
                stderrData = subprocessDict['stderrData']

                crop = re.findall('crop=(.*?)\n', stderrData)[-1]
                cropList = crop.split(':')
                w = int(cropList[0])
                h = int(cropList[1])

                videoFilterList.append(f'crop={crop}')

        timeCompletedCrop = int(time.time()) - timeStarted
        print(
            f'{time.strftime("%X")} Analysis completed in',
            f'{datetime.timedelta(seconds=timeCompletedCrop)}')
        print(f'{timeSpace} Duration: {duration}')
        print(f'{timeSpace} Input  Resolution: {input_w}x{input_h}')
        if crop and not videoCopy:
            print(f'{timeSpace} Output Resolution: {w}x{h}')
        else:
            print(f'{timeSpace} Output Resolution: {input_w}x{input_h}')

        timeStartTranscoding = int(time.time())
        print(timeSpace, 'Transcoding Started')

        transcodeArgs = []
        if not videoFilterList:
            transcodeArgs = [
                'ffmpeg', '-v', 'error', '-stats', '-i', inputFile]
        else:
            transcodeArgs = [
                'ffmpeg', '-v', 'error', '-stats', '-i', inputFile,
                '-filter:v', ','.join(videoFilterList)]
        transcodeArgs.extend(mapList)
        transcodeArgs.extend(videoList)
        transcodeArgs.extend(audioList)
        transcodeArgs.extend(subtitleList)
        transcodeArgs.extend([
            '-map_metadata', '-1', '-metadata', f'title={fileName}',
            '-max_muxing_queue_size', '1024', '-y', '-f', 'matroska',
            outputFilePart])
        transcodeArgs = list(filter(None, transcodeArgs))

        def enqueue_output(stderr, queue):
            for line in iter(stderr.readline, b''):
                queue.put(line)
            stderr.close()
            return None

        p = subprocess.Popen(
            transcodeArgs, stderr=subprocess.PIPE, universal_newlines=True)
        q = Queue()
        mp = Process(target=enqueue_output, args=(p.stderr, q), daemon=True)
        mp.start()

        stderrList = ['']*20
        while True:
            if not q.empty():
                line = q.get(timeout=1)
                line_str = line[:-1]  # removes newline character at end
                print(line_str, end='\r')
                del stderrList[0]
                stderrList.append(line)
                if p.poll() is not None:
                    if p.returncode != 0:
                        with open(errorFile, 'w', encoding='utf-8') as f:
                            stderr = ''.join(stderrList)
                            f.write(f'{transcodeArgs}\n\n{stderr}')
                    q.close()
                    q.join_thread()
                    mp.terminate()
                    mp.join()
                    mp.close()
                    print()
                    break

        timeCompletedTranscoding = int(time.time()) - timeStartTranscoding
        print(
            f'{time.strftime("%X")} Transcoding completed in',
            f'{datetime.timedelta(seconds=timeCompletedTranscoding)}\n')
        os.rename(outputFilePart, outputFile)
        return None


if __name__ == '__main__':

    import argparse

    if os.name == 'posix':
        os.nice(19)

    parser = argparse.ArgumentParser(
        prog='avtc.py',
        description='Audio Video TransCoder',
        epilog=(
            'Copyright 2013-2022 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>'))
    parser.add_argument(
        '--crop', help='Auto Crop Videos', action='store_true')
    parser.add_argument(
        '--deinterlace', help='Deinterlace Videos', action='store_true')
    parser.add_argument(
        '-d', '--directory', dest='directory', help='A directory')
    parser.add_argument(
        '-f', '--filelist', dest='fileList', help=(
            'A comma separated list of files in the current directory'))
    parser.add_argument(
        '-t', '--transcode-force', help='Force file/s to be transcoded',
        action='store_true')
    args = parser.parse_args()

    if (args.fileList and args.directory):
        print(
            'Arguments -f (--filelist) and -d (--directory) can not be ',
            'used together')
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

    AvtcCommon(fileList, workingDir, args.crop, args.deinterlace,
               args.transcode_force)
