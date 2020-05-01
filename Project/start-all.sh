docker run -d --rm --name rabbitmq --hostname rabbitmq --net pronet -p 5672:5672 -p 15672:15672 rabbitmq
docker run -d --rm --name zookeeper --hostname zookeeper --net pronet zookeeper

if [ $# == 1 ]
then
   #cd master && sudo docker-compose build -d
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name master --hostname master --net pronet master 
   sleep 2
   sudo docker exec -it master python3 /app/main.py
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name slave1 --hostname slave1 --net pronet master
   sleep 2
   sudo docker exec -it slave1 python3 /app/main.py 
   cd ../orchestrator && sudo docker-compose up  --build -d
   cd ../
else
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name master --hostname master --net pronet master 
   sleep 2
   sudo docker exec -it master python3 /app/main.py
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name slave1 --hostname slave1 --net pronet master
   sleep 2
   sudo docker exec -it slave1 python3 /app/main.py 
   cd orchestrator && sudo docker-compose up -d
   cd ../
fi
