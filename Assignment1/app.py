from flask import Flask,render_template,jsonify,request,abort,Response
import pymysql
import requests
import ast
from datetime import datetime
from random import randint

db = pymysql.connect("localhost", "root", "", "Cloud")

app = Flask(__name__)

def is_sha1(maybe_sha):
    if len(maybe_sha) != 40:
        return False
    try:
        sha_int = int(maybe_sha, 16)
    except ValueError:
        return False
    return True

# def wrong(timestamp):


@app.route('/api/v1')
def start():
    inp={"table":"Login","columns":["username","password"],"where":""}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    return credential

@app.route('/api/v1/users',methods=["PUT"])
def add_user():

    json = request.get_json()

    if("username" not in json or "password" not in json):
        return Response("Wrong request format",status=400,mimetype='application/text')

    inp={"table":"Login","columns":["username","password"],"where":""}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
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
        inp={"table":"Login","columns":["username","password"],"data":[username,password],"type":"insert"}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/write',json=inp)
        ret=send.json()
        #print(ret)
        return Response("User added",status=201, mimetype='application/text')

@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):

    inp={"table":"Login","columns":["username","password"],"where":"username='"+username+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    #print(credential)
    if(len(credential)<1):
        return Response("Username not found", status=400, mimetype='application/text')
    else:
        inp={"table":"Login","type":"delete","where":"username='"+username+"'"}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/write',json=inp)
        ret=send.json()
        return Response("Removed user %s !" %username, status=200, mimetype='application/text')

@app.route('/api/v1/rides',methods=["POST"])
def create_ride():
    json = request.get_json()

    inp={"table":"Login","columns":["username","password"],"where":"username='"+json["created_by"]+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)

    #Check if timestamp in the correct format
    if("created_by" not in json or "timestamp" not in json or "source" not in json or "destination" not in json or len(credential)<1 or json["source"]=="" or json["destination"]=="" or int(json["source"])<1 or int(json["source"])>198 or int(json["destination"])<1 or int(json["destination"])>198 ):
        return Response("Wrong format",status=400,mimetype="application/text")
    else:
        rideId=randint(0, 10000)
        inp={"table":"Rides","columns":["RideId","CreatedBy"],"where":"RideId='"+str(rideId)+"'"}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
        res=send.content
        print(res)
        while len(res)>5:
            print(res)
            rideId=randint(0, 10000)
            inp={"table":"Rides","columns":["RideId","CreatedBy","timestamp"],"where":"RideId='"+str(rideId)+"'"}
            send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
            res=send.content
        inp={"table":"Rides","type":"insert","columns":["RideId","CreatedBy","Timestamp","Source","Destination"],"data":[str(rideId),json["created_by"],json["timestamp"],json["source"],json["destination"]]}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/write',json=inp)
        ret=send.json()
        inp={"table":"Users","type":"insert","columns":["RideId","username"],"data":[str(rideId),json["created_by"]]}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/write',json=inp)
        ret=send.json()
        return Response("Ride created",status=201,mimetype="application/text")

@app.route('/api/v1/rides',methods=["GET"])
def list_rides():
    
    source = request.args.get("source")
    destination = request.args.get("destination")

    if(source=="" or destination=="" or int(source)<1 or int(source)>198 or int(destination)<1 or int(destination)>198 ):
        return Response("Wrong/Empty src or dest",status=400,mimetype="application/text")
    
    inp={"table":"Rides","columns":["RideId","CreatedBy","timestamp"],"where":"source='"+source+"' AND destination='"+destination+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    res=send.content
    res=eval(res)

    result=[]
    
    for i in range(0,len(res)):
        datetimeObj = datetime.strptime(res[i][2], '%d-%m-%Y:%S-%M-%H')
        if datetimeObj>datetime.now():
            #result.append(res[i])
            temp = {}
            temp["rideId"] = res[i][0]
            temp["username"] = res[i][1]
            temp["timestamp"] = res[i][2]
            result.append(temp)
        

    if(len(result)==0):
        return Response("No match found",status=204,mimetype="application/text")
    else:
        return jsonify(result)

@app.route('/api/v1/rides/<rideId>',methods=["GET"])
def details_ride(rideId):

    
    inp={"table":"Rides","columns":["RideId"],"where":"RideId='"+rideId+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
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
        inp={"table":"Rides","columns":["RideId","CreatedBy","Timestamp","source","destination"],"where":"RideId='"+str(rideId)+"'"}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
        res=send.content
        res=eval(res)

        inp={"table":"users","columns":["username"],"where":"RideId='"+str(rideId)+"'"}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
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
    inp={"table":"Login","columns":["username","password"],"where":"username='"+json["username"]+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    credential=send.content
    credential=eval(credential)
    inp={"table":"Rides","columns":["RideId"],"where":"RideId='"+rideId+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    ride=send.content
    ride=eval(ride)
    rideId = int(rideId)
    if(len(ride)==0 or "username" not in json or len(credential)<1):
        return Response("Wrong rideId/username",status=204,mimetype="application/text")
    else:
        inp={"table":"Users","type":"insert","columns":["RideId","username"],"data":[str(rideId),json["username"]]}
        send=requests.post('http://127.0.0.1:5000/api/v1/db/write',json=inp)
        ret=send.json()
        #rides[rideId][4].append(json["username"])
        return Response("Joined ride",status=200,mimetype="application/text")

@app.route('/api/v1/rides/<rideId>',methods=["DELETE"])
def delete_ride(rideId):

    inp={"table":"Rides","columns":["RideId"],"where":"RideId='"+rideId+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/read',json=inp)
    ride=send.content
    ride=eval(ride)
    rideId = int(rideId)
    #if(len(ride)==0):
    #    return Response("Wrong rideId",status=204,mimetype="application/text")
    #else:
    inp={"table":"Rides","type":"delete","where":"RideId='"+str(rideId)+"'"}
    send=requests.post('http://127.0.0.1:5000/api/v1/db/write',json=inp)
    ret=send.json()
    return Response("Deleted ride",status=200,mimetype="application/text")

@app.route('/api/v1/db/write',methods=["POST"])
def write_db():
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
    #cur.execute("INSERT INTO Login(username,password) VALUES ('Test','123')")
    db.commit()
    cur.close()

    return Response("1",status=200,mimetype="application/text")

@app.route('/api/v1/db/read',methods=["POST"])
def read_db():
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

    return Response(str(results),status=200,mimetype="application/text")

if __name__ == '__main__':
    app.debug=True
    app.run()