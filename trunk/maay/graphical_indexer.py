"""This module contains a Tk wrapper around the indexer, for easier
operation on Windows boxes
"""

__revision__ = '$Id$'

from Tkinter import Tk

from maay import indexer

class IndexerGui(Tk):

    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.title("Maay Indexer")
        self._build_interface()
        
    def _build_interface(self):
        for line, (label, info) in enumerate(indexer.IndexerConfiguration.options):
            pass
        
