FROM python:latest

COPY chatbot.py /

COPY requirements.txt /

RUN pip install update pip

RUN pip install -r requirements.txt

ENV ACCESS_TOKEN    6117411175:AAGmJeNoCE5NUjJIyONCQPj7S3-6tPEM9ng
ENV REDIS_HOST      redis-11576.c11.us-east-1-3.ec2.cloud.redislabs.com
ENV REDIS_PASSWORD  91m3dAeaFj3Hge6BFeWRmeqzoV59yPnG
ENV REDIS_PORT      11576
ENV GPT_API         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

CMD python chatbot.py