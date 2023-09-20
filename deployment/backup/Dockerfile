FROM ubuntu:18.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    nano \
    less \
    vim wget ca-certificates cron lsb-release gnupg2 

RUN  echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends postgresql-client  && \
    apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/* 

WORKDIR /COPO

RUN wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu1804-x86_64-100.8.0.deb
RUN apt-get install ./mongodb-database-tools-*-100.8.0.deb
# create backup directories
RUN mkdir -p /backup/mongo
RUN mkdir -p /backup/postgres


# set up cron jobs
ADD crontab.txt crontab.txt
ADD script.sh   script.sh
ADD restore.sh  restore.sh

RUN chmod 755 script.sh restore.sh

RUN /usr/bin/crontab /COPO/crontab.txt