from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
import os
from datetime import datetime
from random import randint
import json

app = Flask(__name__)
config = {
        'user': 'root',
        'host': 'db_user',
        'port': 3306,
        'database': 'CLOUD'
    }

# Function to check whether password is in sha format or not
def is_sha1(maybe_sha):
    if len(maybe_sha) != 40:
        return False
    try:
        sha_int = int(maybe_sha, 16)
    except ValueError:
        return False
    return True

# Load balancer health checks
@app.route('/',methods=["GET"])
def health():
    return Response("OK",status=200, mimetype='application/text')

# Function for testing old count logic
@app.route('/test',methods=["GET"])
def test():
    try:
        f=open("../COUNT/count","r")
        count_old=int(f.read())
        count_new=count_old+1
        f.close()
    except:
        count_old=0
        count_new=1
    f=open("../COUNT/count","w")
    f.write(str(count_new))
    f.close()
    return str(count_old)

# Function for incrementing count of requests to user microservice
@app.route('/inc',methods=["POST"])
def inc():

    inp={"table":"COUNT_NO","columns":["COUNTS"],"where":""}
    send=requests.post('http://localhost/api/v1/db/read',json=inp)
    res = send.content      
    res = eval(res)      
    count = int(res[0][0]) + 1     
    inp={"table":"COUNT_NO","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db/write',json=inp) 
    inp={"table":"COUNT_NO","type":"insert","columns":["COUNTS"],"data":[count]}
    send=requests.post('http://localhost/api/v1/db/write',json=inp)
    return Response("Incremented",status=200,mimetype="application/text")

# Function for getting count of requests to user microservice
@app.route('/api/v1/_count',methods=["GET"])
def get_count():

    inp={"table":"COUNT_NO","columns":["COUNTS"],"where":""}
    send=requests.post('http://localhost/api/v1/db/read',json=inp)
    res = send.content
    res = eval(res)

    result = []
    result.append(res[0][0])
    return json.dumps(result)

# Function for reseting count of requests to user microservice
@app.route('/api/v1/_count',methods=["DELETE"])
def reset_count():

    inp={"table":"COUNT_NO","type":"delete","where":""}
    send=requests.post('http://localhost/api/v1/db/write',json=inp)
    inp={"table":"COUNT_NO","type":"insert","columns":["COUNTS"],"data":[0]}
    send=requests.post('http://localhost/api/v1/db/write',json=inp)
    return Response("Count reseted",status=200,mimetype="application/text")

# Function for listing users
@app.route('/api/v1/users',methods=["GET"])
def list_users():

    requests.post('http://localhost/inc')

    inp={"table":"LOGIN","columns":["USERNAME"],"where":""}
    send=requests.post('http://'+ os.environ['DBAAS_IP'] +'/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)

    if(len(credential)==0):
        return Response("No users found", status=204, mimetype='application/text')
    else:
        result=[]
        for i in range(0,len(credential)):
            result.append(credential[i][0])
        return jsonify(result)
    return 'OK'

# Function for adding a user
@app.route('/api/v1/users',methods=["PUT"])
def add_user():

    json = request.get_json()

    requests.post('http://localhost/inc')

    if("username" not in json or "password" not in json):
        return Response("Wrong request format",status=400,mimetype='application/text')

    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":""}
    send=requests.post('http://'+os.environ['DBAAS_IP']+'/api/v1/db/read',json=inp)
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
        send=requests.post('http://'+os.environ['DBAAS_IP']+'/api/v1/db/write',json=inp)
        ret=send.json()
        return Response("User added",status=201, mimetype='application/text')

# Function for handling requests sent with wrong methods
@app.route('/api/v1/users',methods=["CONNECT","PATCH","HEAD","OPTIONS","TRACE","POST"])
def noneofabove():

    requests.post('http://localhost/inc')

    return Response("Method not allowed", status=405, mimetype='application/text')

# Function for removing a user
@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):

    requests.post('http://localhost/inc')

    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":"USERNAME='"+username+"'"}
    send=requests.post('http://'+os.environ['DBAAS_IP']+'/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    if(len(credential)<1):
        return Response("Username not found", status=400, mimetype='application/text')
    else:
        inp={"table":"LOGIN","type":"delete","where":"USERNAME='"+username+"'"}
        send=requests.post('http://'+os.environ['DBAAS_IP']+'/api/v1/db/write',json=inp)
        ret=send.json()
        inp={"table":"RIDES","type":"delete","where":"CREATEDBY='"+username+"'"}
        send=requests.post('http://52.202.21.91/api/v1/db/write',json=inp)
        ret=send.json()

        return Response("Removed user %s !" %username, status=200, mimetype='application/text')

# Function for writing count of requests to users microservice to users db
@app.route('/api/v1/db/write',methods=["POST"])
def write_db():
    db = pymysql.connect(**config)

    json = request.get_json()

    cur = db.cursor()

    if(json["type"]=="insert"):

        columns = json["columns"][0]
        data = str(json["data"][0])

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

# Function for reading count of requests to users microservice from users db
@app.route('/api/v1/db/read',methods=["POST"])
def read_db():
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
    results = list(map(list,results))
    cur.close()
    db.close()
    return Response(str(results),status=200,mimetype="application/text")

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
