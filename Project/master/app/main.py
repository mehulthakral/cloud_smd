from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint
import pika
import subprocess
import uuid

from kazoo.client import KazooClient
from kazoo.client import KazooState

import logging
logging.basicConfig()
logging.getLogger("kazoo.client").setLevel(logging.DEBUG)

app = Flask(__name__)
config = {
        'user': 'root',
        'password': '123',
        'host': 'localhost',
        'port': 3306,
        'database': 'CLOUD'
    }

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
output = subprocess.check_output(['bash','-c', bashCommandName]) 
#print(output)
output = output.decode("utf-8")
#print(type(output))
output = output.strip('\n')
print(output)
#output = 'slave1'

config = {'user': 'root','password': '123','host': output,'port': 3306,'database': 'CLOUD'} 
"""
class RPC(object):
    def __init__(self,request_queue):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))

        self.channel = self.connection.channel()
        self.request_queue=request_queue
        result = self.channel.queue_declare(queue="returnQ2", exclusive=True)

        self.channel.basic_consume(
            queue="returnQ2",
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.exchange_declare(exchange='my_exchange', exchange_type='fanout')
        self.channel.basic_publish(exchange='my_exchange', routing_key=self.request_queue, properties=pika.BasicProperties(reply_to="returnQ2",correlation_id=self.corr_id,),body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return self.response
"""
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
    #print(results)
    results = list(map(list,results))
    cur.close()
    db.close()
    return results

def on_request_master(ch, method, props, body):
    print(body)
    message=eval(body)
    if message == 'clear':
        data=clear_db()
    else:
        data=write_db(message)
    
    print(data)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.exchange_declare(exchange='my_exchange', exchange_type='fanout')
    channel.basic_publish(exchange='my_exchange', routing_key='', body=message)
    print(" [x] Sent %r" % message)
    connection.close()
    """
    sync_rpc=RPC("syncQ")
    sync_rpc.call(body)
    sync_rpc.connection.close()
    print("here")
    #channel.queue_declare(queue="syncQ", exclusive=True)
    #channel.basic_publish(exchange='', routing_key=request_queue, body=body)
    #ch.exchange_declare(exchange='my_exchange', exchange_type='fanout')
    """
    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def on_request_slave_read(ch, method, props, body):
    #print(body)
    body=eval(body)
    print(body)
    #print(type(body))
   
    data=read_db(body)
    print(data)
    #data=data.decode("utf-8")

    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def on_request_slave_sync(ch, method, props, body):
    body=eval(body)
    data=write_db(body)
    print(data)
    #ch.exchange_declare(exchange='my_exchange', exchange_type='fanout')
    #ch.basic_publish(exchange='my_exchange', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    #ch.basic_ack(delivery_tag=method.delivery_tag)


if output == 'master':
    #print('master')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='writeQ')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='writeQ', on_message_callback=on_request_master)

    print("Awaiting writeQ requests")
    channel.start_consuming()

else :
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='readQ')
    channel.exchange_declare(exchange='my_exchange', exchange_type='fanout')
    channel.queue_declare(queue='syncQ')
    channel.queue_bind(exchange='my_exchange', queue='syncQ')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='readQ', on_message_callback=on_request_slave_read)
    channel.basic_consume(queue='syncQ', on_message_callback=on_request_slave_sync, auto_ack=True)


    print("Awaiting requests")
    channel.start_consuming()

connection.close()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
