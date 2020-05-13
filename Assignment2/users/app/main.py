from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint

app = Flask(__name__)
config = {
        'user': 'root',
        'password': '123',
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

# Function for testing
@app.route('/',methods=["GET"])
def test():
    return "hi"

# Function for listing users
@app.route('/api/v1/users',methods=["GET"])
def list_users():
    inp={"table":"LOGIN","columns":["USERNAME"],"where":""}
    send=requests.post('http://52.73.190.55:8080/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)

    if(len(credential)==0):
        return Response("No users found", status=204, mimetype='application/text')
    else:
        result=[]
        for i in range(0,len(credential)):
            result.append(credential[i][0])
        return jsonify(result)

# Function for adding a user
@app.route('/api/v1/users',methods=["PUT"])
def add_user():

    json = request.get_json()
    #print(json)

    if("username" not in json or "password" not in json):
        return Response("Wrong request format",status=400,mimetype='application/text')

    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":""}
    send=requests.post('http://52.73.190.55:8080/api/v1/db/read',json=inp)
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
        send=requests.post('http://52.73.190.55:8080/api/v1/db/write',json=inp)
        ret=send.json()
        #print(ret)
        return Response("User added",status=201, mimetype='application/text')

# Function for removing a user
@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):

    inp={"table":"LOGIN","columns":["USERNAME","PASSWORD"],"where":"USERNAME='"+username+"'"}
    send=requests.post('http://52.73.190.55:8080/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    #print(credential)
    if(len(credential)<1):
        return Response("Username not found", status=400, mimetype='application/text')
    else:
        inp={"table":"LOGIN","type":"delete","where":"USERNAME='"+username+"'"}
        send=requests.post('http://52.73.190.55:8080/api/v1/db/write',json=inp)
        ret=send.json()
        inp={"table":"USERS","type":"delete","where":"USERNAME='"+username+"'"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()
        inp={"table":"RIDES","type":"delete","where":"CREATEDBY='"+username+"'"}
        send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
        ret=send.json()

        return Response("Removed user %s !" %username, status=200, mimetype='application/text')

# Function for clearing data of users microservice from users db
@app.route('/api/v1/db/clear',methods=["POST"])
def clear_db():
    inp={"table":"LOGIN","type":"delete","where":""}
    send=requests.post('http://52.73.190.55:8080/api/v1/db/write',json=inp)
    ret=send.json()

    return Response("Cleared database", status=200, mimetype='application/text')

# Function for writing data of users microservice to users db
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

# Function for reading data of users microservice to users db
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
    #print(results)
    results = list(map(list,results))
    cur.close()
    db.close()
    return Response(str(results),status=200,mimetype="application/text")

if __name__ == '__main__':
    app.run()
