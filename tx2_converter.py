#!/usr/bin/python
import argparse,io,math,operator,os.path,struct,sys,zlib

''' Version 0.1.0
    Only works to convert TX2 in Disgaea PC to PNG or DDS.
    There's some weird blocky-alpha around the BU*.TX2s that needs fixing. '''

class ImageFormatException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Image:
    BigEndian = 'BigEndian'
    LittleEndian = 'LittleEndian'
    DXT1 = 'DXT1'
    DXT5 = 'DXT5'
    RGB888 = 'RGB888'
    BGRA8888 = 'BGRA8888'
    RGBA8888 = 'RGBA8888'
    PRGBA8888I4 = 'PRGBA8888I4'
    PRGBA8888I8 = 'PRGBA8888I8'
    validTypes = [DXT1, DXT5, PRGBA8888I4, PRGBA8888I8, BGRA8888, RGBA8888]
    preMultBlackRGB = bytearray([0, 0, 0])
    @staticmethod
    def makeRGBFrom565Byte(byte):
        r = int(round(((byte >> 11) & 31) * (255 / 31)))
        g = int(round(((byte >> 5) & 63) * (255 / 63)))
        b = int(round((byte & 31) * (255 / 31)))
        return [r, g, b]
    @staticmethod
    def makeAlphaValuesForDXT(a0, a1):
        values = [a0, a1]
        if a0 > a1:
            for i in range(1, 7):
                values.append(int(round((((7 - i) * a0) + (i * a1)) / 7)))
        else:
            for i in range(1, 5):
                values.append(int(round((((5 - i) * a0) + (i * a1)) / 7)))
            values.append(0x00)
            values.append(0xFF)
        return values
    @staticmethod
    def makeColorValuesForDXT(c0, c1):
        c0rgb = Image.makeRGBFrom565Byte(c0)
        c1rgb = Image.makeRGBFrom565Byte(c1)
        values = [bytearray(c0rgb), bytearray(c1rgb)]
        if c0 > c1:
            values.append(bytearray([int(round(n / 3)) for n in map(operator.add, [n * 2 for n in c0rgb], c1rgb)]))
            values.append(bytearray([int(round(n / 3)) for n in map(operator.add, c0rgb, [n * 2 for n in c1rgb])]))
        else:
            values.append(bytearray([int(round(n / 2)) for n in map(operator.add, c0rgb, c1rgb)]))
            values.append(Image.preMultBlackRGB)
        return values
    @classmethod
    def fromImage(cls, image):
        return cls(image.type, image.width, image.height, image.endianness, image.paletteColors, image.imageData, paletteData=image.paletteData)
    def __init__(self, type, width, height, endianness, paletteColors, imageData, paletteData=None):
        if not(type in Image.validTypes):
            raise ImageFormatException('Unknown Image Type')
        if (type == Image.PRGBA8888I4 or type == Image.PRGBA8888I8) and (paletteColors <= 0 or paletteData == None):
            raise ImageFormatException('Paletted Image Type without Palette Data')
        self.type = type
        self.width = width
        self.height = height
        self.endianness = endianness
        self.paletteColors = paletteColors
        self.imageData = imageData
        self.paletteData = paletteData
    def writeFile(self, outputPath):
        raise NotImplementedError()
    def isBigEndian(self):
        return self.endianness == Image.BigEndian
    def isLittleEndian(self):
        return self.endianness == Image.LittleEndian
    def isDXT1(self):
        return self.type == Image.DXT1
    def isDXT3(self):
        return False
    def isDXT5(self):
        return self.type == Image.DXT5
    def isRGB888(self):
        return self.type == Image.RGB888
    def isBGRA8888(self):
        return self.type == Image.BGRA8888
    def isRGBA8888(self):
        return self.type == Image.RGBA8888
    def isPRGBA8888I4(self):
        return self.type == Image.PRGBA8888I4
    def isPRGBA8888I8(self):
        return self.type == Image.PRGBA8888I8
    def changeDXT1toRGB888(self):
        assert self.isDXT1()
        imageData = io.BytesIO(self.imageData)
        rgb888 = bytearray()
        for h in range(0, int(self.height / 4)):
            rows = [[] for n in range(0, 4)]
            for w in range(0, int(self.width / 4)):
                c0,c1 = struct.unpack('<HH', imageData.read(4))
                colorValues = Image.makeColorValuesForDXT(c0, c1)
                colorIndexes, = struct.unpack('<L', imageData.read(4))
                for y in range(0, 4):
                    for x in range(0, 4):
                        i = (3 - x) + (y * 4)
                        row = rows[3 - y]
                        colorIndex = (colorIndexes >> (2 * (15 - i))) & 3
                        row += colorValues[colorIndex]
            for row in rows:
                for n in row:
                    rgb888.append(n)
        self.type = Image.RGB888
        self.imageData = rgb888
    def changeDXT3orDXT5toRGBA8888(self):
        ''' DXT3 is unsupported but this code could handle it '''
        assert self.isDXT5()
        imageData = io.BytesIO(self.imageData)
        rgba8888 = bytearray()
        for h in range(0, int(self.height / 4)):
            rows = [[] for n in range(0, 4)]
            for w in range(0, int(self.width / 4)):
                alphaValues = None
                alphaIndexes = None
                if self.isDXT3():
                    alphaValues, = struct.unpack('<Q', imageData.read(8))
                else:
                    alphaValues = Image.makeAlphaValuesForDXT(*struct.unpack('<BB', imageData.read(2)))
                    alphaIndexes, = struct.unpack('<Q', imageData.read(6) + b'\x00\x00')
                c0,c1 = struct.unpack('<HH', imageData.read(4))
                colorValues = Image.makeColorValuesForDXT(c0, c1)
                colorIndexes, = struct.unpack('<L', imageData.read(4))
                for y in range(0, 4):
                    for x in range(0, 4):
                        i = (3 - x) + (y * 4)
                        row = rows[3 - y]
                        colorIndex = (colorIndexes >> (2 * (15 - i))) & 3
                        row += colorValues[colorIndex]
                        if self.isDXT3():
                            row.append((alphaValues >> (4 * (15 - i)) & 15) * 17)
                        else:
                            alphaIndex = (alphaIndexes >> (3 * (15 - i))) & 7
                            row.append(alphaValues[alphaIndex])
            for row in rows:
                for n in row:
                    rgba8888.append(n)
        self.type = Image.RGBA8888
        self.imageData = rgba8888
    def changeBGRA8888toRGBA8888(self):
        assert self.isBGRA8888()
        imageData = io.BytesIO(self.imageData)
        rgba8888 = bytearray()
        for h in range(0, self.height):
            for w in range(0, self.width):
                bgra = imageData.read(4)
                rgba8888.append(bgra[2])
                rgba8888.append(bgra[1])
                rgba8888.append(bgra[0])
                rgba8888.append(bgra[3])
        self.type = Image.RGBA8888
        self.imageData = rgba8888

