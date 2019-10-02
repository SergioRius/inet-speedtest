FROM python:alpine
LABEL maintainer="sergio.rius@hotmail.com"

VOLUME /src/
COPY influxspeedtest.py requirements.txt /src/
ADD influxspeedtest /src/influxspeedtest
WORKDIR /src

RUN pip install -r requirements.txt

ENV DELAY 300
ENV INFLUXDB_HOST 127.0.0.1
ENV INFLUXDB_PORT 8086
ENV INFLUXDB_DATABASE speedtest
ENV INFLUXDB_MEASUREMENT speedtest
ENV INFLUXDB_USR ""
ENV INFLUXDB_PWD ""
ENV INFLUXDB_SSL False
ENV INFLUXDB_VERIFYSSL True
ENV SPEEDTEST_SERVER ""
ENV LOG_LEVEL info

CMD ["python", "-u", "/src/influxspeedtest.py"]
