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

zk.create("/znodes/node_", b"a value", ephemeral=True, sequence=True)    

bashCommandName = 'hostname'
output = subprocess.check_output(['bash','-c', bashCommandName]) 
#print(output)
output = output.decode("utf-8")
#print(type(output))
output = output.strip('\n')
print(output)
#output = 'slave1'

config = {'user': 'root','password': '123','host': output,'port': 3306,'database': 'CLOUD'} 

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
        self.channel.basic_publish(
            exchange='',
            routing_key=self.request_queue,
            properties=pika.BasicProperties(
                reply_to="returnQ2",
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
    #print(results)
    results = list(map(list,results))
    cur.close()
    db.close()
    return results

def on_request_master(ch, method, props, body):
    print(body)
    body=eval(body)
    if body == 'clear':
        data=clear_db()
    else:
        data=write_db(body)
    
    print(data)
    sync_rpc=RPC("syncQ")
    sync_rpc.call(body)
    sync_rpc.connection.close()
    #channel.queue_declare(queue="syncQ", exclusive=True)
    #channel.basic_publish(exchange='', routing_key=request_queue, body=body)

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

    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=str(data))
    ch.basic_ack(delivery_tag=method.delivery_tag)

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
    channel.queue_declare(queue='syncQ')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='readQ', on_message_callback=on_request_slave_read)
    channel.basic_consume(queue='syncQ', on_message_callback=on_request_slave_sync)

    print("Awaiting requests")
    channel.start_consuming()

