from flask import Flask,render_template,jsonify,request,abort,Response
import requests
import atexit
import time
import os
import random
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)



def my_check():
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
                # create_slave(num_slaves+x+1)
                send=requests.get('http://localhost/api/v1/create/'+str(random.randrange(20, 1000, 1)))
    elif(21<=count and count<=40):
        if(num_slaves>2):
            for x in range(num_slaves-2):
                send=requests.post('http://localhost/api/v1/crash/slave')
        elif(num_slaves<2):
            for x in range(2-num_slaves):
                # create_slave(num_slaves+x+1)
                send=requests.get('http://localhost/api/v1/create/'+str(random.randrange(20, 1000, 1)))
    elif(41<=count and count<=60):
        if(num_slaves>3):
            for x in range(num_slaves-3):
                send=requests.post('http://localhost/api/v1/crash/slave')
        elif(num_slaves<3):
            for x in range(3-num_slaves):
                # create_slave(num_slaves+x+1)
                send=requests.get('http://localhost/api/v1/create/'+str(random.randrange(20, 1000, 1)))

# def start():
#     scheduler = BackgroundScheduler(daemon=True)
#     scheduler.add_job(func=my_check, trigger="interval", minutes=2)
#     scheduler.start()
#     scheduler.print_jobs()
#     # Shut down the scheduler when exiting the app
#     # atexit.register(lambda: scheduler.shutdown())
    
if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(my_check, 'interval', minutes=2)
    scheduler.start()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()