class TX2Image(Image):
    typeMap = {
        0: Image.DXT1,
        2: Image.DXT5,
        3: Image.BGRA8888,
        16: Image.PRGBA8888I4,
        256: Image.PRGBA8888I8
    }
    @staticmethod
    def __getPaletteData(file, type, paletteColors):
        if type == Image.PRGBA8888I4 or type == Image.PRGBA8888I8:
            file.seek(16)
            return file.read(paletteColors * 4)
        return None
    @staticmethod
    def __getImageData(file, type, width, height, paletteColors):
        if type == Image.PRGBA8888I4 or type == Image.PRGBA8888I8:
            file.seek(16 + (paletteColors * 4))
        else:
            file.seek(16)
        volume = width * height
        if type == Image.DXT1:
            return file.read(int(volume / 2))
        elif type == Image.DXT5:
            return file.read(volume)
        elif type == Image.BGRA8888:
            return file.read(volume * 4)
        elif type == Image.PRGBA8888I4:
            return file.read(int(volume / 2))
        elif type == Image.PRGBA8888I8:
            return file.read(volume)
        else:
            assert False
    @staticmethod
    def __isValidPow(dim, twoPow):
        powDim = pow(2, twoPow)
        smallerPowDim = twoPow - 1
        dimPow = math.log(dim, 2)
        return dim == powDim or (dimPow < twoPow and dimPow > smallerPowDim)
    @classmethod
    def fromFilePath(cls, filePath):
        file = open(filePath, 'rb')
        file.seek(0)
        width,height,type,widthPow,heightPow,paletteColors,hasPalette,tt = struct.unpack('<HHHBBHHL', file.read(16))
        type = TX2Image.typeMap[type] if type in TX2Image.typeMap else None
        isPaletteType = type == Image.PRGBA8888I4 or type == Image.PRGBA8888I8
        if type == None or tt != 0x10000 or not(TX2Image.__isValidPow(width, widthPow) and TX2Image.__isValidPow(height, heightPow)) or (isPaletteType and (hasPalette == 0 or paletteColors == 0)) or (not(isPaletteType) and hasPalette == 1):
            file.close()
            raise ImageFormatException('Unrecognized TX2 Header: ' + str((type, width, height, widthPow, heightPow, paletteColors, hasPalette, tt)))
        imageData = TX2Image.__getImageData(file, type, width, height, paletteColors)
        paletteData = TX2Image.__getPaletteData(file, type, paletteColors)
        file.close()
        return cls(type, width, height, Image.LittleEndian, paletteColors, imageData, paletteData=paletteData)
    def writeFile(self, outputPath):
        raise NotImplementedError()

