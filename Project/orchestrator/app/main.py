from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint
import pika
import docker
import uuid
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
config = {
        'user': 'root',
        'password': '123',
        'host': 'orchestrator',
        'port': 3306,
        'database': 'CLOUD'
    }
flag = 0

@app.route('/api/v1/inc',methods=["GET"])
def inc():
    inp={"table":"COUNT_NO","columns":["COUNTS"],"where":""}
    send=requests.post('http://localhost/api/v1/db_count/read',json=inp)
    res = send.content      
    res = eval(res)      
    res[0][0] = res[0][0] + 1     
    inp={"table":"COUNT_NO","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp) 
    inp={"table":"COUNT_NO","type":"insert","columns":["COUNTS"],"data":[res[0][0]]}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    # try:
    #     f=open("../COUNT/count","r")
    #     count_old=int(f.read())
    #     count_new=count_old+1
    #     f.close()
    # except:
    #     print("Problem in opening file")
    #     count_old=0
    #     count_new=1
    # f=open("../COUNT/count","w")
    # f.write(str(count_new))
    # f.close()

@app.route('/api/v1/get_count',methods=["GET"])
def get_count():
    
    inp={"table":"COUNT_NO","columns":["COUNTS"],"where":""}
    send=requests.post('http://localhost/api/v1/db_count/read',json=inp)
    res = send.content    
    res = eval(res)
    return res[0][0] 
    # try:
    #     f=open("../COUNT/count","r")
    #     count_old=int(f.read())
    #     f.close()
    # except:
    #     count_old=0
    #     print("Not able to open file")

    # return count_old

@app.route('/api/v1/reset',methods=["GET"])
def reset_count(): 

    inp={"table":"COUNT_NO","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)
    inp={"table":"COUNT_NO","type":"insert","columns":["COUNTS"],"data":[0]}
    send=requests.post('http://localhost/api/v1/db_count/write',json=inp)

    # try:
    #     f=open("../COUNT/count","w")
    #     f.write("0")
    #     f.close()
    # except:
    #     # return Response("Not able to write file")
    #     print("Not able to write file")

    # return Response("Count reseted", status=200, mimetype='application/text')

@app.route('/api/v1/create',methods=["GET"])
def create_slave(num):
    client = docker.from_env()
    container = client.containers.run('master',name="slave"+str(num),hostname="slave"+str(num),environment=["MYSQL_ROOT_PASSWORD=123"],network="pronet",detach=True)

@app.route('/api/v1/check',methods=["GET"])
def check():
    count = get_count()
    reset_count()
    send=requests.get('http://localhost/api/v1/worker/list')
    credential = send.content
    num_slaves = len(eval(credential)[0])
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
    
@app.route('/api/v1/db_count/write',methods=["POST"])
def write_db_count():
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
    #print(results)
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
            routing_key=self.response_queue,
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
    res=write_rpc.call(request)
    return Response(res,status=200,mimetype="application/text")


@app.route('/api/v1/db/read',methods=["POST"])
def read_db():

    inc()
    global flag
    if(flag==0):
        flag = 1
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=check, trigger="interval", seconds=120)
        scheduler.start()

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

    write_rpc=RPC("readQ")
    res=write_rpc.call(request)
    return Response(res,status=200,mimetype="application/text")

@app.route('/api/v1/db/clear',methods=["POST"])
def clear_db():
    write_rpc=RPC("writeQ")
    res=write_rpc.call("clear")
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
      if i.name not in ('master','orchestrator','zookeeper','rabbitmq'):
        res.append(i.attrs['State']['Pid'])

    return jsonify(res)

if __name__ == '__main__':
    app.run()
