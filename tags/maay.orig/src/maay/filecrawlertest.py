import unittest

from filecrawler import FileCrawler

import os
from sets import Set



class FileTree:
    """ 
    a file tree determined by a list of filename specs:

    fileList = [ 
                    "foo/bar/somefile", 
                    "anotherfile", 
                    "baz/yetanotherfile" ],
    yields: 

        <ftroot>/
            foo/
                bar/
                    somefile
            anotherfile
            baz/
                yetanotherfile

    the top directories are those directly under <ftroot>, i.e.: 
    ["<ftroot>/foo", "<ftroot>/baz"]. All paths are os-normalised.
    """
    def __init__ (self, fileList):
        self.root = os.tmpnam () + os.path.sep
        # normalise file paths and prepend root dir
        fileListRelative = map (os.path.normpath, fileList)
        fileListRelative.sort ()
        self.fileList = [(self.root + p) for p in fileListRelative]
        # directory tree
        self.dirList = list (Set (map (os.path.dirname, self.fileList)))
        for d in self.dirList:
            try:
                os.makedirs (d)
            except OSError:
                pass
        # files
        for name in self.fileList:
            f = file (name, "w")
            f.close ()
        # tree top dirs
        def getTop (name):
            dir = os.path.dirname (name)
            if dir: 
                return dir.split (os.path.sep)[0]
            else: 
                return None
        topDirSet = Set (map (getTop, fileListRelative)) - Set ([None])
        self.topDirs = [(self.root + p) for p in topDirSet]

    def __del__ (self):
        """ remove file tree """
        for f in self.fileList:
            os.remove (f)
        self.dirList.reverse () # depth-first
        for d in self.dirList:
            try:
                os.removedirs (d)
            except OSError:
                pass

    def getRoot (self):
        """ tree root """
        return self.root

    def getTopDirs (self):
        """ absolute path of the tree's top dirs """
        return self.topDirs

    def getFiles (self):
        """ absolute file path names """
        return self.fileList

#######################################################################
#
#   Test Cases:
#
#######################################################################

class CrawlerTestCase (unittest.TestCase):
    """ file system crawler on a fake file tree """
    # tree description, see class FileTree
    __files = [ "a/foo", "b/bar", "c/cc/baz" ]

    def setUp (self):
        self.tree = FileTree (self.__files)

    def tearDown (self):
        del (self.tree)

    def testCall (self):
        """ call """
        c = FileCrawler (
                            trees = self.tree.getTopDirs (),
                            filterPaths = [],
                            filterFunc = lambda a: True)
        c = FileCrawler (self.tree.getTopDirs (), [], lambda a: True)
        l = list (c)

    def testWrongArgs (self):
        """ reject relative paths """
        self.assertRaises (ValueError, FileCrawler, ["tmp/foo"])
        self.assertRaises (ValueError, FileCrawler, ["/tmp"], ["foo"])

    def testSimpleCrawl (self):
        """ results of a simple crawl """
        c = FileCrawler (self.tree.getTopDirs ())
        self.assertEqual (Set (c), Set (self.tree.getFiles ()))


class FilterFuncCrawlerTestCase (CrawlerTestCase):
    """ filter function """

    __files = [ "a/aa/foo", "a/aa/bar", "a/baz" ]

    def testFilterFunc (self):
        filterFunc = lambda name: name.find ("aa") == -1
        c = FileCrawler (self.tree.getTopDirs (), [], filterFunc)
        fileList = filter (filterFunc, self.tree.getFiles ())
        self.assertEqual (Set (c), Set (fileList))

class FilterPathCrawlerTestCase (CrawlerTestCase):
    """ filter paths """
    
    __files = [ 
                "a/aa/aafile", 
                "a/ab/abfile", 
                "a/aa/aaa/aaafile", 
                "b/aa/aafile",
                "b/bb/bbfile"
              ]
    __filters = [ "a/ab", "b/aa/aafile", "b/bb" ]
    
    def testFilterPath (self):
        """ filter paths """
        root = self.tree.getRoot ()
        filters = [(root + os.path.normpath (p)) for p in self.__filters]
        c = FileCrawler (self.tree.getTopDirs (), filters)
        fileList = self.tree.getFiles ()
        for e in filters:
            fileList = filter (lambda path: path.find (e) == -1, fileList)
        self.assertEqual (Set (c), Set (fileList))

    def testFilterPathRoot (self):
        """ root in filter paths """
        excludes = [self.tree.getTopDirs ()[0]]
        c = FileCrawler (self.tree.getTopDirs (), excludes)
        fileList = self.tree.getFiles ()
        for e in excludes:
            fileList = filter (lambda path: path.find (e) == -1, fileList)
        self.assertEqual (Set (c), Set (fileList))

    def testNullTree (self):
        """ trees == filter paths """
        topdirs = self.tree.getTopDirs ()
        c = FileCrawler (topdirs, topdirs)
        self.assertEqual (Set (c), Set ([]))




if __name__ == '__main__':
    unittest.main()
    