class DDSImage(Image):
    typeHeaders = {
        Image.DXT1: struct.pack('<L4s5L', 0x4, b'DXT1', 0, 0, 0, 0, 0),
        Image.DXT5: struct.pack('<L4s5L', 0x4, b'DXT5', 0, 0, 0, 0, 0),
        Image.RGB888: struct.pack('<7L', 0x40, 0, 32, 0xFF0000, 0xFF00, 0xFF, 0),
        Image.BGRA8888: struct.pack('<7L', 0x41, 0, 32, 0xFF, 0xFF00, 0xFF0000, 0xFF000000),
        Image.RGBA8888: struct.pack('<7L', 0x41, 0, 32, 0xFF000000, 0xFF0000, 0xFF00, 0xFF),
        Image.PRGBA8888I4: struct.pack('<7L', 0x8, 0, 4, 0, 0, 0, 0),
        Image.PRGBA8888I8: struct.pack('<7L', 0x20, 0, 8, 0, 0, 0, 0),
    }
    def writeFile(self, outputPath):
        if not(self.type in typeHeaders):
            raise NotImplementedError()
        dds = open(outputPath, 'wb')
        dds.write(b'DDS ' + struct.pack('<7L', 124, 0x81007, self.height, self.width, len(self.imageData), 0, 0))
        dds.write((b'\x00' * (4 * 11)) + struct.pack('<L', 0x20))
        dds.write(DDSImage.typeHeaders[self.type])
        dds.write(struct.pack('<L', 0x1000) + (b'\x00' * (4 * 4)))
        if self.paletteData != None:
            dds.write(self.paletteData)
        dds.write(self.imageData)
        dds.close()

