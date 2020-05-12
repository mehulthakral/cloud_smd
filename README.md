# RideShare on AWS
In order to run the project 3 instances must be running:<br>
### 1. Users<br>
&emsp; To start the users container in the users instance:<br>
&emsp;&emsp; 1.`cd Assignment3/users`<br>
&emsp;&emsp; 2.Change environment variable DBAAS_IP to the IP of the database instance in docker-compose.yml<br>
&emsp;&emsp; 3.`sudo docker-compose up --build`<br><br>
### 2. Rides<br>
&emsp; To start the rides container in the rides instance:<br>
&emsp;&emsp; 1.`cd Assignment3/rides`<br>
&emsp;&emsp; 2.Change environment variable DBAAS_IP to the IP of the database instance in docker-compose.yml<br>
&emsp;&emsp; 3.`sudo docker-compose up --build`<br><br>
### 3. Dbaas<br>
&emsp; To start the orchestrator, master, one slave, rabbitmq and zookeeper containers in the dbaas instance:<br>
&emsp;&emsp; 1.`cd Project/`<br>
&emsp;&emsp; 2.`sudo bash start-all.sh build`<br>
&emsp; To stop all the containers:<br>
&emsp;&emsp; 1. `sudo bash stop-all.sh`<br>
