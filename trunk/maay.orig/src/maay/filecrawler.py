import os
from sets import Set          


class NullIterator:
    """ null iterator; stop immediately """
    def next (self):
        raise StopIteration


class FileCrawler:
    """
    breadth-first file iterator

    Tree lists are walked iteratively, yielding absolute file paths. An
    optional list of filter paths specifies base paths excluded from the
    result set. An optional filter function serves the same purpose, akin to
    the first argument of the "filter" built-in.
    """
    def __init__ (self, trees, filterPaths = [], filterFunc = lambda a: True):
        def normPath (p):
            if p[0] != os.path.sep: raise ValueError, "paths must be absolute"
            return os.path.normpath (p)

        filterPaths = map (normPath, filterPaths)
        self.__hasFilterPaths = bool (filterPaths)
        self.__filterDirs = filter (os.path.isdir, filterPaths)
        self.__filterFiles = filter (os.path.isfile, filterPaths)

        trees = map (normPath, trees)
        self.__trees = filter (lambda p: p not in self.__filterDirs, trees)

        if self.__trees:
            self.__walker = os.walk (self.__trees.pop (0))

        self.__filterFunc = filterFunc

        self.__currentDir = None    # current dir
        self.__files = []           # files in current dir
        self.__dirs = []            # directories in current dir

    def __iter__ (self):
        if self.__trees:
            return self
        else:
            # nothing to iterate over
            return NullIterator ()

    def next (self):
        """ return next file """
        while self.__files:
            nextfile = self.__currentDir + self.__files.pop (0)
            if self.__filterFunc (nextfile):
                return nextfile
        # no files left in current dir; move on to next one and try again
        self.__nextdir ()
        return self.next ()

    def __nextdir (self):
        """ walk to next dir """
        currentDir = None
        while not currentDir: 
            try:
                currentDir, self.__dirs, self.__files = self.__walker.next ()
            except StopIteration:
                # tree exhausted
                if self.__trees:
                    # get a walker for next tree
                    self.__walker = os.walk (self.__trees.pop (0))
                else:
                    # all trees exhausted
                    raise 

        currentDir += os.path.sep
        self.__currentDir = currentDir
        # new directory, apply filter paths (carefully...):
        if not self.__hasFilterPaths:
            return
        l = len (currentDir)
        # apply pertinent filter files
        for f in filter (lambda p: p[:l] == currentDir, self.__filterFiles):
            try:
                self.__files.remove (f[l:])
            except ValueError:
                pass
        # apply pertinent filter dirs
        for d in filter (lambda p: p[:l] == currentDir, self.__filterDirs):
            try:
                self.__dirs.remove (d[l:])
            except ValueError:
                pass
