Warning
=======

This is alpha quality software. Before launching anything be sure to read 
this document and the release notes for the program. On Windows systems, 
the release notes are available through the start menu shortcut of Maay.

What is Maay?
=============

Maay is a P2P indexation and search engine. You can use it to index
files on your computer, and export them to other members of the Maay
P2P network. You can also issue searches which will look for documents
on your computer as well as on other nodes of the P2P network.

What is in the current implementation?
======================================

The current Maay implementation features:

 * an indexer, which can handle the following document formats: raw
   text, HTML, Microsoft Word, Rich Text Format, Portable Document
   Format. 

 * a web interface which can be used to issue queries (currently
   queries are ontly dispatched on the current node, i.e. the P2P
   functionnality is not available for now, though we are working on
   it). 

How do I install Maay from source?
==================================

These instruction are intended for people using a unix-like
OS. Windows users are strongly advised to use the prebuilt package
(see below).

A few Python libraries are required to make the whole think work. Most
of them should be available in your OS distribution too :

 * logilab common libraries (http://www.logilab.org/projects/common)
 * mysql-python (http://sourceforge.net/projects/mysql-python)
 * python-twisted (http://twistedmatrix.com/)
 * python-twisted-web (http://twistedmatrix.com/)
 * python-nevow (http://nevow.com/)

You will also need a few helper applications to perform the conversion
of various binary formats to something that Maay can index. There is
probably a prebuilt binary available for your OS distribution
somewhere. You will need to download and install :

 * pdftohtml (http://pdftohtml.sourceforge.net/)
 * antiword (http://www.winfield.demon.nl/)
 * unrtf (http://www.gnu.org/software/unrtf/unrtf.html)

The indexation part uses a MySQL database, so 

Once everything else is installed, you can point you web browser to
http://developer.berlios.de/projects/maay/ and download the latest
source tarball. Unpack it, go to the newly created directory and run::

 # python setup.py install

It is now necessary to create the MySQL database instance that will
store the indexation data::

 # mysql -u root mysql
 mysql> \. sql/mysql.sql

You're done !

How do I install Maay from a package?
=====================================

For now, only a Windows installer is available. Download it from
http://developer.berlios.de/projects/maay/ and run it. This should
install and setup everything properly. 

A package for the Debian GNU/Linux distribution will soon be made
available. 

How do I start using Maay?
==========================

First, edit the configuration files. On Windows, they are in 
C:\Program Files\Maay\webapp.ini and C:\Program Files\Maay\indexer.ini.
On Unix systems, they are in /etc/maay, and you can copy them to 
~/.maay/ if you want to have some personnalized settings. Pay attention 
to the index-dir and skip-dir settings in indexer.ini.

Then, start the Maay service. On Windows, use the start menu to
launch "Maay Server". On unix systems, use /usr/bin/maay-server

You can now visit http://localhost:8080/ which will display the Maay
search page. Issuing a search will probably not yield any result since
you have not indexed any files yet.

Launch the indexer. On Windows, this is done through the start menu
again by choosing "Maay Indexer". On Unix systems, use
/usr/bin/maay-indexer. The indexer will look for files on your hard
disks and index them by sending indexation requests to the
server. Once the indexation is done, queries issued through the web
interface should give results. 

Where can I get help?
=====================

For now the best place to ask for help is on the development mailing
list of Maay. You can subscribe from

http://lists.berlios.de/mailman/listinfo/maay-dev

You may also use the bug tracker on the Berlios project page at 
http://developer.berlios.de/projects/maay/


 Alexandre Fayolle <alexandre.fayolle@logilab.fr>, Thu,  6 Oct 2005 15:50:15 +0200
