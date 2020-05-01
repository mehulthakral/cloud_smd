sudo docker run -d --rm --name rabbitmq --hostname rabbitmq --net pronet -p 5672:5672 -p 15672:15672 rabbitmq
sudo docker run -d --rm --name zookeeper --hostname zookeeper --net pronet -p 2181:2181 zookeeper

if [ $# == 1 ]
then
   cd master && sudo docker-compose up --build -d
   sleep 2
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name slave1 --hostname slave1 --net pronet master
   cd ../orchestrator && sudo docker-compose up  --build -d
   cd ../
else
   cd master && sudo docker-compose up -d
   sudo docker run --rm -d --env MYSQL_ROOT_PASSWORD=123 --name slave1 --hostname slave1 --net pronet master
   cd ../orchestrator && sudo docker-compose up -d
   cd ../
fi
