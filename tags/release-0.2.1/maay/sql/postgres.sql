-- ---------------------------------------------------------
-- maay tables (postgres version)
-- Note: This file is inspired by original MySQL's maay
--       tables creation script, and quite possibly contains
--       inconsistent instructions
-- ---------------------------------------------------------

--
-- Table structure for table `document_providers`
-- 

CREATE TABLE document_providers (
  db_document_id integer NOT NULL default '0',
  node_id varchar(40) NOT NULL default '',
  last_providing_time integer default NULL,
  PRIMARY KEY  (db_document_id,node_id)
);

-- --------------------------------------------------------


-- 
-- Table structure for table document_scores
-- 

CREATE TABLE document_scores (
  db_document_id integer NOT NULL default '0',
  word varchar(50) NOT NULL default '',
  position integer NOT NULL default '-1',
  download_count float NOT NULL default '0',
  relevance float NOT NULL default '0',
  popularity float NOT NULL default '0',
  PRIMARY KEY  (db_document_id,word)
);
-- --------------------------------------------------------

-- 
-- Table structure for table documents
-- 

CREATE SEQUENCE documents_id_seq;

CREATE TABLE documents (
  db_document_id integer NOT NULL default nextval('documents_id_seq'),
  document_id varchar(40) NOT NULL default '',
  mime_type varchar(40) NOT NULL default '',
  title varchar(255) default NULL,
  size integer default NULL,
  text text,
  publication_time integer default NULL,
  state char(1) default NULL,
  download_count float NOT NULL default '0',
  url varchar(255) NOT NULL default '',
  matching float NOT NULL default '0',
  indexed char(1) default '1',
  PRIMARY KEY  (db_document_id)
);

-- --------------------------------------------------------

-- 
-- Table structure for table files
-- 

CREATE TABLE files (
  file_name varchar(255) NOT NULL default '',
  file_time integer NOT NULL default '0',
  db_document_id integer default NULL,
  state integer default NULL,
  file_state smallint default NULL,
  PRIMARY KEY  (file_name)
);

-- --------------------------------------------------------

-- 
-- Table structure for table node_interests
-- 

CREATE TABLE node_interests (
  node_id varchar(40) NOT NULL default '',
  word varchar(50) NOT NULL default '',
  claim_count float NOT NULL default '0',
  specialisation float NOT NULL default '0',
  expertise float NOT NULL default '0',
  PRIMARY KEY  (node_id,word)
);

-- --------------------------------------------------------

-- 
-- Table structure for table nodes
-- 

CREATE TABLE nodes (
  node_id char(40) NOT NULL default '',
  ip char(15) NOT NULL default '',
  port smallint NOT NULL default '0',
  last_seen_time integer default NULL,
  counter integer NOT NULL default '0',
  claim_count float NOT NULL default '0',
  affinity float8 NOT NULL default '0',
  bandwidth integer NOT NULL default '0',
  PRIMARY KEY  (node_id)
);

-- --------------------------------------------------------

-- 
-- Table structure for table words
-- 

CREATE TABLE words (
  word varchar(50) NOT NULL default '',
  claim_count float NOT NULL default '0',
  download_count float NOT NULL default '0',
  PRIMARY KEY  (word)
);
 


-- ---------------------------------------------------------
-- maay user XXX: not implemented yet
-- ---------------------------------------------------------
