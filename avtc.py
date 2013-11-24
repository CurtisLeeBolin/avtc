#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  avtc.py
#
#  Copyright 2013 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
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

import os, shlex, subprocess, time, datetime, re, argparse

class AvtcCommon:
	# list of file extentions too search for
	fileExtList = [
		'3g2', '3gp', 'asf', 'avi', 'divx', 'flv', 'm2ts', 'm4a',
		'mj2', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'ogg', 'ogm',
		'ogv', 'rm', 'rmvb', 'vob', 'wmv'
	]

	inputDir = '0in'
	outputDir = '0out'

	# Just estimated bitrates for vorbis for certain channel numbers
	audioBitrateDict = {
		'mono' : 72,
		'stereo' : 112,
		'2' : 112,
		'2 channels' : 112,
		'5.1' : 276,
		'5.1(side)' : 276,
		'7.1' : 640
	}

	bitRateVary = 512.0

	def __init__(self, fileList, workingDir, deinterlace, scale720p):
		self.mkIODirs(workingDir)
		for f in fileList:
			if os.path.isfile(f):
				fileName, fileExtension = os.path.splitext(f)
				if self.checkFileType(fileExtension):
					self.transcode(f, fileName, deinterlace, scale720p)

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
		stderrData = stderrData.decode()
		return stderrData

	def printLog(self, s):
		with open('{}/0transcode.log'.format(self.inputDir), 'a') as f:
			f.write('{}\n'.format(s))
		print(s)

	def mkIODirs(self, workingDir):
		for dir in [self.inputDir, self.outputDir]:
			if not os.path.exists(dir):
				os.mkdir('{}/{}'.format(workingDir, dir), 0o0755)

	def transcode(self, f, fileName, deinterlace, scale720p):
		videoFilterList = []
		if deinterlace:
			videoFilterList.append('yadif=0:-1:0')
		if scale720p:
			videoFilterList.append('scale=1280:-1')
		inputFile  = '{}/{}'.format(self.inputDir, f)
		outputFile = '{}/{}.mkv'.format(self.outputDir, fileName)
		outputFilePart = '{}.part'.format(outputFile)
		os.rename(f, inputFile)

		self.printLog('{} Cropdetect started on {}'.format(time.strftime('%X'), fileName.__repr__()))
		timeStarted = int(time.time())

		args = 'ffmpeg -i {}'.format(inputFile.__repr__())
		stderrData = self.runSubprocess(args)
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

		cropDetectVideoFilterList = list(videoFilterList)
		cropDetectVideoFilterList.append('cropdetect')

		args = 'ffmpeg -i {} -ss {} -t {} -filter:v {} -an -sn -f rawvideo -y {}'.format(inputFile.__repr__(), cropDetectStart, cropDetectDuration, ','.join(cropDetectVideoFilterList), os.devnull)
		stderrData = self.runSubprocess(args)

		timeCompletedCrop = int(time.time()) - timeStarted
		self.printLog('{} Cropdetect completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedCrop)))

		with open('{}.crop'.format(inputFile), 'w') as f:
			f.write(stderrData)
		self.printLog('         Video Duration: {}'.format(duration))
		crop = re.findall('crop=(.*?)\n', stderrData)[-1]
		cropList = crop.split(':')
		w = int(cropList[0])
		h = int(cropList[1])

		videoFilterList.append('crop={}'.format(crop))

		resolution = w * h / 1024.0
		videoBitrate = ( resolution * ( 2537.0**(1.0/2.5) / resolution**(1.0/2.5) ) ).__round__()
		videoBitrateMax = ( videoBitrate + self.bitRateVary ).__round__()
		if ( videoBitrate > self.bitRateVary ):
			videoBitrateMin = ( videoBitrate - self.bitRateVary ).__round__()
		else:
			videoBitrateMin = 0
		self.printLog('         Video output {}x{} estimated at {}kb/s'.format(w, h, videoBitrate))

		audioCh = re.findall(' Hz, (.*?),', stderrData)[-1]

		audioBitrate = self.audioBitrateDict.get(audioCh,'unknown')
		if duration != 'N/A':
			if audioBitrate != 'unknown':
				self.printLog('         Audio output {} estimated at {}kb/s'.format(audioCh, audioBitrate))
				self.printLog('         Estimated output size of {}MB at {}kb/s'.format((((videoBitrate + audioBitrate) * durationSec)/(1024 * 8)).__round__(), (videoBitrate + audioBitrate)))
			else:
				self.printLog('         Audio {} is unknown'.format(audioCh))
				self.printLog('         Extimated output size of {}MB at {}kb/s (audio not included)\n'.format(((videoBitrate * durationSec)/(1024 * 8)).__round__(), videoBitrate))
		else:
			self.printLog('         Estimated file size can\'t be calculated since the duration is unknown.')
		timeStartPass1 = int(time.time())
		self.printLog('         Pass1 Started')
		args = 'ffmpeg -i {} -pass 1 -passlogfile {}/0pass -filter:v {} -c:v libx264 -preset veryslow -profile:v high -b:v {}k -maxrate {}k -minrate {}k -an -sn -f rawvideo -y {}'.format(inputFile.__repr__(), self.inputDir, ','.join(videoFilterList), videoBitrate.__str__(), videoBitrateMax.__str__(), videoBitrateMin.__str__(), os.devnull)
		stderrData = self.runSubprocess(args)
		timeCompletedPass1 = int(time.time()) - timeStartPass1
		self.printLog('{} Pass1 completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedPass1)))
		with open('{}.pass1'.format(inputFile), 'w') as f:
			f.write(stderrData)
		timeStartPass2 = int(time.time())
		self.printLog('         Pass2 Started')
		if 'vorbis' in audioCodec:
			args = 'ffmpeg -i {} -pass 2 -passlogfile {}/0pass -filter:v {} -c:v libx264 -preset veryslow -profile:v high -b:v {}k -maxrate {}k -minrate {}k -c:a copy -c:s copy -f matroska -metadata title="{}" -y {}'.format(inputFile.__repr__(), self.inputDir, ','.join(videoFilterList), videoBitrate.__str__(), videoBitrateMax.__str__(), videoBitrateMin.__str__(), fileName, outputFilePart.__repr__())
		else:
			args = 'ffmpeg -i {} -pass 2 -passlogfile {}/0pass -filter:v {} -c:v libx264 -preset veryslow -profile:v high -b:v {}k -maxrate {}k -minrate {}k -c:a libvorbis -q:a 3 -c:s copy -f matroska -metadata title="{}" -y {}'.format(inputFile.__repr__(), self.inputDir, ','.join(videoFilterList), videoBitrate.__str__(), videoBitrateMax.__str__(), videoBitrateMin.__str__(), fileName, outputFilePart.__repr__())
		stderrData = self.runSubprocess(args)
		timeCompletedPass2 = int(time.time()) - timeStartPass2
		self.printLog('{} Pass2 completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedPass2)))
		with open('{}.pass2'.format(inputFile), 'w') as f:
			f.write(stderrData)
		os.rename(outputFilePart, outputFile)
		timeCompleted = int(time.time())
		timeJobSeconds = timeCompleted - timeStarted
		timeJob = str(datetime.timedelta(seconds=timeJobSeconds))
		self.printLog('         Completed transcoding in {}\n'.format(timeJob))

if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		prog='avtc.py',
		description='Audio Video Transcoder',
		epilog='Copyright 2013 Curtis lee Bolin <CurtisLeeBolin@gmail.com>')
	parser.add_argument('-f', '--filelist',
		dest='fileList',
		help='A comma separated list of files in the current directory')
	parser.add_argument('-d', '--directory',
		dest='directory',
		help='A directory')
	parser.add_argument('--deinterlace',
		help='Deinterlace Videos.',
		action="store_true")
	parser.add_argument('--scale720p',
		help='Scale Videos to 720p.',
		action="store_true")
	args = parser.parse_args()

	if (args.fileList and args.directory):
		print('Arguments -f (--filelist) and -d (--directory) can not be used together.')
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

	AvtcCommon(fileList, workingDir, args.deinterlace, args.scale720p)
