from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint
import pika
import docker
import uuid
import subprocess

import os

from kazoo.client import KazooClient
from kazoo.client import KazooState
from kazoo.handlers.gevent import SequentialGeventHandler

import logging
logging.basicConfig()
logging.getLogger("kazoo.client").setLevel(logging.DEBUG)

import sys

from kazoo.exceptions import ConnectionLossException
from kazoo.exceptions import NoAuthException

app = Flask(__name__)
config = {
        'user': 'root',
        'password': '123',
        'host': 'db',
        'port': 3306,
        'database': 'CLOUD'
    }

# zk = KazooClient(hosts='zookeeper:2181',handler=SequentialGeventHandler())

# # returns immediately
# event = zk.start_async()

# # Wait for 30 seconds and see if we're connected
# event.wait(timeout=30)

# if not zk.connected:
#     # Not connected, stop trying to connect
#     zk.stop()
#     raise Exception("Unable to connect.")

# zk.ensure_path_async("/znodes")

# # @zk.ChildrenWatch("/znodes")
# # def watch_children(children):
# #     print("Children are now: %s" % children)
# # Above function called immediately, and from then on

# zk.create_async("znodes/node", value=b" ", acl=None, ephemeral=True, sequence=True, makepath=False)

# print("hello")

# def my_callback(async_obj):
#     try:
#         children = async_obj.get()
#         print(children)
#     except (ConnectionLossException, NoAuthException):
#         sys.exit(1)

# # Both these statements return immediately, the second sets a callback
# # that will be run when get_children_async has its return value
# async_obj = zk.get_children_async("/znodes")
# async_obj.rawlink(my_callback)

zk = KazooClient(hosts='zookeeper:2181')
zk.start()

if zk.connected:
    print("zk connected")
else:
    print("Not able to connect to zk")

# if(zk.exists("/znodes")):
#     zk.delete("/znodes",recursive=True)

# print("All znodes deleted")

# Ensure a path, create if necessary
zk.ensure_path("/znodes")

# Create a node with data
# zk.create("/znodes/node_", b"a value", ephemeral=True, sequence=True)

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

def my_func(event):
    # check to see what the children are now
    print(event)
    children = zk.get_children("/znodes")
    print("There are %s children with names %s" % (len(children), children))

# Call my_func when the children change
children = zk.get_children("/znodes", watch=my_func)
print("There are %s children with names %s" % (len(children), children))

# if(zk.exists("/znodes/node_0000000000")):
#     zk.delete("/znodes/node_0000000000")
# else:
#     print("/znodes/node_0000000000 doesn't exist")

