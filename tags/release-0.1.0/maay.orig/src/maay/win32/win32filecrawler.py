"""
  This modules contains the functions to crawl the user filesystem.
""" 

import win32api
import win32file
import win32con

import os
import os.path
import stat

PUBLISHED_INDEXATION = 0
PRIVATE_INDEXATION = 1
CACHED_INDEXATION = 2

def lexico_sort(a, b):
    A = a.upper()
    B = b.upper()
    if A > B:
        return 1
    if A < B:
        return -1
    return 0

def getDefaultIndexableRootDirectories():
    directories = [ ]

    drives = win32api.GetLogicalDriveStrings().split("\x00")
    for drive in drives:
        if win32file.GetDriveType(drive) == win32file.DRIVE_FIXED:
            directories.append(drive)
    return directories

def getAllIndexableRootDirectories():
    directories = [ ]

    drives = win32api.GetLogicalDriveStrings().split("\x00")
    for drive in drives:
        directories.append(drive)
    return directories


def isIncluding(directory, directories):
    for d in directories:
        if d.upper().find(directory.upper()) == 0:
            return True
    return False

def isIncluded(directory, directories):
    for d in directories:
        if directory.upper().find(d.upper()) == 0:
            return True
    return False

class FileCrawler:
    def __init__(self, indexedDirectories, notIndexedDirectories, publishedDirectories, notPublishedDirectories, temporaryDirectories, cachedDirectories, indexationType, isIndexableFunction):
        self.__indexationType = indexationType
        self.__indexedDirectories = indexedDirectories
        self.__indexedDirectories.sort(lexico_sort)
        self.__notIndexedDirectories = notIndexedDirectories
        self.__publishedDirectories = publishedDirectories
        self.__publishedDirectories.sort(lexico_sort)
        self.__notPublishedDirectories = notPublishedDirectories
        self.__isIndexableFunction = isIndexableFunction

        self.__temporaryDirectories = temporaryDirectories
        self.__cachedDirectories = cachedDirectories

        self.__files = None
        self.__path = None

        self.reset()

    def setIndexedDirectories(self, indexedDirectories):
        self.__indexedDirectories = indexedDirectories

    def setNotIndexedDirectories(self, notIndexedDirectories):
        self.__notIndexedDirectories = notIndexedDirectories

    def setPublishedDirectories(self, publishedDirectories):
        self.__publishedDirectories = publishedDirectories

    def setNotPublishedDirectories(self, notPublishedDirectories):
        self.__notPublishedDirectories = notPublishedDirectories

    def reset(self):
        if self.__indexationType == PUBLISHED_INDEXATION:
            self.__files = [ self.__publishedDirectories ]
        else:
            self.__files = [ self.__indexedDirectories ]


        self.__path = [ 0 ]

    def getNextFilename(self):
        while 1:
            depth = len(self.__path)
            if depth == 0:
                return None

            index = self.__path[depth - 1]
            
            if index >= len(self.__files[depth - 1]):
                # backtrack
                del self.__path[depth - 1]
                del self.__files[depth - 1]
                depth -= 1
                if depth > 0:
                    self.__path[depth - 1] += 1

                continue

            filename = self.__files[depth - 1][index]

            current_filename = ""
            for i in xrange(depth):
                current_filename = os.path.join(current_filename, self.__files[i][self.__path[i]])

            try:
                mode = os.lstat(current_filename)[stat.ST_MODE]
            except:
                self.__path[depth-1] += 1
                continue


            if stat.S_ISDIR(mode):
                files = []
                try:
                    filenames = os.listdir(current_filename)
                except:
                    filenames = []
                    
#                               filenames.sort(lexico_sort)
                for fn in filenames:
                    try:

                        absolute_fn = os.path.join(current_filename, fn)

                        mode_fn = os.lstat(absolute_fn)[stat.ST_MODE]
                        if not stat.S_ISDIR(mode_fn) and not self.__isIndexableFunction(absolute_fn):
                            continue
                        if not isIncluded(absolute_fn, self.__indexedDirectories):
                            continue                                                        

                        if isIncluded(absolute_fn, self.__notIndexedDirectories):
                            continue                                                        

                        if isIncluded(absolute_fn, self.__cachedDirectories):
                            continue                                                        

                        if isIncluded(absolute_fn, self.__temporaryDirectories):
                            continue                                                        

                        if self.__indexationType == PRIVATE_INDEXATION and isIncluded(absolute_fn, self.__publishedDirectories) and isIncluding(absolute_fn, self.__notPublishedDirectories):
                            continue                                                        

                        if self.__indexationType == PUBLISHED_INDEXATION:
                            if not isIncluded(absolute_fn, self.__publishedDirectories):
                                continue
                        if isIncluded(absolute_fn, self.__notPublishedDirectories):
                            continue

                        attr = win32api.GetFileAttributes(absolute_fn)
                        if attr & win32con.FILE_ATTRIBUTE_HIDDEN:
                            continue
                    except:
                        continue


                    files.append(fn)

                self.__files.append(files)      
                self.__path.append(0)
            elif stat.S_ISREG(mode):
                self.__path[depth-1] += 1
                return current_filename
        
