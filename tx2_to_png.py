#!/usr/bin/python
import operator,os.path,struct,sys,zlib

''' Only works to convert TX2s in Disgaea PC to PNGs.
    There's also some weird blocky-alpha around the BU*.TX2s that needs fixing. '''

class Chunk:
    def __init__(self, name):
        self.name = name
        self.data = bytes()
    def addBytes(self, data):
        self.data += data
    def getBytes(self):
        nameAndDataStr = self.name.encode('ascii') + self.data
        return struct.pack('>L', len(self.data)) + nameAndDataStr + struct.pack('>L', zlib.crc32(nameAndDataStr))

def readBGRAintoRGBA(file, width, height):
    out = bytearray()
    for i in range(0, height):
        out.append(0)
        for j in range(0, width):
            bgra = file.read(4)
            out.append(bgra[2])
            out.append(bgra[1])
            out.append(bgra[0])
            out.append(bgra[3])
    return out

def makeAlphaValues(a0, a1):
    values = [a0, a1]
    if a0 > a1:
        for i in range(1, 7):
            values.append(int(round((((7 - i) * a0) + (i * a1)) / 7)))
    else:
        for i in range(1, 5):
            values.append(int(round((((5 - i) * a0) + (i * a1)) / 7)))
        values.append(0)
        values.append(255)
    return values

def makeRGBFrom565Byte(byte):
    r = int(round(((byte >> 11) & 31) * (255 / 31)))
    g = int(round(((byte >> 5) & 63) * (255 / 63)))
    b = int(round((byte & 31) * (255 / 31)))
    return [r, g, b]

preMultBlack = [0, 0, 0]
def makeColorValues(c0, c1):
    c0rgb = makeRGBFrom565Byte(c0)
    c1rgb = makeRGBFrom565Byte(c1)
    values = [c0rgb, c1rgb]
    if c0 > c1:
        values.append([int(round(n / 3)) for n in map(operator.add, [n * 2 for n in c0rgb], c1rgb)])
        values.append([int(round(n / 3)) for n in map(operator.add, c0rgb, [n * 2 for n in c1rgb])])
    else:
        values.append([int(round(n / 2)) for n in map(operator.add, c0rgb, c1rgb)])
        values.append(preMultBlack)
    return values

def readDXT1(file, width, height):
    out = bytearray()
    for h in range(0, int(height / 4)):
        rows = [[0] for n in range(0, 4)]
        for w in range(0, int(width / 4)):
            color = file.read(8)
            c0,c1 = struct.unpack('<HH', color[:4])
            colorValues = makeColorValues(c0, c1)
            colorIndexes, = struct.unpack('<L', color[4:])
            for y in range(0, 4):
                for x in range(0, 4):
                    i = (3 - x) + (y * 4)
                    row = rows[3 - y]
                    colorIndex = (colorIndexes >> (2 * (15 - i))) & 3
                    colorValue = colorValues[colorIndex]
                    for i in range(0, 3):
                        row.append(colorValue[i])
                    row.append(255)
        for row in rows:
            for n in row:
                out.append(n)
    return out

def readDXT5(file, width, height):
    out = bytearray()
    for h in range(0, int(height / 4)):
        rows = [[0] for n in range(0, 4)]
        for w in range(0, int(width / 4)):
            alpha = file.read(8)
            alphaValues = makeAlphaValues(alpha[0], alpha[1])
            alphaIndexes, = struct.unpack('<Q', alpha[2:] + b'\x00\x00')
            color = file.read(8)
            c0,c1 = struct.unpack('<HH', color[:4])
            colorValues = makeColorValues(c0, c1)
            colorIndexes, = struct.unpack('<L', color[4:])
            for y in range(0, 4):
                for x in range(0, 4):
                    i = (3 - x) + (y * 4)
                    row = rows[3 - y]
                    colorIndex = (colorIndexes >> (2 * (15 - i))) & 3
                    colorValue = colorValues[colorIndex]
                    alphaIndex = (alphaIndexes >> (3 * (15 - i))) & 7
                    row.append(colorValue[0])
                    row.append(colorValue[1])
                    row.append(colorValue[2])
                    row.append(alphaValues[alphaIndex])
        for row in rows:
            for n in row:
                out.append(n)
    return out

def readPaletteAndData(file, width, height, paletteCount):
    out = bytearray()
    palette = []
    for p in range(0, paletteCount):
        rgba = file.read(4)
        palette.append([rgba[0], rgba[1], rgba[2], rgba[3]])
    for h in range(0, height):
        out.append(0)
        rowData = file.read(int(width / 2))
        for w in range(0, int(width / 2)):
            indexes = rowData[w]
            rgba1 = palette[indexes & 15]
            rgba2 = palette[(indexes >> 4) & 15]
            for i in range(0, 4):
                out.append(rgba1[i])
            for i in range(0, 4):
                out.append(rgba2[i])
    return out

def makePNG(fileName):
    tx2 = open(fileName, 'rb')
    width,height,type,unknown1,unknown2,paletteCount,unknown3,one1 = struct.unpack('<HHHBBHLH', tx2.read(16))
    if (one1 != 1 or not(type == 0 or type == 2 or type == 3 or type == 16) or (type == 16 and paletteCount <= 0)):
        print('Unknown Header', fileName, [type, unknown1, unknown2, unknown3, one1])
    else:
        png = open(fileName + '.PNG', 'wb')
        png.write(b'\x89PNG\x0D\x0A\x1A\x0A')
        ihdr = Chunk('IHDR')
        ihdr.addBytes(struct.pack('>LLBBBBB', width, height, 8, 6, 0, 0, 0))
        png.write(ihdr.getBytes())
        idat = Chunk('IDAT')
        if (type == 0):
            idat.addBytes(zlib.compress(readDXT1(tx2, width, height)))
        if (type == 2):
            idat.addBytes(zlib.compress(readDXT5(tx2, width, height)))
        elif (type == 3):
            idat.addBytes(zlib.compress(readBGRAintoRGBA(tx2, width, height)))
        elif (type == 16):
            idat.addBytes(zlib.compress(readPaletteAndData(tx2, width, height, paletteCount)))

        png.write(idat.getBytes())
        iend = Chunk('IEND')
        png.write(iend.getBytes())
        png.close()
    tx2.close()

for arg in sys.argv[1:]:
    if os.path.isfile(arg):
        makePNG(arg)