@app.route('/api/v1/inc',methods=["GET"])
def inc():

    inp={"table":"COUNT_NO","columns":["COUNTS"],"where":""}
    send=requests.post('http://localhost/api/v1/db_count/read',json=inp)
    res = send.content      
    res = eval(res)      
    count = int(res[0][0]) + 1     
    inp={"table":"COUNT_NO","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp) 
    inp={"table":"COUNT_NO","type":"insert","columns":["COUNTS"],"data":[count]}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    return Response("Incremented",status=200,mimetype="application/text")

@app.route('/api/v1/get_count',methods=["GET"])
def get_count():
    
    inp={"table":"COUNT_NO","columns":["COUNTS"],"where":""}
    send=requests.post('http://localhost/api/v1/db_count/read',json=inp)
    res = send.content   
    res = eval(res)
    # return int(res[0][0])
    return Response(str(res[0][0]),status=200,mimetype="application/text") 

@app.route('/api/v1/reset_count',methods=["GET"])
def reset_count(): 

    inp={"table":"COUNT_NO","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    inp={"table":"COUNT_NO","type":"insert","columns":["COUNTS"],"data":[0]}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    return Response("Count reseted",status=200,mimetype="application/text")

@app.route('/api/v1/change',methods=["GET"])
def change_flag():
     
    inp={"table":"FLAGS","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp) 
    inp={"table":"FLAGS","type":"insert","columns":["FLAG"],"data":[1]}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    return Response("Changed flag",status=200,mimetype="application/text")

@app.route('/api/v1/get_flag',methods=["GET"])
def get_flag():
    
    inp={"table":"FLAGS","columns":["FLAG"],"where":""}
    send=requests.post('http://localhost/api/v1/db_count/read',json=inp)
    res = send.content    
    res = eval(res)
    # return int(res[0][0])
    return Response(str(res[0][0]),status=200,mimetype="application/text") 

@app.route('/api/v1/reset_flag',methods=["GET"])
def reset_flag(): 

    inp={"table":"FLAGS","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    inp={"table":"FLAGS","type":"insert","columns":["FLAG"],"data":[0]}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    return Response("Flag reseted",status=200,mimetype="application/text")

@app.route('/api/v1/create/<num>',methods=["GET"])
def create_slave(num):
    client = docker.from_env()
    container = client.containers.run('master','',name="slave"+str(num),hostname="slave"+str(num),environment=["MYSQL_ROOT_PASSWORD=123"],network="pronet",detach=True)
    return Response("Slave created",status=200,mimetype="application/text")


@app.route('/api/v1/check',methods=["GET"])
def check():
    print("check called")
    send=requests.get('http://localhost/api/v1/get_count')
    res = eval(send.content)   
    # print(res)
    count = int(res)
    send=requests.get('http://localhost/api/v1/reset_count')
    send=requests.get('http://localhost/api/v1/worker/list')
    credential = send.content
    num_slaves = len(eval(credential))
    if(0<=count and count<=20):
        if(num_slaves>1):
            for x in range(num_slaves-1):
                send=requests.post('http://localhost/api/v1/crash/slave')
        elif(num_slaves<1):
            for x in range(1-num_slaves):
                create_slave(num_slaves+x+1)
    elif(21<=count and count<=40):
        if(num_slaves>2):
            for x in range(num_slaves-2):
                send=requests.post('http://localhost/api/v1/crash/slave')
        elif(num_slaves<2):
            for x in range(2-num_slaves):
                create_slave(num_slaves+x+1)
    elif(41<=count and count<=60):
        if(num_slaves>3):
            for x in range(num_slaves-3):
                send=requests.post('http://localhost/api/v1/crash/slave')
        elif(num_slaves<3):
            for x in range(3-num_slaves):
                create_slave(num_slaves+x+1)
    return Response("Scaled successfully",status=200,mimetype="application/text")
    
@app.route('/api/v1/db_count/write',methods=["POST"])
def write_db_count():
    db = pymysql.connect(**config)

    json = request.get_json()

    cur = db.cursor()

    if(json["type"]=="insert"):

        columns = json["columns"][0]
        data = str(json["data"][0])

        # for iter in range(1,len(json["columns"])):
        #     columns = columns + "," + json["columns"][iter]
        #     data = data + ",'" + json["data"][iter]+"'"

        sql = "INSERT INTO "+json["table"]+"("+columns+") VALUES ("+data+")"
    elif(json["type"]=="delete"):

        if json["where"]!="":
            sql = "DELETE FROM "+json["table"]+" WHERE "+json["where"]
        else:
            sql = "DELETE FROM "+json["table"]

    cur.execute(sql)
    #cur.execute("INSERT INTO LOGIN(username,password) VALUES ('Test','123')")
    db.commit()
    cur.close()
    db.close()
    return Response("1",status=200,mimetype="application/text")

@app.route('/api/v1/db_count/read',methods=["POST"])
def read_db_count():
    db = pymysql.connect(**config)

    json = request.get_json()

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
    print(results)
    results = list(map(list,results))
    cur.close()
    db.close()
    return Response(str(results),status=200,mimetype="application/text")

class RPC(object):

    def __init__(self,request_queue):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))

        self.channel = self.connection.channel()
        self.request_queue=request_queue
        result = self.channel.queue_declare(queue="responseQ", exclusive=True)

        self.channel.basic_consume(
            queue="responseQ",
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
                reply_to="responseQ",
                correlation_id=self.corr_id,
            ),
            body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return self.response


@app.route('/test')
def test():
    return "hi"

@app.route('/api/v1/db/write',methods=["POST"])
def write_db():
    write_rpc=RPC("writeQ")
    res=write_rpc.call(request.get_json())
    write_rpc.connection.close()
    return Response(res,status=200,mimetype="application/text")


@app.route('/api/v1/db/read',methods=["POST"])
def read_db():
    
    send=requests.get('http://localhost/api/v1/inc')
    send=requests.get('http://localhost/api/v1/get_flag')
    flag = int(eval(send.content))
    print(flag)
    if(flag==0):
        send=requests.get('http://localhost/api/v1/change')
        print("first time")
        # os.system('python scale.py')
        p = subprocess.Popen(['python', 'auto_scale.py'], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        
    # scheduler.print_jobs()
    # read_rpc=RPC("readQ")
    # res=read_rpc.call(request.get_json())
    # read_rpc.connection.close()
    # return Response(res,status=200,mimetype="application/text")
    return Response("Successfully read",status=200,mimetype="application/text")

@app.route('/api/v1/db/clear',methods=["POST"])
def clear_db():
    clear_rpc=RPC("writeQ")
    res=clear_rpc.call("clear")
    clear_rpc.connection.close()
    return Response(res,status=200,mimetype="application/text")

@app.route('/api/v1/crash/master',methods=["POST"])
def crash_master():
    client = docker.from_env()
    l=client.containers.list()
    l.sort(key=lambda x:x.attrs['State']['Pid'],reverse=True)
    res=[]
    for i in l:
      if i.name=='master':
        res.append(i.attrs['State']['Pid'])
        i.stop()
        break
    return jsonify(res)

@app.route('/api/v1/crash/slave',methods=["POST"])
def crash_slave():
    client = docker.from_env()
    l=client.containers.list()
    l.sort(key=lambda x:x.attrs['State']['Pid'],reverse=True)
    res=[]
    for i in l:
      if i.name not in ('master','orchestrator','zookeeper','rabbitmq'):
        res.append(i.attrs['State']['Pid'])
        i.stop()
        break
    return jsonify(res)

@app.route('/api/v1/worker/list',methods=["GET"])
def worker_list():
    client = docker.from_env()
    l=client.containers.list()
    l.sort(key=lambda x:x.attrs['State']['Pid'],reverse=True)
    res=[]
    for i in l:
      if i.name not in ('master','orchestrator','zookeeper','rabbitmq','orchestrator_db_1'):
        res.append(i.attrs['State']['Pid'])

    return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
