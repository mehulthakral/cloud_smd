CREATE DATABASE CLOUD;
USE CLOUD;
CREATE TABLE RIDES(
	RIDEID int,
    CREATEDBY varchar(50),
	TIMESTAMPS varchar(50),
	SOURCE varchar(50),
    DESTINATION varchar(50),
	PRIMARY KEY(RIDEID)
	);
	
CREATE TABLE USERS(
	RIDEID int,
    USERNAME varchar(50),
	FOREIGN KEY(RIDEID) REFERENCES RIDES(RIDEID) ON DELETE CASCADE ON UPDATE CASCADE,
	PRIMARY KEY(RIDEID,USERNAME)
	);
