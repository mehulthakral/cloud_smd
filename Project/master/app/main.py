from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint
import pika
import subprocess
import uuid
import time

time.sleep(15)
from kazoo.client import KazooClient
from kazoo.client import KazooState
import logging
logging.basicConfig()
logging.getLogger("kazoo.client").setLevel(logging.DEBUG)

print("hello")

zk = KazooClient(hosts='zookeeper:2181')
zk.start()

if zk.connected:
    print("zk connected")
else:
    print("Not able to connect to zk")

def my_listener(state):
    if state == KazooState.LOST:
        # Register somewhere that the session was lost
        print("zk lost")
    elif state == KazooState.SUSPENDED:
        # Handle being disconnected from Zookeeper
        print("zk suspended")
    else:
        # Handle being connected/reconnected to Zookeeper
        print("zk state changed")

zk.add_listener(my_listener)
zk.ensure_path("/znodes")
zk.create("/znodes/node_", b"a value", ephemeral=True, sequence=True, makepath=True)    

bashCommandName = 'hostname'
output = subprocess.check_output(['sh','-c', bashCommandName]) 
output = output.decode("utf-8")
output = output.strip('\n')
print(output)

config = {'user': 'root','password': '123','host': output,'port': 3306,'database': 'CLOUD'} 
config2 = {'user': 'root','password': '123','host': output,'port': 3306}

class RPC(object):

    def __init__(self,request_queue):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))

        self.channel = self.connection.channel()
        self.request_queue=request_queue
        result = self.channel.queue_declare(queue="responseQ2", exclusive=True)

        self.channel.basic_consume(
            queue="responseQ2",
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key=self.request_queue,
            properties=pika.BasicProperties(
                reply_to="responseQ2",
                correlation_id=self.corr_id,
            ),
            body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return self.response

def write_db(json):

    db = pymysql.connect(**config)
    cur = db.cursor()

    if(json["type"]=="insert"):

        columns = json["columns"][0]
        data = "'"+json["data"][0]+"'"

        for iter in range(1,len(json["columns"])):
            columns = columns + "," + json["columns"][iter]
            data = data + ",'" + json["data"][iter]+"'"

        sql = "INSERT INTO "+json["table"]+"("+columns+") VALUES ("+data+")"
    elif(json["type"]=="delete"):

        if json["where"]!="":
            sql = "DELETE FROM "+json["table"]+" WHERE "+json["where"]
        else:
            sql = "DELETE FROM "+json["table"]

    cur.execute(sql)
    db.commit()
    cur.close()
    db.close()
    return "1"

def clear_db():
    inp={"table":"RIDES","type":"delete", "where":""}
    data=write_db(inp)

    inp={"table":"USERS","type":"delete", "where":""}
    data=write_db(inp)

    return "Cleared database"

def read_db(json):
    db = pymysql.connect(**config)

    cur = db.cursor()
    columns = json["columns"][0]
    
    for iter in range(1,len(json["columns"])):
        columns = columns + "," + json["columns"][iter]

    if json["where"]!="":
        sql = "SELECT "+columns+" FROM "+json["table"]+" WHERE "+json["where"]
    else:
        sql = "SELECT "+columns+" FROM "+json["table"]
    cur.execute(sql)
    results = cur.fetchall()
    results = list(map(list,results))
    cur.close()
    db.close()
    return results

def on_request_master(ch, method, props, body):
    print(body)

    if body == b'clear':
        data=clear_db()
    else:
        message=eval(body)
        data=write_db(message)
    
    print(data)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.exchange_declare(exchange='my_exchange', exchange_type='fanout')
    channel.basic_publish(exchange='my_exchange', routing_key='', body=body)
    print(" [x] Sent %r" % message)
    connection.close()
    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def on_request_master_db(ch, method, props, body):
    print(body)
    db = pymysql.connect(**config)
    cur = db.cursor()
    sql = "SHOW TABLES;"
    cur.execute(sql)
    results = cur.fetchall()
    results = list(map(list,results))
    print(results)
    data={}
    for table in results:
        sql = "SELECT * FROM "+table[0]
        cur.execute(sql)
        data[table[0]] = cur.fetchall()
        data[table[0]] = list(map(list,data[table[0]]))
    cur.close()
    db.close()
    
    print(data)
    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def update_db(data):
    data=eval(data)
    print(data)
    col={"LOGIN":["USERNAME","PASSWORD"],"RIDES":["RIDEID","CREATEDBY","TIMESTAMPS","SOURCE","DESTINATION"],"USERS":["RIDEID","USERNAME"],"COUNT_NO":["RIDEACCESS","RIDES"]}
    for table in data:
        for row in data[table]:
            inp={"table":table,"type":"insert","columns":col[table],"data":row}
            write_db(inp)

def add_db():
    db = pymysql.connect(**config2)
    cur = db.cursor()
    sql = "DROP DATABASE IF EXISTS CLOUD;"
    cur.execute(sql)
    results = cur.fetchall()
    sql = "CREATE DATABASE CLOUD;"
    cur.execute(sql)
    results = cur.fetchall()
    sql = "USE CLOUD;"
    cur.execute(sql)
    results = cur.fetchall()
    sql = "CREATE TABLE LOGIN(USERNAME varchar(50),PASSWORD varchar(50),PRIMARY KEY(USERNAME));"
    cur.execute(sql)
    results = cur.fetchall()
    sql = "CREATE TABLE RIDES(RIDEID int,CREATEDBY varchar(50),TIMESTAMPS varchar(50),SOURCE varchar(50),DESTINATION varchar(50),FOREIGN KEY(CREATEDBY) REFERENCES LOGIN(USERNAME) ON DELETE CASCADE ON UPDATE CASCADE,PRIMARY KEY(RIDEID));"
    cur.execute(sql)
    results = cur.fetchall()
    sql = "CREATE TABLE USERS(RIDEID int,USERNAME varchar(50),FOREIGN KEY(RIDEID) REFERENCES RIDES(RIDEID) ON DELETE CASCADE ON UPDATE CASCADE,FOREIGN KEY(USERNAME) REFERENCES LOGIN(USERNAME) ON DELETE CASCADE ON UPDATE CASCADE,PRIMARY KEY(RIDEID,USERNAME));"
    cur.execute(sql)
    results = cur.fetchall()
    sql = "CREATE TABLE COUNT_NO(RIDEACCESS int,RIDES int);"
    cur.execute(sql)
    results = cur.fetchall()
    cur.close()
    db.close()
    print("Added db")

def on_request_slave_read(ch, method, props, body):
    body=eval(body)
    print(body)
   
    data=read_db(body)
    print(data)

    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def on_request_slave_sync(ch, method, props, body):
    body=eval(body)
    data=write_db(body)
    print(data)



if output == 'master':
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='writeQ')
    channel.queue_declare(queue='CopyQ')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='writeQ', on_message_callback=on_request_master)
    channel.basic_consume(queue='CopyQ', on_message_callback=on_request_master_db)

    print("Awaiting writeQ requests")
    channel.start_consuming()

else :
    add_db()
    copy_rpc=RPC("CopyQ")
    res=copy_rpc.call("copy")
    copy_rpc.connection.close()
    update_db(res)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='readQ')
    channel.exchange_declare(exchange='my_exchange', exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='my_exchange', queue=queue_name)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='readQ', on_message_callback=on_request_slave_read)
    channel.basic_consume(queue=queue_name, on_message_callback=on_request_slave_sync, auto_ack=True)


    print("Awaiting requests")
    channel.start_consuming()

connection.close()
