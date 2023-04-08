FROM python:latest

COPY requirements.txt /

RUN pip install update pip

RUN pip install -r requirements.txt

COPY chatbot.py /

RUN mkdir /images

CMD python chatbot.py