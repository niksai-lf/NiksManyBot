FROM python:3.10-slim

RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD nginx && python main.py
