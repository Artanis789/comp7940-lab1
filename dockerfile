FROM python:latest

COPY requirements.txt /

RUN pip install update pip

RUN pip install -r requirements.txt

COPY chatbot.py /

ENV ACCESS_TOKEN    6021929462:AAGu_0F6w5Zk2o0t0pcKknm8E0KECLBaOo8
ENV GPT_API         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
ENV DB_HOST         cook.mysql.database.azure.com
ENV DB_USER         comp7940
ENV DB_PWD          project7940!
ENV DATABASE        cook

CMD python chatbot.py