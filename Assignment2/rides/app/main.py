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
        'host': 'db_ride',
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
@app.route('/')
def test():
    return "hi"

# Function for creating a new ride
@app.route('/api/v1/rides',methods=["POST"])
def create_ride():
    json = request.get_json()
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

# Function for listing all future rides
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

# Function to get the details of a particular ride
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

# Function for adding user to a ride
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

# Function to delete a ride
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

# Function for writing data to database
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

# Function for reading data from database
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

# Function for clearing the database
@app.route('/api/v1/db/clear',methods=["POST"])
def clear_db():
    inp={"table":"RIDES","type":"delete", "where":""}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
    ret=send.json()

    inp={"table":"USERS","type":"delete", "where":""}
    send=requests.post('http://52.73.190.55:8000/api/v1/db/write',json=inp)
    ret=send.json()

    return Response("Cleared database", status=200, mimetype='application/text')

if __name__ == '__main__':
    app.run()
