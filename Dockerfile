FROM centos

ENV HOME=/home/watchDogs
ENV GOOGLE_CHROME_VERSION=94.0.4606.54

WORKDIR /etc/yum.repos.d/
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-*
RUN sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-*

WORKDIR /var/cache/dnf
RUN rm -rf ./*
RUN dnf install yum -y

RUN yum install epel-release -y
RUN yum install wget -y
RUN yum install python3 -y
RUN yum install python3-pip -y
RUN yum install Xvfb -y
RUN yum install -y https://dl.google.com/linux/chrome/rpm/stable/x86_64/google-chrome-stable-${GOOGLE_CHROME_VERSION}-1.x86_64.rpm

WORKDIR ${HOME}
ADD ./requirements.txt ./
ADD ./chromedriver ./chromedriver 
ADD ./start_services.sh ./
COPY ./masterOfMalts ./masterOfMalts

RUN pip3 install -r requirements.txt

ENV DISPLAY=:6501
RUN Xvfb :6501 &