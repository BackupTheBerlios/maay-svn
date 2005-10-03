#!/usr/bin/env python
# id3v2.py Version 0.1 (work still in progress)
# $Header: //d/usr/CVS/Python/id3v2.py,v 1.2 2001/04/06 23:34:32 becky Exp $
#
# This takes a list of mp3 filenames and spits out an alternative
# filename based on the files id3v2 tag.
# There is another script id3.py which uses the v1 tag.
# I'll integrate it in when I get the time. Shouldnt be too hard
# but I'm often stupidly optimistic like this.
#
# This script only reads id3v2 tags.
# I suppose next enhancement might be to write id3v2 tags.
# and maybe some interaction with CDDB.
# Hmmmm, might need to next write some code to calculate the CDDB id.
#
# Would be nice if u sent me any enhancements/suggestions.
# mailto:calcium@altavista.net
# http://www.ozemail.com.au/~calcium
#
# -----------------
# TODO
# -----------------
# Handle extended headers properly
# Ability to create id3v2 tags.
# Make it more robust.
#
# -----------------
# The documentation.
# -----------------
# I doubt this will be of much use to anyone apart from curiousity value.
# I guess if u want to enhance it to handle additional tags, u'll need
# to write a function called "processXXXX" where XXXX is the frameId.
#
# I also suspect u'll need to have the id3v2 spec to make sense of
# some of the code.
# See http://www.id3.org
# See http://www.python.org
# See http://www.jython.org
# That's it.
#
# Ciao,
# Chai in Melbourne, Australia.
#

import sys
import string
import struct

#
# This gets the id3v2 tag from the file specified.
#
class Mp3file:
    def __init__( self, filename):
        self.filename                   = filename
        self.ok                         = 0

        f                               = open( self.filename )

        # The header
        self.header                     = f.read( 3 )
        if self.header != "ID3":
            return
        # The version is the next 2 bytes
        self.version                    = f.read( 2 )

        # The flags. See the id3 v2 spec for details. Am ignoring it.
        self.flags                      = f.read( 1 )

        # I guess I shouldnt ignore the flags but could nt find any test data.
        if ord( self.flags ) != 0:
            print "Hey! There is an extended header present. Untested!!!"

        # The id3 Tag Size.
        b1, b2, b3, b4                  = struct.unpack( '>bbbb', f.read( 4 ) )

        id3Size                         = self.syncSafeInt( b1, b2, b3, b4 )

        '''
        # Not ready
        # If there is extended header.
        if ord( self.flags ) != 0:
            # The extended header Size.
            b1, b2, b3, b4              = struct.unpack( '>bbbb', f.read( 4 ) )
            self.extHeaderSize          = self.syncSafeInt( b1, b2, b3, b4 )
            self.extHeaderFlagBytes     = f.read( 1 )
            self.extHeaderExtendedFlags = f.read( 1 )
            print "reading" + str ( self.extHeaderSize )
            self.extHeaderData          = f.read( self.extHeaderSize )
        '''

        # Reading in the id3 frames
        while ( 1 ) :
            # Assume that the id3size specified in the header is correct.
            if ( f.tell() >= id3Size + 10 ):
                break
            self.frameId                = f.read( 4 )
            self.frameSize              = struct.unpack( '>l', f.read( 4 ) )
            # incase the id3 size is wrong, break anyway.
            if self.frameSize[ 0 ] == 0:
                break;
            # read the frame header flags
            self.frameFlags             = f.read( 2 )
            blkSize                     = self.frameSize[ 0 ]
            if blkSize < 0:
                raise RuntimeError, "Error in frame size(" + str( blkSize ) + ")"
            self.data                   = f.read( blkSize )

            # constructing the statement to process the header
            # passing the TAG, EXTFLAGS, DATA as parameters.
            pStr = "self.process" + self.frameId \
                    + "( self.frameId, self.frameFlags, self.data )"
            try:
                exec pStr
                self.ok                 = 1
            except AttributeError:
                print "Warning: process" + self.frameId + "() not implemented."
                continue
        f.close()

    #
    # This massages the tag in to the required format.
    #
    def fixTag( self, theString ):
        # I've had a few songs padded with 0xff and 0x00. Figure?
        theString =  string.replace( theString, chr(0xff), " " )
        theString =  string.replace( theString, chr(0x00), " " )
        theString =  string.strip( theString )
        # Comment out the following line if u prefer spaces to "_"
        theString =  string.replace( theString, " ", "_" )

        # Guess I should also check that filename is legal.
        return theString

    #
    # Gets the filename
    #
    def getFilename( self ):
        return self.filename

    #
    # A guess as to whether file interrogation succeeded
    #
    def isOK( self ):
        return self.ok

    #
    # Gets the version
    #
    def getVersion( self ):
        return self.version

    #
    # Gets the flags
    #
    def getFlags( self ):
#       print "Flags='%x" % ( ord( self.flags ) )
        return self.flags
    #
    # Sets the album name
    #
    def processTALB( self, theString, theFlags, theValue ):
        self.album = self.fixTag( theValue )

    def getAlbum( self ):
        return self.album

    #
    # Sets the artist name
    #
    def processTPE1( self, theString, theFlags, theValue ):
        self.artist = self.fixTag( theValue )

    def getArtist( self ):
        return self.artist

    #
    # Sets the title track name
    #
    def processTIT2( self, theString, theFlags, theValue ):
        self.song = self.fixTag( theValue )

    def getSong( self ):
        return self.song

    def syncSafeInt( self, b1, b2, b3, b4 ):
        return ( b4 & 0xff ) + \
                    + ( ( b3 & 0xff ) << 7 ) \
                    + ( ( b2 & 0xff ) << 14 ) \
                    + ( ( b1 & 0xff ) << 21 ) 


#
# Main program starts here
#
if __name__ == "__main__":
    for i in range( len( sys.argv ) - 1 ):
        filename = sys.argv[i + 1]

        mp3File = Mp3file ( filename )

        # replace "mv" with whatever will work for your OS eg rename etc...
        OS_RENAME_CMD = "mv"
        if mp3File.isOK():
            print "%s \"%s\" \"%02d-%s-%s.mp3\"" % ( OS_RENAME_CMD,
                                                     filename,
                                                     i + 1,
                                                     mp3File.getArtist(),
                                                     mp3File.getSong() )
