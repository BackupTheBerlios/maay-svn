==================
Maay documentation
==================

.. revision: $Id$

Warning
=======

This is beta quality software. Before launching anything be sure to read 
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

 * the maay node, which acts as an XMLRPC and HTTP server. The XMLRPC
   interface is used to process indexation requests and distributed
   queries. The HTTP interface is available through a web browser to
   issue local and distributed queries, as well as indexation
   requests. 

 * an indexer, which can handle the following document formats: raw
   text, HTML, Microsoft Word, Rich Text Format, Portable Document
   Format. 

 * a presence server, which can handle presence information from maay
   nodes, in order to seed the node database. 


How do I start using Maay?
==========================

First, edit the configuration files. On Windows, they are in
C:\Program Files\Maay\node.ini and C:\Program
Files\Maay\indexer.ini. The Windows installer should have set the
different configuration values.  On Unix systems, they are in
/etc/maay, and you can copy them to ~/.maay/ if you want to have some
personnalized settings. Pay attention to the index-dir and skip-dir
settings in indexer.ini.

Then, start the Maay service. On Windows, this is done automatically
when your machine boots. On unix systems, use /usr/bin/maay-server

You can now visit http://localhost:7777/ which will display the Maay
search page. Issuing a search will probably not yield any result since
you have not indexed any files yet.

Launch the indexer: visit http://localhost:7777/indexation, check that
the directories are correct and click on the "index now" button. On
Windows, the indexation can also be launched manually through the
start menu again by choosing "Maay Indexer". On Unix systems, the
manual indexation is done by running /usr/bin/maay-indexer. 

The indexer will look for files on your hard disks and index them by
sending indexation requests to the server. Once the indexation is
done, queries issued through the web interface should give results.

Where can I get help?
=====================

For now the best place to ask for help is on the development mailing
list of Maay. You can subscribe from
http://lists.berlios.de/mailman/listinfo/maay-dev

You may also use the bug tracker on the Berlios project page at 
http://developer.berlios.de/projects/maay/

When reporting a bug or asking for help, don't forget to provide the
following pieces of information:

 * operating system
 * version and name of browser
 * version of maay
 * on unix: version of python
 * steps to reproduce the bug

Be as precise as possible. Just saying "the indexer does not work"
won't give us any clue to help you. 


 Alexandre Fayolle <alexandre.fayolle@logilab.fr>, Fri, 18 Nov 2005 15:00:58 +0100


