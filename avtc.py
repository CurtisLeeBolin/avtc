#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  avtc.py
#
#  Copyright 2013-2015 Curtis Lee Bolin <CurtisLeeBolin@gmail.com>
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
		'm4v', 'mj2', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'nuv',
		'ogg', 'ogm', 'ogv', 'rm', 'rmvb', 'vob', 'webm', 'wmv'
	]

	inputDir = '0in'
	outputDir = '0out'
	logDir = '0log'

	def __init__(self, fileList, workingDir, deinterlace=False, scale720p=False):
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
		if not stdoutData is None:
			stdoutData = stdoutData.decode(encoding='utf-8', errors='ignore')
		if not stderrData is None:
			stderrData = stderrData.decode(encoding='utf-8', errors='ignore')
		return {'stdoutData': stdoutData, 'stderrData': stderrData, 'returncode': p.returncode}

	def printLog(self, s):
		with open('{}/0transcode.log'.format(self.logDir), 'a', encoding='utf-8') as f:
			f.write('{}\n'.format(s))
		print(s)

	def mkIODirs(self, workingDir):
		for dir in [self.inputDir, self.outputDir, self.logDir]:
			if not os.path.exists(dir):
				os.mkdir('{}/{}'.format(workingDir, dir), 0o0755)

	def transcode(self, f, fileName, deinterlace, scale720p):
		inputFile  = '{}/{}'.format(self.inputDir, f)
		outputFile = '{}/{}.mkv'.format(self.outputDir, fileName)
		outputFilePart = '{}.part'.format(outputFile)
		logFile  = '{}/{}'.format(self.logDir, f)
		timeSpace = '        '
		os.rename(f, inputFile)

		self.printLog('{} Analyzing {}'.format(time.strftime('%X'), fileName.__repr__()))
		timeStarted = int(time.time())

		args = 'ffmpeg -i {}'.format(inputFile.__repr__())
		subprocessDict = self.runSubprocess(args)
		duration = re.findall('Duration: (.*?),', subprocessDict['stderrData'])[-1]
		audioCodecList = re.findall('Audio: (.*?),', subprocessDict['stderrData'])
		if audioCodecList:
			audioCodec = audioCodecList[-1]
		else:
			audioCodec = ''
		durationList = duration.split(':')
		resolution = re.findall('Video: .*? (\d\d+x\d+)', subprocessDict['stderrData'])[0]
		if resolution[-1] == ',':
			resolution = resolution[:-1]
		resolutionList = resolution.split('x')
		input_w = int(resolutionList[0])
		input_h = int(resolutionList[1])

		videoFilterList = []
		if deinterlace:
			videoFilterList.append('yadif=0:-1:0')
		if scale720p:
			if input_w > 1280 or input_h > 720:
				videoFilterList.append('scale=1280:-1')
				self.printLog('{} Above 720p: Scaling Enabled'.format(timeSpace))
			else:
				self.printLog('{} Not Above 720p: Scaling Disabled'.format(timeSpace))

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
		subprocessDict = self.runSubprocess(args)

		timeCompletedCrop = int(time.time()) - timeStarted
		self.printLog('{} Analysis completed in {}'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedCrop)))

		with open('{}.crop'.format(logFile), 'w', encoding='utf-8') as f:
			f.write('{}\n\n{}'.format(args, subprocessDict['stderrData']))
		self.printLog('{} Duration: {}'.format(timeSpace,duration))
		crop = re.findall('crop=(.*?)\n', subprocessDict['stderrData'])[-1]
		cropList = crop.split(':')
		w = int(cropList[0])
		h = int(cropList[1])

		self.printLog('{} Input  Resolution: {}x{}'.format(timeSpace, input_w, input_h))
		self.printLog('{} Output Resolution: {}x{}'.format(timeSpace,w, h))

		videoFilterList.append('crop={}'.format(crop))

		timeStartTranscoding = int(time.time())
		self.printLog('{} Transcoding Started'.format(timeSpace))
		if 'vorbis' in audioCodec:
			args = 'ffmpeg -i {0} -filter:v {1} -c:a copy -metadata title={2} -y -f matroska {3}'.format(inputFile.__repr__(), ','.join(videoFilterList), fileName.__repr__(), outputFilePart.__repr__())
			subprocessDict = self.runSubprocess(args)
			if subprocessDict['returncode'] != 0:
				args = 'ffmpeg -i {0} -filter:v {1} -c:a copy -sn -metadata title={2} -y -f matroska {3}'.format(inputFile.__repr__(), ','.join(videoFilterList), fileName.__repr__(), outputFilePart.__repr__())
				subprocessDict = self.runSubprocess(args)

		else:
			args = 'ffmpeg -i {0} -filter:v {1} -metadata title={2} -y -f matroska {3}'.format(inputFile.__repr__(), ','.join(videoFilterList), fileName.__repr__(), outputFilePart.__repr__())
			subprocessDict = self.runSubprocess(args)
			if subprocessDict['returncode'] != 0:
				args = 'ffmpeg -i {0} -filter:v {1} -sn -metadata title={2} -y -f matroska {3}'.format(inputFile.__repr__(), ','.join(videoFilterList), fileName.__repr__(), outputFilePart.__repr__())
				subprocessDict = self.runSubprocess(args)

		timeCompletedTranscoding = int(time.time()) - timeStartTranscoding
		self.printLog('{} Transcoding completed in {}\n'.format(time.strftime('%X'), datetime.timedelta(seconds=timeCompletedTranscoding)))
		with open('{}.transcode'.format(logFile), 'w', encoding='utf-8') as f:
			f.write('{}\n\n{}'.format(args, subprocessDict['stderrData']))
		os.rename(outputFilePart, outputFile)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		prog='avtc.py',
		description='Audio Video Transcoder',
		epilog='Copyright 2013-2015 Curtis lee Bolin <CurtisLeeBolin@gmail.com>')
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
		fileList = args.fileList.split(',')
	elif (args.directory):
		workingDir = args.directory
		fileList = os.listdir(workingDir)
		fileList.sort()
	else:
		workingDir = os.getcwd()
		fileList = os.listdir(workingDir)
		fileList.sort()

	AvtcCommon(fileList, workingDir, args.deinterlace, args.scale720p)
