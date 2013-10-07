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
	'2' : 112,
	'2 channels' : 112,
	'5.1' : 276,
	'5.1(side)' : 276,
	'7.1' : 640}
bitRateVary = 512.0

def checkFileType(fileExtension):
	fileExtension = fileExtension[1:].lower()
	result = False
	for ext in fileType:
		if (ext == fileExtension):
			result = True
			break
	return result

def runSubprocess(args):
	p = subprocess.Popen(args, stderr=subprocess.PIPE)
	stdoutData, stderrData = p.communicate()
	stderrData = stderrData.decode()
	return stderrData

def printLog(s):
	with open('{}/0transcode.log'.format(inputDir), 'a') as f:
		f.write('{}\n'.format(s))
	print(s)

if __name__ == '__main__':
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
				inputFile  = '{}/{}'.format(inputDir, f)
				outputFile = '{}/{}.mkv'.format(outputDir, fileName)
				outputFilePart = '{}.part'.format(outputFile)
				os.rename(f, inputFile)

				printLog('{} Cropdetect started on {}'.format(time.strftime('%X'), fileName.__repr__()))
				timeStarted = int(time.time())

				args = shlex.split('ffmpeg -i {}'.format(inputFile.__repr__()))
				stderrData = runSubprocess(args)
				duration = re.findall('Duration: (.*?),', stderrData)[-1]
				audioCodec = re.findall('Audio: (.*?),', stderrData)[-1]
				durationList = duration.split(':')
				if duration != 'N/A':
					durationSec = 60 * 60 * int(durationList[0]) + 60 * int(durationList[1]) + float(durationList[2])
					cropDetectStart =  str(datetime.timedelta(seconds=(durationSec / 10)))
					cropDetectDuration =  str(datetime.timedelta(seconds=(durationSec / 100)))
				else:
					cropDetectStart = '0'
					cropDetectDuration = '60'
				args = shlex.split('ffmpeg -i {} -ss {} -t {} -filter:v cropdetect -an -sn -f rawvideo -y /dev/null'.format(inputFile.__repr__(), cropDetectStart, cropDetectDuration))
				stderrData = runSubprocess(args)

				timeCompletedCrop = int(time.time()) - timeStarted
				printLog('{} Cropdetect completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedCrop)))

				with open('{}.crop'.format(inputFile), 'w') as f:
					f.write(stderrData)
				printLog('         Video Duration: {}'.format(duration))
				crop = re.findall('crop=(.*?)\n', stderrData)[-1]
				cropList = crop.split(':')
				w = int(cropList[0])
				h = int(cropList[1])

				resolution = w * h / 1024.0
				videoBitrate = ( resolution * ( 2537.0**(1.0/2.5) / resolution**(1.0/2.5) ) ).__round__()
				videoBitrateMax = ( videoBitrate + bitRateVary ).__round__()
				if ( videoBitrate > bitRateVary ):
					videoBitrateMin = ( videoBitrate - bitRateVary ).__round__()
				else:
					videoBitrateMin = 0
				printLog('         Video output {}x{} at {}kb/s'.format(w, h, videoBitrate))

				audioCh = re.findall(' Hz, (.*?),', stderrData)[-1]

				audioBitrate = audioBitrateDict.get(audioCh,'unknown')
				if duration != 'N/A':
					if audioBitrate != 'unknown':
						printLog('         Audio output {} at {}kb/s'.format(audioCh, audioBitrate))
						printLog('         Estimated output size of {}MB at {}kb/s'.format((((videoBitrate + audioBitrate) * durationSec)/(1024 * 8)).__round__(), (videoBitrate + audioBitrate)))
					else:
						printLog('         Audio {} is unknown'.format(audioCh))
						printLog('         Extimated output size of {}MB at {}kb/s (audio not included)\n'.format(((videoBitrate * durationSec)/(1024 * 8)).__round__(), videoBitrate))
				else:
					printLog('         Estimated file size can\'t be calculated since the duration is unknown.')
				timeStartPass1 = int(time.time())
				printLog('         Pass1 Started')
				args = shlex.split('ffmpeg -i {} -pass 1 -passlogfile {}/0pass -vf crop={} -c:v libx264 -preset veryslow -profile high -b:v {}k -maxrate {}k -minrate {}k -an -sn -f rawvideo -y /dev/null'.format(inputFile.__repr__(), inputDir, crop, videoBitrate.__str__(), videoBitrateMax.__str__(), videoBitrateMin.__str__()))
				stderrData = runSubprocess(args)
				timeCompletedPass1 = int(time.time()) - timeStartPass1
				printLog('{} Pass1 completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedPass1)))
				with open('{}.pass1'.format(inputFile), 'w') as f:
					f.write(stderrData)
				timeStartPass2 = int(time.time())
				printLog('         Pass2 Started')
				if 'vorbis' in audioCodec:
					args = shlex.split('ffmpeg -i {} -pass 2 -passlogfile {}/0pass -vf crop={} -c:v libx264 -preset veryslow -profile high -b:v {}k -maxrate {}k -minrate {}k -c:a copy -c:s copy -f matroska -metadata title="{}" {}'.format(inputFile.__repr__(), inputDir, crop, videoBitrate.__str__(), videoBitrateMax.__str__(), videoBitrateMin.__str__(), fileName, outputFilePart.__repr__()))
				else:
					args = shlex.split('ffmpeg -i {} -pass 2 -passlogfile {}/0pass -vf crop={} -c:v libx264 -preset veryslow -profile high -b:v {}k -maxrate {}k -minrate {}k -c:a libvorbis -q:a 3 -c:s copy -f matroska -metadata title="{}" {}'.format(inputFile.__repr__(), inputDir, crop, videoBitrate.__str__(), videoBitrateMax.__str__(), videoBitrateMin.__str__(), fileName, outputFilePart.__repr__()))
				stderrData = runSubprocess(args)
				timeCompletedPass2 = int(time.time()) - timeStartPass2
				printLog('{} Pass2 completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedPass2)))
				with open('{}.pass2'.format(inputFile), 'w') as f:
					f.write(stderrData)
				os.rename(outputFilePart, outputFile)
				timeCompleted = int(time.time())
				timeJobSeconds = timeCompleted - timeStarted
				timeJob = str(datetime.timedelta(seconds=timeJobSeconds))
				printLog('         Completed transcoding in {}\n'.format(timeJob))
