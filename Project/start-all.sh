sudo docker run -d --rm --name rabbitmq --hostname rabbitmq --net pronet -p 5672:5672 -p 15672:15672 rabbitmq
sudo docker run -d --rm --name zookeeper --hostname zookeeper --net pronet -p 2181:2181 zookeeper

sleep 10
if [ $# == 1 ]
then
   cd orchestrator && sudo docker-compose up  --build -d
   cd ../
   sleep 2
   cd master && sudo docker-compose build --force-rm
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name master --hostname master --net pronet -v data:/var/lib/mysql master 
   sleep 4
   # sudo docker exec -it master python3 /app/main.py
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name slave1 --hostname slave1 --net pronet master
   # cd master && sudo docker-compose build -d
   # sleep 2
   # sudo docker exec -it slave1 python3 /app/main.py
   
else
   cd orchestrator && sudo docker-compose up -d
   cd ../
   sleep 2
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name master --hostname master --net pronet -v data:/var/lib/mysql master 
   sleep 4
   # sudo docker exec -it master python3 /app/main.py
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name slave1 --hostname slave1 --net pronet master
   # sleep 2
   # sudo docker exec -it slave1 python3 /app/main.py 
   
fi