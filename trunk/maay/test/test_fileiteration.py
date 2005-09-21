"""tests file iteration"""

__revision__ = '$Id$'

import unittest
import os
from os.path import join, abspath, dirname, exists

from maay.indexer import FileIterator as BaseFileIterator

HERE = dirname(__file__)
DATADIR = join(HERE, 'data')
assert exists(DATADIR)

def touch(filename):
    # not a real *touch*, but oh well ...
    fp = file(filename, 'w')
    fp.close()


class FileIterator(BaseFileIterator):
    """just transforms relative paths to absolute paths"""
    def __init__(self, indexed, skipped=None):
        indexed = [abspath(path) for path in indexed]
        if skipped:
            skipped = [abspath(path) for path in skipped]
        else:
            skipped = []
        BaseFileIterator.__init__(self, indexed, skipped)
            

class FileIterationTC(unittest.TestCase):
    def setUp(self):
        self.pathList = [
            ('a/b/c', ['foo', 'bar']),
            ('a/c/d', []), ('a/b/e', []),
            ('b/c/d', ['baz', 'spam']),
            ('b/c/e', ['foobar', 'bazbar']),
            ]
        for dirpath, filenames in self.pathList:
            realpath = join(DATADIR, dirpath)
            os.makedirs(realpath)
            for filename in filenames:
                touch(join(realpath, filename))

    def tearDown(self):
        for dirpath, filenames in self.pathList:
            realpath = join(DATADIR, dirpath)
            for filename in filenames:
                os.remove(join(realpath, filename))
            os.removedirs(realpath)

    def testDirCreation(self):
        """make sure all paths in pathList have been created"""
        for dirpath, filenames in self.pathList:
            self.assert_(os.path.exists(join(DATADIR, dirpath)))


    def testNothingSkipped(self):
        it = FileIterator(['a', 'b', 'c'])
        self.assertEquals(list(it), [])
        it = FileIterator(['data/a', 'data/b', 'data/c'])
        expected = [abspath(join('data', 'a', 'b', 'c', 'bar')),
                    abspath(join('data', 'a', 'b', 'c', 'foo')),
                    abspath(join('data', 'b', 'c', 'd', 'baz')),
                    abspath(join('data', 'b', 'c', 'd', 'spam')),
                    abspath(join('data', 'b', 'c', 'e', 'bazbar')),
                    abspath(join('data', 'b', 'c', 'e', 'foobar')),
                    ]
        self.assertEquals(list(it), expected)

    def testEverythingSkipped(self):
        everything = ['data/a', 'data/b', 'data/c']
        it = FileIterator(everything, everything)
        self.assertEquals(list(it), [])


    def testSkippingSomething(self):
        everything = ['data/a', 'data/b', 'data/c']
        skipped = ['data/a', 'data/b/c/e']
        it = FileIterator(everything, skipped)
        expected = [abspath(join('data', 'b', 'c', 'd', 'baz')),
                    abspath(join('data', 'b', 'c', 'd', 'spam')),
                    ]
        self.assertEquals(list(it), expected)


    def testFailOnRelativePath(self):
        """make sure FileIterator forbids relative paths"""
        self.assertRaises(AssertionError, BaseFileIterator, ['data/a'], ['data/b'])
        self.assertRaises(AssertionError, BaseFileIterator, ['/data/a'], ['/data/b', 'data/c'])
        

if __name__ == '__main__':
    unittest.main()
