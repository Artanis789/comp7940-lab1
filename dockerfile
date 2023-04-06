FROM python:latest

COPY requirements.txt /

RUN pip install update pip

RUN pip install -r requirements.txt

COPY chatbot.py /

RUN mkdir /images

ENV ACCESS_TOKEN    6021929462:AAGu_0F6w5Zk2o0t0pcKknm8E0KECLBaOo8
ENV DB_HOST         cook.mysql.database.azure.com
ENV DB_USER         comp7940
ENV DB_PWD          project7940!
ENV DATABASE        cook

CMD python chatbot.py