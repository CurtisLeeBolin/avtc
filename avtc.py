#!/usr/bin/env python3
#
#  avtc.py
#
#  Copyright 2013-2024 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
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

import datetime
import os
import re
import subprocess


class AVTC:
    # list of file extentions to find
    fileExtList = [
        '3g2', '3gp', 'asf', 'avi', 'divx', 'flv', 'm2ts', 'm4a', 'm4v', 'mj2',
        'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nuv', 'ogg', 'ogm', 'ogv',
        'rm', 'rmvb', 'ts', 'vob', 'webm', 'wmv'
    ]
    imageTypeList = ['mjpeg', 'png']
    inputDir = '0in'
    outputDir = '0out'

    def __init__(
        self,
        workingDir,
        fileList,
        crop=False,
        deinterlace=False,
        transcodeForce=False
    ):
        self.workingDir = workingDir
        self.fileList = fileList
        self.crop = crop
        self.deinterlace = deinterlace
        self.transcodeForce = transcodeForce

    def run(self):
        for file in self.fileList:
            if os.path.isfile(file):
                filename, fileExt = os.path.splitext(file)
                if self.checkFileType(fileExt):
                    self.transcode(
                        file,
                        filename,
                        self.crop,
                        self.deinterlace,
                        self.transcodeForce
                    )

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

    def printOnSameLine(self, line):
        columns, lines = os.get_terminal_size()
        clear_line_string = ' ' * columns
        line = line.replace('\n', '')
        line = line[:columns]
        print(f'\r{clear_line_string}\r{line}', end='')

    def timedeltaFormat(self, delta):
        """
        Formats a string from datetime.timedelta to HH:MM:SS

        datetime.timedelta does not support setting string format

        >>> help(datetime.timedelta.__format__)
        Help on method_descriptor:

            __format__(self, format_spec, /) unbound builtins.object method
            Default object formatter.

            Return str(self) if format_spec is empty. Raise TypeError otherwise.
        """
        s = delta.total_seconds()
        return f'{int(s/60/60 % 60):02}:{int(s/60 % 60):02}:{round(s % 60):02}'

    def runSubprocess(self, command):
        with subprocess.Popen(
            command,
            stderr = subprocess.PIPE,
            universal_newlines = True
        ) as p:
            stderrList = ['']*1024
            if p.stderr is not None:
                for line in p.stderr:
                    self.printOnSameLine(line)
                    del stderrList[0]
                    stderrList.append(line)
                print()
            p.wait()
            return (p.returncode, stderrList)

    def writeErrorFile(self, errorFile, transcodeArgs, stderrList):
        with open(errorFile, 'w', encoding='utf-8') as f:
            stderr = ''.join(stderrList)
            f.write(f'{transcodeArgs}\n\n{stderr}')

    def setMetadata(self, file, title):
        args = [
            'mkvpropedit',
            f'./{file}',
            '--tags', 'all:',
            '--edit', 'info',
            '--set', f'title={title}'
        ]
        return self.runSubprocess(args)

    def transcode(
        self,
        file,
        filename,
        crop,
        deinterlace,
        transcodeForce
    ):
        inputFile = f'{self.inputDir}/{file}'
        outputFile = f'{self.outputDir}/{filename}.webm'
        outputFilePart = f'{outputFile}.part'
        errorFile = f'{outputFile}.error'
        timeSpace = f'{" ":>9}'

        if not os.path.isfile(f'{file}.lock'):
            with open(f'{file}.lock', 'w') as f:
                pass

            now = datetime.datetime.now()
            print(f'{now:%H:%M:%S} Analyzing \'{filename}\'')

            timeStarted = now

            transcodeArgs = ['ffprobe', '-hide_banner', '-i', f'./{file}']
            returncode, stderrList = self.runSubprocess(transcodeArgs)
            if returncode != 0:
                self.writeErrorFile(errorFile, transcodeArgs, stderrList)

            videoCopy = False
            streamList = [x for x in stderrList if 'Stream #0' in x]
            stderrData = ''.join(stderrList)
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
                        result = re.findall(r'Stream #0:(\d+)', stream)
                        mapList.extend(['-map', f'0:{result[0]}'])
                        if (
                            not transcodeForce and not deinterlace
                            and re.search('av1', stream) is not None
                        ):
                            videoList.extend([
                                f'-c:v:{videoStreamNumber}', 'copy'
                            ])
                            videoCopy = True
                        else:
                            videoList.extend([
                                f'-c:v:{videoStreamNumber}', 'libsvtav1'
                            ])
                        videoStreamNumber = videoStreamNumber + 1
                        resolution = re.findall(
                            r'Video: .*? (\d\d+x\d+)', stream
                        )[0]
                        if resolution[-1] == ',':
                            resolution = resolution[:-1]
                        resolutionList = resolution.split('x')
                        input_w = int(resolutionList[0])
                        input_h = int(resolutionList[1])
                elif 'Audio' in stream:
                    result = re.findall(r'Stream #0:(\d+)', stream)
                    mapList.extend(['-map', f'0:{result[0]}'])
                    if 'opus' in stream:
                        audioList.extend([f'-c:a:{audioStreamNumber}', 'copy'])
                    else:
                        audioBitRate = '256k'
                        if re.search('mono', stream) is not None:
                            audioBitRate = '48k'
                        elif re.search('(stereo|downmix)', stream) is not None:
                            audioBitRate = '96k'
                        elif re.search(
                            '(2.1|3.0|4.0|quad|5.0|4.1|5.1|6.0|hexagonal)',
                            stream
                        ) is not None:
                            audioBitRate = '128k'
                        elif re.search(
                            '(6.1|7.0|7.1|octagonal|hexadecagonal)',
                            stream
                        ) is not None:
                            audioBitRate = '256k'
                        if re.search(r'5.1\(side\)', stream) is not None:
                            audioList.extend([
                                f'-filter:a:{audioStreamNumber}',
                                'aformat=channel_layouts=5.1'
                            ])
                        elif re.search(r'5.0\(side\)', stream) is not None:
                            audioList.extend([
                                f'-filter:a:{audioStreamNumber}',
                                'aformat=channel_layouts=5.0'
                            ])
                        audioList.extend([
                            f'-c:a:{audioStreamNumber}', 'libopus',
                            f'-b:a:{audioStreamNumber}', audioBitRate
                        ])
                    audioStreamNumber = audioStreamNumber + 1
                elif 'Subtitle' in stream:
                    result = re.findall(r'Stream #0:(\d+)', stream)
                    if 'webvtt' in stream:
                        mapList.extend(['-map', f'0:{result[0]}'])
                        subtitleList.extend([
                            f'-c:s:{subtitleStreamNumber}', 'copy'
                        ])
                    elif re.search(
                        '(srt|ssa|subrip|mov_text)',
                        stream
                    ) is not None:
                        mapList.extend(['-map', f'0:{result[0]}'])
                        subtitleList.extend([
                            f'-c:s:{subtitleStreamNumber}', 'webvtt'
                        ])
                    subtitleStreamNumber = subtitleStreamNumber + 1

            durationList = re.findall('Duration: (.*?),', stderrData)
            if durationList != []:
                durationString = durationList[-1]
                hours, minutes, seconds = durationString.split(':')
                durationSeconds = (
                    60 * 60 * int(hours) +
                    60 * int(minutes) +
                    float(seconds)
                )
            else:
                durationString = 'N/A'
                durationSeconds = 0
            videoFilterList = []
            if not videoCopy:
                if deinterlace:
                    videoFilterList.append('bwdif')

                if crop:
                    if durationSeconds != 0 and durationSeconds > 60:
                        start = datetime.timedelta(seconds=(durationSeconds / 10))
                        cropDetectStart = f'{self.timedeltaFormat(start)}'
                        duration = datetime.timedelta(seconds=(durationSeconds / 100))
                        cropDetectDuration = f'{self.timedeltaFormat(duration)}'
                    else:
                        cropDetectStart = '0'
                        cropDetectDuration = '60'

                    cropDetectVideoFilterList = list(videoFilterList)
                    cropDetectVideoFilterList.append('cropdetect')

                    transcodeArgs = [
                        'ffmpeg',
                        '-hide_banner',
                        '-nostats',
                        '-ss', cropDetectStart,
                        '-t', cropDetectDuration,
                        '-i', f'./{file}',
                        '-filter:v', ','.join(cropDetectVideoFilterList),
                        '-an',
                        '-sn',
                        '-f', 'rawvideo',
                        '-y',
                        os.devnull
                    ]

                    returncode, stderrList = self.runSubprocess(transcodeArgs)
                    if returncode != 0:
                        self.writeErrorFile(
                            errorFile,
                            transcodeArgs,
                            stderrList
                        )

                    stderrData = ''.join(stderrList)

                    crop = re.findall('crop=(.*?)\n', stderrData)[-1]
                    cropList = crop.split(':')
                    w = int(cropList[0])
                    h = int(cropList[1])

                    videoFilterList.append(f'crop={crop}')

            now = datetime.datetime.now()
            delta = now - timeStarted
            print(
                f'{now:%H:%M:%S} Analysis completed in',
                f'{self.timedeltaFormat(delta)}'
            )
            print(f'{timeSpace} Duration: {durationString}')
            print(f'{timeSpace} Input  Resolution: {input_w}x{input_h}')
            if crop and not videoCopy:
                print(f'{timeSpace} Output Resolution: {w}x{h}')
            else:
                print(f'{timeSpace} Output Resolution: {input_w}x{input_h}')

            timeStartTranscoding = now
            print(f'{timeSpace} Transcoding Started')

            transcodeArgs = [
                    'ffmpeg',
                    '-i', f'./{file}'
                ]
            if videoFilterList:
                transcodeArgs.extend([
                    '-filter:v', ','.join(videoFilterList)
                ])
            transcodeArgs.extend(mapList)
            transcodeArgs.extend(videoList)
            transcodeArgs.extend([
                '-svtav1-params', 'tune=2'
            ])
            transcodeArgs.extend(audioList)
            transcodeArgs.extend(subtitleList)
            transcodeArgs.extend([
                '-max_muxing_queue_size', '1024',
                '-y',
                '-f', 'matroska',
                outputFilePart
            ])
            transcodeArgs = list(filter(None, transcodeArgs))

            os.makedirs(self.outputDir, exist_ok=True)
            returncode, stderrList = self.runSubprocess(transcodeArgs)
            if returncode == 0:
                os.remove(f'{file}.lock')
                os.makedirs(self.inputDir, exist_ok=True)
                now = datetime.datetime.now()
                delta = now - timeStartTranscoding
                print(
                    f'{now:%H:%M:%S} Transcoding completed in',
                    f'{self.timedeltaFormat(delta)}'
                )
                print(f'{timeSpace} Setting Metadata')
                self.setMetadata(outputFilePart, filename)
                os.rename(outputFilePart, outputFile)
                os.rename(file, inputFile)
            else:
                self.writeErrorFile(errorFile, transcodeArgs, stderrList)
                now = datetime.datetime.now()
                print(f'{now:%H:%M:%S} Error: transcoding stopped\n')


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog = 'avtc.py',
        description = 'Audio Video TransCoder',
        epilog = (
            'Copyright 2013-2024 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>'
        )
    )
    parser.add_argument(
        '--crop',
        help = 'Auto Crop Videos',
        action = 'store_true'
    )
    parser.add_argument(
        '--deinterlace',
        help = 'Deinterlace Videos',
        action = 'store_true'
    )
    parser.add_argument(
        '-d',
        '--directory',
        dest = 'directory',
        help = 'A directory'
    )
    parser.add_argument(
        '-f',
        '--filelist',
        dest = 'fileList',
        nargs = '*',
        help = 'File list in the current directory'
    )
    parser.add_argument(
        '-t',
        '--transcode',
        help = 'Force file/s to be transcoded',
        action = 'store_true'
    )
    args = parser.parse_args()

    if (args.fileList and args.directory):
        print(
            'Arguments -f (--filelist) and -d (--directory) can not be ',
            'used together'
        )
        exit(1)
    elif (args.fileList):
        workingDir = os.getcwd()
        fileList = args.fileList
    elif (args.directory):
        workingDir = args.directory
        fileList = os.listdir(workingDir)
        fileList.sort()
    else:
        workingDir = os.getcwd()
        fileList = os.listdir(workingDir)
        fileList.sort()

    tc = AVTC(
        workingDir,
        fileList,
        args.crop,
        args.deinterlace,
        args.transcode
    )
    tc.run()


if __name__ == '__main__':
    main()
