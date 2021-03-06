#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""tests file iteration"""

__revision__ = '$Id$'

import unittest
import os
from os.path import join, abspath, dirname, exists
from sets import Set

from maay.indexer import FileIterator

HERE = dirname(__file__)
DATADIR = join(HERE, 'data')
assert exists(DATADIR)

def touch(filename):
    # not a real *touch*, but oh well ...
    fp = file(filename, 'w')
    fp.close()

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

        f = open(join(DATADIR, '\xe2\x99\xaa\xe2\x99\xac'), 'w')
        f.write("""After
% kbd_mode -u
% echo -e '\033%8'
% loadkeys
control shift keycode 59 = U+266a
control shift keycode 60 = U+266C
%
I typed this file and called it by the two-symbol name
ctrl-shift-F1 ctrl-shift-F2.

In order to tell `ls' not to be afraid, give it the `-N' flag.
Give `less' the `-r' flag.
""")
        f.close()
        

        
    def tearDown(self):
        for dirpath, filenames in self.pathList:
            realpath = join(DATADIR, dirpath)
            for filename in filenames:
                os.remove(join(realpath, filename))
            os.removedirs(realpath)
        os.remove(join(DATADIR, '\xe2\x99\xaa\xe2\x99\xac'))

    def testDirCreation(self):
        """make sure all paths in pathList have been created"""
        for dirpath, filenames in self.pathList:
            self.assert_(os.path.exists(join(DATADIR, dirpath)))


    def testNothingSkipped(self):
        it = FileIterator(['a', 'b', 'c'])
        self.assertEquals(list(it), [])
        it = FileIterator([join(DATADIR, 'a'), join(DATADIR, 'b'),
                           join(DATADIR, 'c')])
        expected = Set([abspath(join(DATADIR, 'a', 'b', 'c', 'bar')),
                        abspath(join(DATADIR, 'a', 'b', 'c', 'foo')),
                        abspath(join(DATADIR, 'b', 'c', 'd', 'baz')),
                        abspath(join(DATADIR, 'b', 'c', 'd', 'spam')),
                        abspath(join(DATADIR, 'b', 'c', 'e', 'bazbar')),
                        abspath(join(DATADIR, 'b', 'c', 'e', 'foobar')),
                        ])
        self.assertEquals(Set(it), expected)

    def testEverythingSkipped(self):
        everything = ['data/a', 'data/b', 'data/c']
        it = FileIterator(everything, everything)
        self.assertEquals(list(it), [])


    def testSkippingSomething(self):
        everything = [join(DATADIR, 'a'), join(DATADIR, 'b'),
                      join(DATADIR, 'c')]
        skipped = [join(DATADIR, 'a'), join(DATADIR, 'b', 'c', 'e')]
        it = FileIterator(everything, skipped)
        expected = Set([abspath(join(DATADIR, 'b', 'c', 'd', 'baz')),
                        abspath(join(DATADIR, 'b', 'c', 'd', 'spam')),
                        ])
        self.assertEquals(expected, Set(it))

    def testRelativePathConversion(self):
        """FileIterator should automatically convert relative paths"""
        paths = [(['data/a'], ['data/b']),
                 (['/data/a'], ['/data/b', 'data/c'])]
        for indexed, skipped in paths:
            onRelatives = list(FileIterator(indexed, skipped))
            absIndexed = [abspath(path) for path in indexed]
            absSkipped = [abspath(path) for path in skipped]
            onAbspaths = list(FileIterator(absIndexed, absSkipped))
            self.assertEquals(onRelatives, onAbspaths)

    def testSkipNonAllowed(self):
        """tests that files that don't have 'read' permission are skipped"""
        # these two files should be skipped
        os.chmod(join(DATADIR, 'a/b/c/foo'), 0)
        os.chmod(join(DATADIR, 'b/c/d/spam'), 0)
        it = FileIterator([join(DATADIR, 'a'), join(DATADIR, 'b'),
                           join(DATADIR, 'c')])
        expected = Set([abspath(join(DATADIR, 'a', 'b', 'c', 'bar')),
                        abspath(join(DATADIR, 'b', 'c', 'd', 'baz')),
                        abspath(join(DATADIR, 'b', 'c', 'e', 'bazbar')),
                        abspath(join(DATADIR, 'b', 'c', 'e', 'foobar')),
                        ])
        self.assertEquals(Set(it), expected)

    def testDontChokeOnWeirdFilename(self):
        """we should iter without pain on everything in DATADIR, including
           the file whose name begins with an &acirc;
        """
        try:
            l = list(FileIterator([DATADIR]))
        except:
            self.fail("Exception while iterating on %s"%DATADIR)

    def testValidateFileIteratorTypeCheckOnInit(self):
        """FileIterator.__init__ type checks ints indexed and skipped
           parameters : ensure it does
        """
        ofBogusType = "foo"
        self.assertRaises(AssertionError, FileIterator, ofBogusType)
        
if __name__ == '__main__':
    unittest.main()
