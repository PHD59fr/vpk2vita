#!/usr/bin/python

from Struct 	import Struct
import ConfigParser
import math
import ntpath
import os
import random
import struct
import sys
import time
import zipfile

SFO_MAGIC  = 0x46535000
SFO_STRING = 2
SFO_INT    = 4

def nullterm(str_plus):
    z = str_plus.find('\0')
    if z != -1:
        return str_plus[:z]
    else:
        return str_plus
class bcolors:
    PINK 	= '\033[95m'
    BLUE 	= '\033[94m'
    GREEN 	= '\033[92m'
    YELLOW 	= '\033[93m'
    RED 	= '\033[91m'
    ENDC 	= '\033[0m'
    BOLD 	= '\033[1m'
    UNDERLINE 	= '\033[4m'

class Header(Struct):
    __endian__ = Struct.LE
    def __format__(self):
        self.magic = Struct.uint32
        self.unk1 = Struct.uint32
        self.KeyOffset = Struct.uint32
        self.ValueOffset = Struct.uint32
        self.PairCount = Struct.uint32
    def __str__(self):
        out  = ""
        out += "[X] Magic: %08x\n" % self.magic
        out += "[ ] Unk1: %08x\n" % self.unk1
        out += "[X] Key Offset: %08x\n" % self.KeyOffset
        out += "[X] Value Offset: %08x\n" % self.ValueOffset
        out += "[X] Pair Count: %08x" % self.PairCount
        return out

class Entry(Struct):
    __endian__ = Struct.LE
    def __format__(self):
        self.key_off    = Struct.uint16
        self.unk1       = Struct.uint8
        self.value_type = Struct.uint8
        self.value_len  = Struct.uint32
        self.padded_len = Struct.uint32
        self.value_off  = Struct.uint32

    def __str__(self):
        out  = ""
        out += "[X] Key Offset: %04x\n" % self.key_off
        out += "[ ] Unk1: %02x\n" % self.unk1
        out += "[/] Value Type: %02x\n" % self.value_type
        out += "[X] Value Length: %08x\n" % self.value_len
        out += "[X] Padded Length: %08x\n" % self.padded_len
        out += "[X] Value Offset: %08x" % self.value_off
        return out

    def PrettyPrint(self, data, key_off, value_off):
        out  = ""
        out += "[X] Key: '%s'[%04x]\n" % (nullterm(data[self.key_off + key_off:]), self.key_off)
        out += "[/] Unk: %02x\n" % (self.unk1)
        out += "[/] Value Type: %02x\n" % self.value_type
        out += "[X] Value Length: %08x\n" % self.value_len
        out += "[X] Padded Length: %08x\n" % self.padded_len
        out += "[X] Value Offset: %08x" % self.value_off
        if self.value_type == SFO_STRING:
            out += "[X] Value: '%s'[%08x]" % (nullterm(data[self.value_off + value_off:]), self.value_off+value_off)
        elif self.value_type == SFO_INT:
            out += "[X] Value: %d[%08x]" % (struct.unpack('<I', data[self.value_off + value_off:self.value_off + value_off + 4])[0], self.value_off+value_off)
        else:
            out += "[X] Value Type Unknown"
        return out

def convertSize(size):
   if (size == 0):
       return '0B'
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = round(size/p,2)
   return '%s %s' % (s,size_name[i])

def readSFO(data):
    global pretty
    stuff = {}
    offset = 0
    header = Header()
    header.unpack(data[offset:offset+len(header)])
    assert header.magic == SFO_MAGIC
    assert header.unk1 == 0x00000101
    offset += len(header)
    off1 = header.KeyOffset
    off2 = header.ValueOffset
    for x in xrange(header.PairCount):
        entry = Entry()
        entry.unpack(data[offset:offset+len(entry)])
        key = nullterm(data[off1+entry.key_off:])
        if entry.value_type == SFO_STRING:
                value = nullterm(data[off2+entry.value_off:])
        else:
                value = struct.unpack('<I', data[entry.value_off + off2:entry.value_off + off2 + 4])[0]
        stuff[key] = value
        offset += len(entry)
    return stuff

def runApp():
    args        = sys.argv[1:]
    if len(args) == 0:
        print bcolors.RED + "No file selected" + bcolors.ENDC
        print bcolors.GREEN + "Usage: " + sys.argv[0] + " file.vpk file2.vpk file3.vpk OR " + sys.argv[0] + " *.vpk" + bcolors.ENDC
        print "Exiting App ..."
        sys.exit(0)
    gameList = {}
    for file in args:
        file_extension = os.path.splitext(file)[1]
        if ( file_extension.lower() != ".vpk" ):
            continue
        print "##################################################################"
        print bcolors.YELLOW + "File \"" + ntpath.basename(file) + "\""+ bcolors.ENDC
        print "##################################################################"
        vpk 		= zipfile.ZipFile(file, 'r')
        vpkInfoData 	= vpk.read('sce_sys/param.sfo')
        vpkInfo 	= readSFO(vpkInfoData)
        fileInfo 	= os.stat(file)
        fileSize 	= fileInfo.st_size
        print "Title:			" 	+ vpkInfo['TITLE']
        print "Installation Directory:	" 	+ "ux0://app/" + vpkInfo['TITLE_ID']
        print "Size:			"	+ convertSize(fileSize)
        print "Version:		" 		+ vpkInfo['VERSION']
        print "Min FW PSVITA Version:	" 	+ vpkInfo['PSP2_DISP_VER']
        print "##################################################################"
        raw_input("Press any key for continue or ctl+c for cancel")
        gameList[file] = vpkInfo['TITLE']
        print "\n"
    if not (gameList):
        print bcolors.RED + "No file found" + bcolors.ENDC
        print "Exiting App ..."
        sys.exit(0)
    print bcolors.YELLOW + "Loading Configuration (config.cfg)..." + bcolors.ENDC
    try:
        config      = ConfigParser.ConfigParser()
        config.read("config.cfg")
        psVitaIp    = config.get("PSVITA","ip")
        psVitaPort  = config.get("PSVITA","port")
    except:
        print bcolors.RED + "Error in config.cfg" + bcolors.ENDC
        print(config.get("PSVITA","ip"))
        print "Exiting App ..."
    print bcolors.YELLOW + "PSVITA IP:              " + psVitaIp + bcolors.ENDC
    print bcolors.YELLOW + "PSVITA PORT:            " + psVitaPort + bcolors.ENDC

    print bcolors.BLUE + "\n[Extract and upload File Content]" + bcolors.ENDC
    for filename,name in gameList.items():
        print "Processing file for [" +name+ "] ..."
        z = zipfile.ZipFile(filename, allowZip64=True)
        uncompress_size = sum(file.file_size for file in z.infolist())
        extracted_size = 0
        for file in z.infolist():
            extracted_size += file.file_size
            sys.stdout.write("Extract file for [" +name+ "] ... %s %%\r" % (extracted_size * 100/uncompress_size))
            if ((extracted_size/uncompress_size) != 1 ):
                sys.stdout.flush()
            z.extract(file, name)
        print "Extract file for [" +name+ "] ... done!"
        ##TODO##
        print "Files for ["+name+"] is unpacked, uploading ... done!"
        print name,"is uploaded on your VITA, you can now run this APP"


if __name__ == '__main__':
    try:
        runApp()
    except KeyboardInterrupt:
        print "\nExiting App ..."
        sys.exit(0)
