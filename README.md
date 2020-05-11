In order to run the project 3 instances must be running
1. Users
    To start the users container in the users instance
        1.`cd Assignment3/users`
        2.Change environment variable DBAAS_IP to the IP of the database instance in docker-compose.yml
        3.`sudo docker-compose up --build`
2. Rides
    To start the rides container in the rides instance
        1.`cd Assignment3/rides`
        2.Change environment variable DBAAS_IP to the IP of the database instance in docker-compose.yml
        3.`sudo docker-compose up --build`
3. Dbaas
    To start the orchestrator,master,one slave, rabbitmq and zookeeper containers in the dbaas instance
        1.`cd Project/`
        2.`sudo bash start-all.sh build`
    To stop all the containers
        1. `sudo bash stop-all.sh`