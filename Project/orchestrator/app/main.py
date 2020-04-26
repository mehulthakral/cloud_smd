from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint
import pika
import docker
import uuid
app = Flask(__name__)

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


@app.route('/')
def test():
    return "hi"

@app.route('/api/v1/db/write',methods=["POST"])
def write_db():
    write_rpc=RPC("writeQ")
    res=write_rpc.call(request)
    return Response(res,status=200,mimetype="application/text")


@app.route('/api/v1/db/read',methods=["POST"])
def read_db():
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
