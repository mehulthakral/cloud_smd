FROM mysql:5.7

COPY ./app /app

RUN apt-get update && apt-get install -y python3
RUN apt-get update && apt-get install -y python3-pip

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ENTRYPOINT [ "python3", "/app/main.py" ]
