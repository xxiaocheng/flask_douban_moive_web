FROM python:3.6-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y python3-pip && \
    pip3 install pipenv && \
    pipenv install --system && chmod +x boot.sh

# EXPOSE 5000

# CMD flask run --host=0.0.0.0
