#!/usr/bin/python
import os,struct,sys

''' Version 0.1.0
    ARC, DAT and MPP unpacker. '''

class FileBundle:
    def __init__(self):
        self.files = []
    def addFiles(self):
        raise NotImplementedError()
    def extractFiles(self, outputFolder):
        if not os.path.exists(outputFolder):
            os.mkdir(outputFolder)

class FileBundleWithSizes(FileBundle):
    def addFile(self, fileName, fileStart, fileSize):
        self.files.append({'fileName': fileName, 'fileStart': fileStart, 'fileSize': fileSize})
    def extractFiles(self, outputFolder, inputFile):
        super().extractFiles(outputFolder)
        for fileData in self.files:
            inputFile.seek(fileData['fileStart'])
            outputFile = open(os.path.join(outputFolder, fileData['fileName']), 'wb')
            outputFile.write(inputFile.read(fileData['fileSize']))
            outputFile.close()

class FileBundleWithOffsets(FileBundle):
    def addFile(self, fileName, fileStart):
        self.files.append({'fileName': fileName, 'fileStart': fileStart})
    def extractFiles(self, outputFolder, inputFile):
        super().extractFiles(outputFolder)
        fileSize = os.fstat(inputFile.fileno()).st_size
        for i in range(0, len(self.files)):
            fileData = self.files[i]
            fileEnd = fileSize if (i == len(self.files) - 1) else self.files[i + 1]['fileStart']
            inputFile.seek(fileData['fileStart'])
            outputFile = open(os.path.join(outputFolder, fileData['fileName']), 'wb')
            outputFile.write(inputFile.read(fileEnd - fileData['fileStart']))
            outputFile.close()

def unpackMPP(filePath):
    mpp = open(filePath, 'rb')
    u1,isNew,unknown1,unknown2,fileSize,dataOffset = struct.unpack('<HHHHLL', mpp.read(16))
    if fileSize != os.fstat(mpp.fileno()).st_size or dataOffset <= 0xF:
        print('Invalid header', filePath)
    else:
        fileBundle = FileBundleWithOffsets()
        fileBundle.addFile('0', dataOffset)
        i = 1
        while mpp.tell() < dataOffset:
            fileOffset, = struct.unpack('<L', mpp.read(4))
            if fileOffset == 0:
                break
            fileBundle.addFile(str(i), fileOffset)
            i += 1
        fileBundle.extractFiles(filePath + ' Files', mpp)
    mpp.close()

def unpackPSPFS_V1(file, filePath):
    fileCount,unknown1 = struct.unpack('<LL', file.read(8))
    if fileCount == 0:
        print('Invalid fileCount %d:'.format(fileCount), filePath)
    else:
        fileBundle = FileBundleWithSizes()
        for i in range(0, fileCount):
            name = file.read(44).split(b'\x00')[0].decode()
            size,offset = struct.unpack('<LL', file.read(8))
            fileBundle.addFile(name, offset, size)
        fileBundle.extractFiles(filePath + ' Files', file)

def unpack0x00020000(file, filePath):
    fileCount,unknown1 = struct.unpack('<LL', file.read(8))
    if fileCount == 0:
        print('Invalid file count %d:'.format(fileCount), filePath)
    elif unknown1 != 0x00020000:
        print('Invalid header:', filePath)
    else:
        fileBundle = FileBundleWithOffsets()
        for i in range(0, fileCount):
            fileBundle.addFile(str(i), struct.unpack('<L', file.read(4))[0])
        fileBundle.extractFiles(filePath + ' Files', file)

def unpackDAT(filePath):
    dat = open(filePath, 'rb')
    if dat.read(8).decode() == 'PSPFS_V1':
        unpackPSPFS_V1(dat, filePath)
    else:
        dat.seek(0)
        unpack0x00020000(dat, filePath)
    dat.close()

def unpackARC(filePath):
    arc = open(filePath, 'rb')
    dsarcidx,fileCount,unknown1 = struct.unpack('<8sLL', arc.read(16))
    if dsarcidx.decode() != 'DSARCIDX' or unknown1 != 0:
        print('Invalid header:', filePath)
    elif fileCount == 0:
        print('Invalid file count %d:'.format(fileCount), filePath)
    else:
        arc.seek(int((0x1F + (fileCount * 2)) / 0x10) * 0x10)
        fileBundle = FileBundleWithSizes()
        for i in range(0, fileCount):
            name = arc.read(40).split(b'\x00')[0].decode()
            size,offset = struct.unpack('<LL', arc.read(8))
            fileBundle.addFile(name, offset, size)
        fileBundle.extractFiles(filePath + ' Files', arc)
    arc.close()

for arg in sys.argv[1:]:
    if os.path.isfile(arg):
        if arg.endswith('.ARC'):
            unpackARC(arg)
        elif arg.endswith('.DAT'):
            unpackDAT(arg)
        elif arg.endswith('.MPP'):
            unpackMPP(arg)
        else:
            print('Unknown file extension:', arg)
    else:
        print('File not accessible:', arg)