class PNGImage(Image):
    Filter = {'None': 0}
    FilterByteMap = {Filter['None']: 'None'}
    class PNGChunk:
        def __init__(self, name):
            self.name = name.encode()
            self.data = bytearray()
        def addBytes(self, data):
            self.data += data
        def getBytes(self):
            nameAndDataStr = self.name + self.data
            return struct.pack('>L', len(self.data)) + nameAndDataStr + struct.pack('>L', zlib.crc32(nameAndDataStr))
    def getFilteredImageData(self, filterType):
        # Don't support any filtering yet
        assert filterType == PNGImage.Filter['None']
        imageData = bytearray(self.imageData)
        bitsPerPixel = None
        if self.isRGB888():
            bitsPerPixel = 24
        elif self.isRGBA8888():
            bitsPerPixel = 32
        elif self.isPRGBA8888I4():
            bitsPerPixel = 4
            if self.isLittleEndian():
                for i in range(0, len(imageData)):
                    imageData[i] = ((imageData[i] << 4) & 0xF0) | ((imageData[i] >> 4) & 0xF)
        elif self.isPRGBA8888I8():
            bitsPerPixel = 8
        widthPixels = int((self.width * bitsPerPixel) / 8)
        for offset in reversed(range(0, self.height)):
            imageData.insert(offset * widthPixels, 0)
        return imageData
    def writeFile(self, outputPath):
        png = open(outputPath, 'wb')
        png.write(b'\x89PNG\x0D\x0A\x1A\x0A')
        ihdr = PNGImage.PNGChunk('IHDR')
        plte = None
        trns = None
        idat = PNGImage.PNGChunk('IDAT')
        iend = PNGImage.PNGChunk('IEND')
        # Convert uncompatible image types to compatible ones
        if self.isDXT1():
            self.changeDXT1toRGB888()
        elif self.isDXT3() or self.isDXT5():
            self.changeDXT3orDXT5toRGBA8888()
        elif self.isBGRA8888():
            self.changeBGRA8888toRGBA8888()
        if self.isPRGBA8888I4() or self.isPRGBA8888I8():
            # Create chunks for paletted images
            plte = PNGImage.PNGChunk('PLTE')
            trns = PNGImage.PNGChunk('tRNS')
            for p in range(0, int(self.paletteColors / 4) * 4):
                offset = p * 4
                plte.addBytes(self.paletteData[offset:offset + 3])
                trns.addBytes(self.paletteData[offset + 3:offset + 4])
            trns.data = trns.data.rstrip(b'\xFF')
            if len(trns.data) == 0:
                trns = None
        bitDepth = 4 if self.isPRGBA8888I4() else 8
        colorType = 2 if self.isRGB888() else 3 if self.isPRGBA8888I4() or self.isPRGBA8888I8() else 6
        ihdr.addBytes(struct.pack('>LLBBBBB', self.width, self.height, bitDepth, colorType, 0, 0, 0))
        idat.addBytes(zlib.compress(self.getFilteredImageData(PNGImage.Filter['None'])))
        png.write(ihdr.getBytes())
        if plte != None:
            png.write(plte.getBytes())
        if trns != None:
            png.write(trns.getBytes())
        png.write(idat.getBytes())
        png.write(iend.getBytes())
        png.close()

def convertImage(inputType, outputType, filePath):
    inputImage = None
    try:
        if inputType == 'tx2':
            inputImage = TX2Image.fromFilePath(filePath)
        if outputType == 'dds':
            DDSImage.fromImage(inputImage).writeFile(filePath + '.DDS')
        elif outputType == 'png':
            PNGImage.fromImage(inputImage).writeFile(filePath + '.PNG')
    except ImageFormatException as err:
        print(filePath, 'ERROR:', err)

class CaseInsensitiveList(list):
    def __init__(self, *args):
        if len(args) == 1 and type(args[0]) == list:
            items = args[0]
            super().__init__([item.lower() if type(item) == str else item for item in items])
        else:
            super().__init__(*args)
    def __contains__(self, other):
        return super().__contains__(other.lower())

parser = argparse.ArgumentParser(description='Convert TX2s to either DDS or PNG.')
parser.add_argument('-t', '--type', choices=CaseInsensitiveList(['dds', 'png']), default='png', help='the output file format, png by default')
parser.add_argument('files', metavar='F', type=str, nargs='+', help='a file to be converted')
args = parser.parse_args()
for arg in args.files:
    if os.path.isfile(arg):
        convertImage('tx2', args.type, arg)
    else:
        print('Problem loading file:', arg)
