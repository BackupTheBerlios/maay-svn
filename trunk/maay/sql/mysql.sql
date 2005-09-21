-- ---------------------------------------------------------
-- maay database
-- ---------------------------------------------------------

create database maay;

use maay;

-- ---------------------------------------------------------
-- maay tables
-- ---------------------------------------------------------

-- phpMyAdmin SQL Dump
-- version 2.6.0-pl2
-- http://www.phpmyadmin.net
-- 
-- Host: localhost
-- Generation Time: Feb 08, 2005 at 03:28 PM
-- Server version: 3.23.58
-- PHP Version: 4.3.9
-- 
-- Database: `maay`
-- 

-- --------------------------------------------------------

-- 
-- Table structure for table `document_providers`
-- 

CREATE TABLE `document_providers` (
  `db_document_id` int(11) NOT NULL default '0',
  `node_id` char(40) NOT NULL default '',
  `last_providing_time` int(11) default NULL,
  PRIMARY KEY  (`db_document_id`,`node_id`),
  KEY `db_document_id` (`db_document_id`)
) TYPE=MyISAM;

-- --------------------------------------------------------

-- 
-- Table structure for table `document_scores`
-- 

CREATE TABLE `document_scores` (
  `db_document_id` int(11) NOT NULL default '0',
  `word` varchar(50) NOT NULL default '',
  `position` int(11) NOT NULL default '-1',
  `download_count` float NOT NULL default '0',
  `relevance` float NOT NULL default '0',
  `popularity` float NOT NULL default '0',
  PRIMARY KEY  (`db_document_id`,`word`),
  KEY `db_document_id` (`db_document_id`),
  KEY `word` (`word`)
) TYPE=MyISAM;

-- --------------------------------------------------------

-- 
-- Table structure for table `documents`
-- 

CREATE TABLE `documents` (
  `db_document_id` int(11) NOT NULL auto_increment,
  `document_id` varchar(40) NOT NULL default '',
  `mime_type` varchar(40) NOT NULL default '',
  `title` varchar(255) default NULL,
  `size` int(11) default NULL,
  `text` text,
  `publication_time` int(14) default NULL,
-- FIXME: this should be an unsigned tinyint
  `state` char(1) default NULL,
  `download_count` float NOT NULL default '0',
  `url` varchar(255) NOT NULL default '',
  `matching` float NOT NULL default '0',
  `indexed` char(1) default '1',
  PRIMARY KEY  (`db_document_id`),
  KEY `document_id` (`document_id`),
  KEY `url` (`url`)
) TYPE=MyISAM AUTO_INCREMENT=313 ;

-- --------------------------------------------------------

-- 
-- Table structure for table `files`
-- 

CREATE TABLE `files` (
  `file_name` varchar(255) NOT NULL default '',
  `file_time` int(11) NOT NULL default '0',
  `db_document_id` int(11) default NULL,
-- FIXME : this matches documents.state, and should be unsigned tinyint too
  `state` tinyint(4) default NULL,
-- FIXME: unsigned tinyint too
  `file_state` tinyint(4) default NULL,
  PRIMARY KEY  (`file_name`),
  KEY `db_document_id` (`db_document_id`)
) TYPE=MyISAM;

-- --------------------------------------------------------

-- 
-- Table structure for table `node_interests`
-- 

CREATE TABLE `node_interests` (
  `node_id` varchar(40) NOT NULL default '',
  `word` varchar(50) NOT NULL default '',
  `claim_count` float NOT NULL default '0',
  `specialisation` float NOT NULL default '0',
  `expertise` float NOT NULL default '0',
  PRIMARY KEY  (`node_id`,`word`),
  KEY `node_id` (`node_id`)
) TYPE=MyISAM;

-- --------------------------------------------------------

-- 
-- Table structure for table `nodes`
-- 

CREATE TABLE `nodes` (
  `node_id` char(40) NOT NULL default '',
  `ip` char(15) NOT NULL default '',
-- FIXME: this should be unsigned smallint
  `port` smallint(11) NOT NULL default '0',
  `last_seen_time` int(11) default NULL,
  `counter` int(11) NOT NULL default '0',
  `claim_count` float NOT NULL default '0',
  `affinity` double NOT NULL default '0',
  `bandwidth` int(11) NOT NULL default '0',
  PRIMARY KEY  (`node_id`)
) TYPE=MyISAM;

-- --------------------------------------------------------

-- 
-- Table structure for table `words`
-- 

CREATE TABLE `words` (
  `word` varchar(50) NOT NULL default '',
  `claim_count` float NOT NULL default '0',
  `download_count` float NOT NULL default '0',
  PRIMARY KEY  (`word`)
) TYPE=MyISAM;
 


-- ---------------------------------------------------------
-- maay user
-- ---------------------------------------------------------

grant all on maay.* to "maay"@"localhost" identified by "maay";
