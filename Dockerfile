FROM ubuntu:14.04

RUN apt-get update
RUN apt-get install -y python python-pip
RUN pip install Flask
RUN apt-get install -y python-yaml

COPY generic_aiml /generic_aiml
COPY futurist_aiml /futurist_aiml
COPY server /server
COPY docker-entrypoint.sh /

EXPOSE 8001

ENTRYPOINT ["bash", "/docker-entrypoint.sh"]

CMD ["python", "/server/run.py"]
