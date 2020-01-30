CREATE TABLE Login(
    username varchar(50),
	password varchar(50),
	PRIMARY KEY(username)
	);

CREATE TABLE RIDES(
	RideID int,
    CreatedBy varchar(50),
	Timestamp varchar(50),
	Source varchar(50),
    Destination varchar(50),
	FOREIGN KEY(CreatedBy) REFERENCES Login(username) ON DELETE CASCADE ON UPDATE CASCADE,
	PRIMARY KEY(RideID)
	);
	
CREATE TABLE USERS(
	RideID int,
    username varchar(50),
	FOREIGN KEY(RideID) REFERENCES RIDES(RideID) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY(username) REFERENCES Login(username) ON DELETE CASCADE ON UPDATE CASCADE,
	PRIMARY KEY(RideID,username)
	);