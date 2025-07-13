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


class AudioVideoTransCoder:
    # list of file extentions to find
    file_ext_list = [
        '3g2', '3gp', 'asf', 'avi', 'divx', 'flv', 'm2ts', 'm4a', 'm4v', 'mj2',
        'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nuv', 'ogg', 'ogm', 'ogv',
        'rm', 'rmvb', 'ts', 'vob', 'webm', 'wmv'
    ]
    image_type_list = ['mjpeg', 'png']
    input_dir = '0in'
    output_dir = '0out'

    def __init__(
        self,
        working_dir,
        file_list,
        crop=False,
        deinterlace=False,
        transcode_force=False
    ):
        self.working_dir = working_dir
        self.file_list = file_list
        self.crop = crop
        self.deinterlace = deinterlace
        self.transcode_force = transcode_force

    def run(self):
        for file in self.file_list:
            if os.path.isfile(file):
                filename, file_ext = os.path.splitext(file)
                if self.check_file_type(file_ext):
                    self.transcode(
                        file,
                        filename,
                        self.crop,
                        self.deinterlace,
                        self.transcode_force
                    )

    def check_file_type(self, file_ext):
        file_ext = file_ext[1:].lower()
        result = False
        for ext in self.file_ext_list:
            if (ext == file_ext):
                result = True
                break
        return result

    def check_for_image(self, videoString):
        for each in self.image_type_list:
            if each in videoString:
                return True
        return False

    def print_on_same_line(self, line):
        columns, lines = os.get_terminal_size()
        clear_line_string = ' ' * columns
        line = line.replace('\n', '')
        line = line[:columns]
        print(f'\r{clear_line_string}\r{line}', end='')

    def time_delta_format(self, delta):
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

    def run_subprocess(self, command):
        with subprocess.Popen(
            command,
            stderr = subprocess.PIPE,
            universal_newlines = True
        ) as p:
            stderr_list = ['']*1024
            if p.stderr is not None:
                for line in p.stderr:
                    self.print_on_same_line(line)
                    del stderr_list[0]
                    stderr_list.append(line)
                print()
            p.wait()
            return (p.returncode, stderr_list)

    def write_error_file(self, error_file, transcode_args, stderr_list):
        with open(error_file, 'w', encoding='utf-8') as f:
            stderr = ''.join(stderr_list)
            f.write(f'{transcode_args}\n\n{stderr}')

    def transcode(
        self,
        file,
        filename,
        crop,
        deinterlace,
        transcode_force
    ):
        input_file = f'{self.input_dir}/{file}'
        output_file = f'{self.output_dir}/{filename}.webm'
        output_file_part = f'{output_file}.part'
        error_file = f'{output_file}.error'
        time_spacing = f'{" ":>9}'

        if not os.path.isfile(f'{file}.lock'):
            with open(f'{file}.lock', 'w') as f:
                pass

            now = datetime.datetime.now()
            print(f'{now:%H:%M:%S} Analyzing \'{filename}\'')

            time_started = now

            transcode_args = ['ffprobe', '-hide_banner', '-i', f'./{file}']
            returncode, stderr_list = self.run_subprocess(transcode_args)
            if returncode != 0:
                self.write_error_file(error_file, transcode_args, stderr_list)

            video_copy = False
            stream_list = [x for x in stderr_list if 'Stream #0' in x]
            stderr_data = ''.join(stderr_list)
            map_list = []
            video_list = []
            audio_list = []
            subtitle_list = []
            video_stream_number = 0
            audio_stream_number = 0
            subtitle_stream_number = 0
            input_w = 0
            input_h = 0
            w = 0
            h = 0
            for stream in stream_list:
                if 'Video' in stream:
                    if not self.check_for_image(stream):
                        result = re.findall(r'Stream #0:(\d+)', stream)
                        map_list.extend(['-map', f'0:{result[0]}'])
                        if (
                            not transcode_force and not deinterlace
                            and re.search('av1', stream) is not None
                        ):
                            video_list.extend([
                                f'-c:v:{video_stream_number}', 'copy'
                            ])
                            video_copy = True
                        else:
                            video_list.extend([
                                f'-c:v:{video_stream_number}', 'libsvtav1'
                            ])
                        video_stream_number = video_stream_number + 1
                        resolution = re.findall(
                            r'Video: .*? (\d\d+x\d+)', stream
                        )[0]
                        if resolution[-1] == ',':
                            resolution = resolution[:-1]
                        resolution_list = resolution.split('x')
                        input_w = int(resolution_list[0])
                        input_h = int(resolution_list[1])
                elif 'Audio' in stream:
                    result = re.findall(r'Stream #0:(\d+)', stream)
                    map_list.extend(['-map', f'0:{result[0]}'])
                    if 'opus' in stream:
                        audio_list.extend([f'-c:a:{audio_stream_number}', 'copy'])
                    else:
                        audio_bit_rate = '256k'
                        if re.search('mono', stream) is not None:
                            audio_bit_rate = '48k'
                        elif re.search('(stereo|downmix)', stream) is not None:
                            audio_bit_rate = '96k'
                        elif re.search(
                            '(2.1|3.0|4.0|quad|5.0|4.1|5.1|6.0|hexagonal)',
                            stream
                        ) is not None:
                            audio_bit_rate = '128k'
                        elif re.search(
                            '(6.1|7.0|7.1|octagonal|hexadecagonal)',
                            stream
                        ) is not None:
                            audio_bit_rate = '256k'
                        if re.search(r'5.1\(side\)', stream) is not None:
                            audio_list.extend([
                                f'-filter:a:{audio_stream_number}',
                                'aformat=channel_layouts=5.1'
                            ])
                        elif re.search(r'5.0\(side\)', stream) is not None:
                            audio_list.extend([
                                f'-filter:a:{audio_stream_number}',
                                'aformat=channel_layouts=5.0'
                            ])
                        audio_list.extend([
                            f'-c:a:{audio_stream_number}', 'libopus',
                            f'-b:a:{audio_stream_number}', audio_bit_rate
                        ])
                    audio_stream_number = audio_stream_number + 1
                elif 'Subtitle' in stream:
                    result = re.findall(r'Stream #0:(\d+)', stream)
                    if 'webvtt' in stream:
                        map_list.extend(['-map', f'0:{result[0]}'])
                        subtitle_list.extend([
                            f'-c:s:{subtitle_stream_number}', 'copy'
                        ])
                    elif re.search(
                        '(srt|ssa|subrip|mov_text)',
                        stream
                    ) is not None:
                        map_list.extend(['-map', f'0:{result[0]}'])
                        subtitle_list.extend([
                            f'-c:s:{subtitle_stream_number}', 'webvtt'
                        ])
                    subtitle_stream_number = subtitle_stream_number + 1

            duration_list = re.findall('Duration: (.*?),', stderr_data)
            if duration_list != []:
                duration_string = duration_list[-1]
                hours, minutes, seconds = duration_string.split(':')
                duration_seconds = (
                    60 * 60 * int(hours) +
                    60 * int(minutes) +
                    float(seconds)
                )
            else:
                duration_string = 'N/A'
                duration_seconds = 0
            video_filter_list = []
            if not video_copy:
                if deinterlace:
                    video_filter_list.append('bwdif')

                if crop:
                    if duration_seconds != 0 and duration_seconds > 60:
                        start = datetime.timedelta(seconds=(duration_seconds / 10))
                        crop_detect_start = f'{self.time_delta_format(start)}'
                        duration = datetime.timedelta(seconds=(duration_seconds / 100))
                        crop_detect_duration = f'{self.time_delta_format(duration)}'
                    else:
                        crop_detect_start = '0'
                        crop_detect_duration = '60'

                    crop_detect_video_filter_list = list(video_filter_list)
                    crop_detect_video_filter_list.append('cropdetect')

                    transcode_args = [
                        'ffmpeg',
                        '-hide_banner',
                        '-nostats',
                        '-ss', crop_detect_start,
                        '-t', crop_detect_duration,
                        '-i', f'./{file}',
                        '-filter:v', ','.join(crop_detect_video_filter_list),
                        '-an',
                        '-sn',
                        '-f', 'rawvideo',
                        '-y',
                        os.devnull
                    ]

                    returncode, stderr_list = self.run_subprocess(transcode_args)
                    if returncode != 0:
                        self.write_error_file(
                            error_file,
                            transcode_args,
                            stderr_list
                        )

                    stderr_data = ''.join(stderr_list)

                    crop = re.findall('crop=(.*?)\n', stderr_data)[-1]
                    crop_list = crop.split(':')
                    w = int(crop_list[0])
                    h = int(crop_list[1])

                    video_filter_list.append(f'crop={crop}')

            now = datetime.datetime.now()
            delta = now - time_started
            print(
                f'{now:%H:%M:%S} Analysis completed in',
                f'{self.time_delta_format(delta)}'
            )
            print(f'{time_spacing} Duration: {duration_string}')
            print(f'{time_spacing} Input  Resolution: {input_w}x{input_h}')
            if crop and not video_copy:
                print(f'{time_spacing} Output Resolution: {w}x{h}')
            else:
                print(f'{time_spacing} Output Resolution: {input_w}x{input_h}')

            time_start_transcoding = now
            print(f'{time_spacing} Transcoding Started')

            transcode_args = [
                'ffmpeg',
                '-i', f'./{file}'
            ]
            if video_filter_list:
                transcode_args.extend([
                    '-filter:v', ','.join(video_filter_list)
                ])
            transcode_args.extend(map_list)
            transcode_args.extend(video_list)
            transcode_args.extend([
                '-svtav1-params', 'tune=2:preset=5'
            ])
            transcode_args.extend(audio_list)
            transcode_args.extend(subtitle_list)
            transcode_args.extend([
                '-max_muxing_queue_size', '1024',
                '-map_metadata', '0',
                '-metadata', f'title={filename}',
                '-metadata', 'svtav1-params=tune=2:preset=5',
                '-y',
                '-f', 'webm',
                output_file_part
            ])
            transcode_args = list(filter(None, transcode_args))

            os.makedirs(self.output_dir, exist_ok=True)
            returncode, stderr_list = self.run_subprocess(transcode_args)
            if returncode == 0:
                os.remove(f'{file}.lock')
                os.makedirs(self.input_dir, exist_ok=True)
                now = datetime.datetime.now()
                delta = now - time_start_transcoding
                print(
                    f'{now:%H:%M:%S} Transcoding completed in',
                    f'{self.time_delta_format(delta)}'
                )
                os.rename(output_file_part, output_file)
                os.rename(file, input_file)
            else:
                self.write_error_file(error_file, transcode_args, stderr_list)
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
        dest = 'file_list',
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

    if (args.file_list and args.directory):
        print(
            'Arguments -f (--filelist) and -d (--directory) can not be ',
            'used together'
        )
        exit(1)
    elif (args.file_list):
        working_dir = os.getcwd()
        file_list = args.file_list
    elif (args.directory):
        working_dir = args.directory
        file_list = os.listdir(working_dir)
        file_list.sort()
    else:
        working_dir = os.getcwd()
        file_list = os.listdir(working_dir)
        file_list.sort()

    tc = AudioVideoTransCoder(
        working_dir,
        file_list,
        args.crop,
        args.deinterlace,
        args.transcode
    )
    tc.run()


if __name__ == '__main__':
    main()
