from flask import Flask,render_template,jsonify,request,abort,Response

app = Flask(__name__)

credentials = {}
rides = []

def is_sha1(maybe_sha):
    if len(maybe_sha) != 40:
        return False
    try:
        sha_int = int(maybe_sha, 16)
    except ValueError:
        return False
    return True

@app.route('/api/v1')
def start():
    return jsonify(credentials)

@app.route('/api/v1/users',methods=["PUT"])
def add_user():

    json = request.get_json()

    if("username" not in json or "password" not in json):
        return Response("Wrong request format",status=400,mimetype='application/text')

    username = request.get_json()["username"]
    password = request.get_json()["password"]

    if(username in credentials):
        return Response("Username already exists", status=400, mimetype='application/text')

    elif(is_sha1(password)==False):
        return Response("Wrong password format", status=400, mimetype='application/text')  
    
    else:       
        credentials[username] = password
        return Response("User added len: "+ str(len(credentials))+" with username " + username + " password: " + password,status=201, mimetype='application/text')

@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):

    if(username not in credentials):
        return Response("Username not found", status=400, mimetype='application/text')
    else:
        """To Do in Database - Delete rides of this user"""
        """To Do in Database - Remove this user from upcoming joined rides"""
        del credentials[username]
        return Response("Removed user %s !" %username, status=200, mimetype='application/text')

@app.route('/api/v1/rides',methods=["POST"])
def create_ride():
    json = request.get_json()

    if("created_by" not in json or "timestamp" not in json or "source" not in json or "destination" not in json or json["created_by"] not in credentials):
        return Response("Wrong format",status=400,mimetype="application/text")
    else:
        rides.append([json["created_by"],json["timestamp"],json["source"],json["destination"],[json["created_by"]]])
        return Response("Ride created len- %d"%len(rides),status=200,mimetype="application/text")

@app.route('/api/v1/rides',methods=["GET"])
def list_rides():
    
    source = request.args.get("source")
    destination = request.args.get("destination")

    if(source=="" or destination=="" or int(source)<1 or int(source)>198 or int(destination)<1 or int(destination)>198 ):
        return Response("Wrong/Empty src or dest",status=400,mimetype="application/text")
    
    # source = int(source)
    # destination = int(destination)
    res = []
    for i in range(len(rides)):
        if(rides[i][2]==source and rides[i][3]==destination):
            temp = {}
            temp["rideId"] = i
            temp["username"] = rides[i][0]
            temp["timestamp"] = rides[i][1]
            res.append(temp)
    if(len(res)==0):
        return Response("No match found",status=204,mimetype="application/text")
    else:
        return jsonify(res)

@app.route('/api/v1/rides/<rideId>',methods=["GET"])
def details_ride(rideId):

    rideId = int(rideId)
    if(len(rides)<=rideId):
        return Response("No match found",status=204,mimetype="application/text")
    else:
        temp = {}
        temp["rideId"] = rideId
        temp["Created_by"] = rides[rideId][0]
        temp["users"] = rides[rideId][4]
        temp["Timestamp"] = rides[rideId][1]
        temp["source"] = rides[rideId][2]
        temp["destination"] = rides[rideId][3]
        return jsonify(temp)

@app.route('/api/v1/rides/<rideId>',methods=["POST"])
def join_ride(rideId):
    json = request.get_json()
    rideId = int(rideId)
    if(len(rides)<=rideId or "username" not in json or json["username"] not in credentials):
        return Response("Wrong rideId/username",status=204,mimetype="application/text")
    else:
        rides[rideId][4].append(json["username"])
        return Response("Joined ride",status=200,mimetype="application/text")

@app.route('/api/v1/rides/<rideId>',methods=["DELETE"])
def delete_ride(rideId):

    rideId = int(rideId)
    if(len(rides)<=rideId):
        return Response("Wrong rideId",status=204,mimetype="application/text")
    else:
        del rides[rideId]
        return Response("Deleted ride",status=200,mimetype="application/text")

if __name__ == '__main__':
    app.debug=True
    app.run()