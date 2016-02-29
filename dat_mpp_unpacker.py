#!/usr/bin/python
import os,struct,sys

''' Version 0.0.1
    DAT and MPP unpacker. '''

def unpackMPP(fileName):
    mpp = open(fileName, 'rb')
    five1,isNew,unknown1,unknown2,fileSize,dataOffset = struct.unpack('<HHHHLL', mpp.read(16))
    if five1 != 5 or fileSize != os.fstat(mpp.fileno()).st_size or dataOffset <= 0xF:
        print('Invalid header', fileName)
    else:
        fileDir = os.path.dirname(os.path.realpath(fileName))
        mppFolder = os.path.join(fileDir, fileName + ' Files')
        if not os.path.exists(mppFolder):
            os.mkdir(mppFolder)
        fileOffsets = []
        while mpp.tell() < dataOffset:
            fileOffset, = struct.unpack('<L', mpp.read(4))
            if fileOffset == 0:
                mpp.seek(dataOffset)
                break
            fileOffsets.append(fileOffset)
        fileOffsets.append(fileSize)
        for i in range(0, len(fileOffsets)):
            outPiece = open(os.path.join(mppFolder, str(i)), 'wb')
            outPiece.write(mpp.read(fileOffsets[i] - mpp.tell()))
            outPiece.close()
    mpp.close()

def unpackDAT(fileName):
    dat = open(fileName, 'rb')
    pspfs_v1 = dat.read(8).decode()
    fileCount,unknown1 = struct.unpack('<LL', dat.read(8))
    if pspfs_v1 != 'PSPFS_V1' or fileCount <= 0:
        print('Invalid header', fileName)
    else:
        fileDir = os.path.dirname(os.path.realpath(fileName))
        datFolder = os.path.join(fileDir, fileName + ' Files')
        if not os.path.exists(datFolder):
            os.mkdir(datFolder)
        fileList = []
        for i in range(0, fileCount):
            name = dat.read(44).split(b'\x00')[0].decode()
            size,offset = struct.unpack('<LL', dat.read(8))
            fileList.append((name,size,offset))
        fileList.sort(key=lambda tup: tup[2])
        for i in range(0, fileCount):
            fileData = fileList[i]
            dat.seek(fileData[2])
            out = open(os.path.join(datFolder, fileData[0]), 'wb')
            out.write(dat.read(fileData[1]))
            out.close()
    dat.close()

for arg in sys.argv[1:]:
    if os.path.isfile(arg):
        if arg.endswith('.DAT'):
            unpackDAT(arg)
        elif arg.endswith('.MPP'):
            unpackMPP(arg)
        else:
            print('Unknown file extension:', os.path.dirname(os.path.realpath(arg)))