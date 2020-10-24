FROM    ubuntu:20.04
MAINTAINER  Xenya Lisovskaya xenya.lisovskaya@pm.me
RUN apt update
RUN DEBIAN_FRONTEND="noninteractive" apt -y dist-upgrade
RUN DEBIAN_FRONTEND="noninteractive" apt -y install python3-pip ssh
RUN ln -fs /usr/share/zoneinfo/America/Halifax /etc/localtime
RUN mkdir /bandwidth_tester
WORKDIR /bandwidth_tester
COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN ansible-galaxy collection install amazon.aws -p ./
RUN ansible-galaxy collection install community.aws -p ./
COPY bandwidth_tester.py .
COPY perf_tester_modules ./perf_tester_modules
COPY perf_tool.ini .
COPY ansible.cfg .
COPY playbooks ./playbooks