connection.close()
"""
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq'))

channel = connection.channel()

channel.queue_declare(queue='writeQ')
channel.queue_declare(queue='readQ')

def on_request(ch, method, props, body):

    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=body)
    data=send.content
    response=eval(data)
    return data

    print(" [.] fib(%s)" % n)
    
    ch.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = \props.correlation_id), body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='writeQ', on_message_callback=on_request)

print(" [x] Awaiting RPC requests")
channel.start_consuming()


def is_sha1(maybe_sha):
    if len(maybe_sha) != 40:
        return False
    try:
        sha_int = int(maybe_sha, 16)
    except ValueError:
        return False
    return True

# def wrong(timestamp):
@app.route('/')
def test():
    return "hi"

@app.route('/api/v1')
def start():
    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":""}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    return credential

@app.route('/api/v1/users',methods=["PUT"])
def add_user():

    json = request.get_json()

    if("username" not in json or "password" not in json):
        return Response("Wrong request format",status=400,mimetype='application/text')

    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":""}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)

    username = request.get_json()["username"]
    password = request.get_json()["password"]

    for i in range(0,len(credential)):
        if(username in credential[i]):
            return Response("Username already exists", status=400, mimetype='application/text')

    if(is_sha1(password)==False):
        return Response("Wrong password format", status=400, mimetype='application/text')  
    
    else:       
        inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"data":[username,password],"type":"insert"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()
        #print(ret)
        return Response("User added",status=201, mimetype='application/text')

@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):

    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":"USERNAME='"+username+"'"}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    #print(credential)
    if(len(credential)<1):
        return Response("Username not found", status=400, mimetype='application/text')
    else:
        inp={"table":"LOGIN","type":"delete","where":"USERNAME='"+username+"'"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()
        return Response("Removed user %s !" %username, status=200, mimetype='application/text')

@app.route('/api/v1/rides',methods=["POST"])
def create_ride():
    json = request.get_json()

    #inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":"USERNAME='"+json["created_by"]+"'"}
    send=requests.get('http://52.73.190.55:8080/api/v1/users')
    #SEND REQUEST to list all users
    credential=send.content
    credential=eval(credential)

    #Check if timestamp in the correct format
    if("created_by" not in json or "timestamp" not in json or "source" not in json or "destination" not in json or json["created_by"] not in credential or json["source"]=="" or json["destination"]=="" or int(json["source"])<1 or int(json["source"])>198 or int(json["destination"])<1 or int(json["destination"])>198 ):
        return Response("Wrong format",status=400,mimetype="application/text")
    else:
        rideId=randint(0, 10000)
        inp={"table":"RIDES","columns":["RIDEID","CREATEDBY"],"where":"RIDEID='"+str(rideId)+"'"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
        res=send.content
        print(res)
        while len(res)>5:
            print(res)
            rideId=randint(0, 10000)
            inp={"table":"RIDES","columns":["RIDEID","CREATEDBY","timestamp"],"where":"RIDEID='"+str(rideId)+"'"}
            send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
            res=send.content
        inp={"table":"RIDES","type":"insert","columns":["RIDEID","CREATEDBY","TIMESTAMPS","SOURCE","DESTINATION"],"data":[str(rideId),json["created_by"],json["timestamp"],json["source"],json["destination"]]}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()
        inp={"table":"USERS","type":"insert","columns":["RIDEID","USERNAME"],"data":[str(rideId),json["created_by"]]}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()
        return Response("Ride created",status=201,mimetype="application/text")

@app.route('/api/v1/rides',methods=["GET"])
def list_rides():
    
    source = request.args.get("source")
    destination = request.args.get("destination")
    if(source=="" or destination=="" or int(source)<1 or int(source)>198 or int(destination)<1 or int(destination)>198 ):
        return Response("Wrong/Empty src or dest",status=400,mimetype="application/text")
    
    inp={"table":"RIDES","columns":["RIDEID","CREATEDBY","TIMESTAMPS"],"where":"SOURCE="+source+" AND DESTINATION="+destination}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    res=send.content
    res=eval(res)
    result=[]
    
    for i in range(0,len(res)):
        datetimeObj = datetime.strptime(res[i][2], '%d-%m-%Y:%S-%M-%H')
        #return str(datetimeObj)+" "+str(datetime.now())
        if datetimeObj>datetime.now():
            #result.append(res[i])
            temp = {}
            temp["rideId"] = res[i][0]
            temp["USERNAME"] = res[i][1]
            temp["timestamp"] = res[i][2]
            result.append(temp)
    if(len(result)==0):
        return Response("No match found",status=204,mimetype="application/text")
    else:
        return jsonify(result)

@app.route('/api/v1/rides/<rideId>',methods=["GET"])
def details_ride(rideId):

    
    inp={"table":"RIDES","columns":["RIDEID"],"where":"RIDEID='"+rideId+"'"}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    res=send.content
    res=eval(res)

    rideId = int(rideId)
    flag=0
    
    for i in range(0,len(res)):
        if(rideId in res[i]):
            flag+=1
    if flag==0:
        return Response("No match found",status=204,mimetype="application/text")
    else:
        inp={"table":"RIDES","columns":["RIDEID","CREATEDBY","TIMESTAMPS","SOURCE","DESTINATION"],"where":"RIDEID='"+str(rideId)+"'"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
        res=send.content
        res=eval(res)

        inp={"table":"USERS","columns":["USERNAME"],"where":"RIDEID='"+str(rideId)+"'"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
        riders=send.content
        riders=eval(riders)

        temp = {}
        temp["rideId"] = res[0][0]
        temp["created_by"] = res[0][1]

        ride=[]
        for i in range(0,len(riders)):
            ride.append(riders[i][0])

        temp["users"] = ride
        temp["timestamp"] = res[0][2]
        temp["source"] = res[0][3]
        temp["destination"] = res[0][4]

        return jsonify(temp)

@app.route('/api/v1/rides/<rideId>',methods=["POST"])
def join_ride(rideId):
    json = request.get_json()
    #inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":"USERNAME='"+json["username"]+"'"}
    send=requests.get('http://52.73.190.55:8080/api/v1/users')
    #SEND REQUEST to list rides
    credential=send.content
    credential=eval(credential)
    inp={"table":"RIDES","columns":["RIDEID"],"where":"RIDEID='"+rideId+"'"}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    ride=send.content
    ride=eval(ride)
    
    inp={"table":"USERS","columns":["USERNAME"],"where":"RIDEID='"+rideId+"'"}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    user=send.content
    user=eval(user)
    rideId = int(rideId)
    if(len(ride)==0 or "username" not in json or json["username"] not in credential or any(json["username"] in username for username in user)):
        return Response("Wrong rideId/username",status=204,mimetype="application/text")
    else:
        inp={"table":"USERS","type":"insert","columns":["RIDEID","USERNAME"],"data":[str(rideId),json["username"]]}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()
        #rides[rideId][4].append(json["username"])
        return Response("Joined ride",status=200,mimetype="application/text")

@app.route('/api/v1/rides/<rideId>',methods=["DELETE"])
def delete_ride(rideId):

    inp={"table":"RIDES","columns":["RIDEID"],"where":"RIDEID='"+rideId+"'"}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/read',json=inp)
    ride=send.content
    ride=eval(ride)
    rideId = int(rideId)
    #if(len(ride)==0):
    #    return Response("Wrong rideId",status=204,mimetype="application/text")
    #else:
    inp={"table":"RIDES","type":"delete","where":"RIDEID='"+str(rideId)+"'"}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
    ret=send.json()
    return Response("Deleted ride",status=200,mimetype="application/text")



@app.route('/api/v1/db/write',methods=["POST"])
def write_db():
    db = pymysql.connect(**config)

    json = request.get_json()

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
    #cur.execute("INSERT INTO LOGIN(username,password) VALUES ('Test','123')")
    db.commit()
    cur.close()
    db.close()
    return Response("1",status=200,mimetype="application/text")

def read_db(json):
    db = pymysql.connect(**config)

    #json = request.get_json()

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
    #return Response(str(results),status=200,mimetype="application/text")
    return results

@app.route('/api/v1/db/clear',methods=["POST"])
def clear_db():
    inp={"table":"RIDES","type":"delete", "where":""}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
    ret=send.json()

    inp={"table":"USERS","type":"delete", "where":""}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
    ret=send.json()

    return Response("Cleared database", status=200, mimetype='application/text')
"""
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
