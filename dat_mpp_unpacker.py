#!/usr/bin/python
import os,struct,sys

''' Version 0.0.5
    DAT and MPP unpacker. '''

def unpackMPP(fullPath):
    mpp = open(fullPath, 'rb')
    five1,isNew,unknown1,unknown2,fileSize,dataOffset = struct.unpack('<HHHHLL', mpp.read(16))
    if five1 != 5 or fileSize != os.fstat(mpp.fileno()).st_size or dataOffset <= 0xF:
        print('Invalid header', fullPath)
    else:
        mppFolder = fullPath + ' Files'
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

def unpackPSPFS_V1(file):
    fileCount,unknown1 = struct.unpack('<LL', file.read(8))
    if fileCount <= 0:
        print('Invalid fileCount %d:'.format(fileCount), fullPath)
    else:
        datFolder = fullPath + ' Files'
        if not os.path.exists(datFolder):
            os.mkdir(datFolder)
        fileList = []
        for i in range(0, fileCount):
            name = file.read(44).split(b'\x00')[0].decode()
            size,offset = struct.unpack('<LL', file.read(8))
            fileList.append((name,size,offset))
        fileList.sort(key=lambda tup: tup[2])
        for i in range(0, fileCount):
            fileData = fileList[i]
            file.seek(fileData[2])
            out = open(os.path.join(datFolder, fileData[0]), 'wb')
            out.write(file.read(fileData[1]))
            out.close()

def unpack0x00020000(file, fullPath):
    fileCount,unknown1 = struct.unpack('<LL', file.read(8))
    if fileCount <= 0:
        print('Invalid file count %d:'.format(fileCount), fullPath)
    elif unknown1 != 0x00020000:
        print('Invalid header:', fullPath)
    else:
        fileOffsets = []
        fileSize = os.fstat(file.fileno()).st_size
        dataOffset = struct.unpack('<L', file.read(4))
        for i in range(1, fileCount):
            fileOffsets.append(struct.unpack('<L', file.read(4))[0])
        fileOffsets.append(fileSize)
        filesFolder = fullPath + ' Files'
        if not os.path.exists(filesFolder):
            os.mkdir(filesFolder)
        for i in range(0, fileCount):
            outPiece = open(os.path.join(filesFolder, str(i)), 'wb')
            outPiece.write(file.read(fileOffsets[i] - file.tell()))
            outPiece.close()

def unpackDAT(fullPath):
    dat = open(fullPath, 'rb')
    pspfs_v1 = dat.read(8).decode()
    if pspfs_v1 == 'PSPFS_V1':
        unpackPSPFS_V1(dat)
    else:
        dat.seek(0)
        unpack0x00020000(dat, fullPath)

    dat.close()

for arg in sys.argv[1:]:
    if os.path.isfile(arg):
        fullPath = os.path.abspath(arg)
        if arg.endswith('.DAT'):
            unpackDAT(fullPath)
        elif arg.endswith('.MPP'):
            unpackMPP(fullPath)
        else:
            print('Unknown file extension:', fullPath)
