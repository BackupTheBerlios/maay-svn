from zope.interface import implements, Interface

from twisted.web import static

from nevow import rend

from maay.configuration import get_path_of

class MaayPage(rend.Page):
    """base web perspective"""
    child_maaycss = static.File(get_path_of('maay.css')
    child_images = static.File(get_path_of('images/')


class IIndexerPerspective(Interface):
    """Indexer perspective Interface"""
    def _updateDocument(docInfo):
        """updates DB according to docInfo"""


class IndexerPerspective:
    implements(IIndexerPerspective)

    def __init__(self, driver='mysql', host='', database='', user='', password=''):
        self._cnx = get_connection(driver, host, database, user, password)
        
    def _updateDocument(self, docInfo):
        """updates DB according to docInfo"""
        print "I'm asked to update DB according to", docInfo

    def remote_update(self, cnxId, docInfo):
        self._updateDocument(docInfo)
    
