DROP DATABASE IF EXISTS CLOUD;
CREATE DATABASE CLOUD;
USE CLOUD;

CREATE TABLE LOGIN(
    USERNAME varchar(50),
	PASSWORD varchar(50),
	PRIMARY KEY(USERNAME)
	);

CREATE TABLE RIDES(
	RIDEID int,
    CREATEDBY varchar(50),
	TIMESTAMPS varchar(50),
	SOURCE varchar(50),
    DESTINATION varchar(50),
	FOREIGN KEY(CREATEDBY) REFERENCES LOGIN(USERNAME) ON DELETE CASCADE ON UPDATE CASCADE,
	PRIMARY KEY(RIDEID)
	);
	
CREATE TABLE USERS(
	RIDEID int,
    USERNAME varchar(50),
	FOREIGN KEY(RIDEID) REFERENCES RIDES(RIDEID) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY(USERNAME) REFERENCES LOGIN(USERNAME) ON DELETE CASCADE ON UPDATE CASCADE,
	PRIMARY KEY(RIDEID,USERNAME)
	);
	
CREATE TABLE COUNT_NO(
	RIDEACCESS int,
    RIDES int
	);
