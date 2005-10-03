CREATE TABLE documents (
  db_document_id INTEGER PRIMARY KEY, 
  document_id CHAR(40) NOT NULL default '',
  mime_type varchar(40) NOT NULL default '',
  title varchar(255) default NULL,
  size int(11) default NULL,
  text text,
  publication_time int(14) default NULL,
  state CHAR,
  download_count int(11) NOT NULL default '0',
  url varchar(255) NOT NULL default '',
  checked tinyint(4) NOT NULL default '0',
  matching float NOT NULL default '0'
);

CREATE INDEX document_id ON documents(document_id);

CREATE TABLE document_providers (
  db_document_id INTEGER NOT NULL,
  node_id char(40) NOT NULL default '',
  last_providing_time int(11) default NULL,
  PRIMARY KEY  (db_document_id,node_id)
); 

CREATE TABLE document_scores (
  db_document_id INTEGER NOT NULL,
  word varchar(50) NOT NULL,
  position int(11) NOT NULL default '-1',
  download_count float NOT NULL default '0',
  relevance float NOT NULL default '0',
  popularity float NOT NULL default '0',
  PRIMARY KEY  (db_document_id,word)
); 

CREATE INDEX document_scores_db_document_id ON document_scores(db_document_id);
CREATE INDEX document_scores_word ON document_scores(word);

CREATE TABLE files (
  file_name varchar(255) NOT NULL,
  file_time int(11) NOT NULL default '0',
  db_document_id INT,
  state tinyint,
  file_state tinyint,
  PRIMARY KEY (file_name)
);

CREATE TABLE node_interests (
  node_id char(40) NOT NULL,
  word char(40) NOT NULL,
  claim_count float NOT NULL default '0',
  relevance float NOT NULL default '0',
  popularity float NOT NULL default '0',
  PRIMARY KEY  (node_id,word)
);

CREATE TABLE nodes (
  node_id char(40) NOT NULL,
  ip char(15) NOT NULL default '',
  port smallint(11) NOT NULL default '0',
  last_seen_time int(11) default NULL,
  counter int(11) NOT NULL default '0',
  claim_count float NOT NULL default '0',
  passion double NOT NULL default '0',
  bandwidth int(11) NOT NULL default '0',
  PRIMARY KEY (node_id)
);

CREATE TABLE words (
  word char(40) NOT NULL,
  claim_count float NOT NULL default '0',
  download_count float NOT NULL default '0',
  PRIMARY KEY  (word)
);

CREATE TABLE word_relationships (
  word1 char(40) NOT NULL,
  word2 char(40) NOT NULL,
  search_count int(11) NOT NULL default '0',
  download_count int(11) NOT NULL default '0',
  response_count int(11) NOT NULL default '0',
  node_count int(11) NOT NULL default '0',
  PRIMARY KEY  (word1,word2)
);

CREATE TABLE links (
  src_document_id varchar(40) NOT NULL,
  path varchar(255) NOT NULL,
  link_time int(11) NOT NULL,
  dst_document_id varchar(40) NOT NULL default '',
  PRIMARY KEY  (src_document_id,path,link_time)
);
CREATE TABLE file_links (
  src_file_name varchar(200) NOT NULL,
  path varchar(200) NOT NULL,
  dst_file_name varchar(255) NOT NULL default '',
  state int(11) NOT NULL default '0',
  PRIMARY KEY  (src_file_name,path)
);



