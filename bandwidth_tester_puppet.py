#!/usr/bin/env python3
import iperf3
import pickle
import socket
import threading
import sys
import time
import argparse

host2BindAdress = '0.0.0.0'
commandPort = 1919
dataReportPort = 1921
#host2BindAdress = sys.argv[1]
#commandPort = sys.argv[2]
#dataReportPort = sys.argv[3]

testResults = {}
awaitingResults = True

def launchIperf3Client(**kwargs):
    print(f"iperf client, args: {kwargs}")
    client = iperf3.Client()
    client.duration = kwargs['durationSecs']
    client.server_hostname = kwargs['iperf3ServerHost']
    client.port = kwargs['iperf3ServerPort']
    client.num_streams = kwargs['numStreams']
    res = client.run()
    awaitingResults = False
    testResults = res.json

def launchIperf3Server(**kwargs):
    print(f"iperf server, kwargs: {kwargs}")
    iperfServer = iperf3.Server()
    iperfServer.bind_address = kwargs['iperf3BindAddress']
    iperfServer.port = kwargs['iperf3ServerPort']
    iperfServer.verbose = False
    res = None
    try:
        res = iperfServer.run()
        res = res.json
    except:
        print('it fails!')
    print("writing results")
    print(type(testResults))
    testResults = res

def dataSender(conn,_):
    pickledResults = pickle.dumps(testResults)
    print("launch sender to send results: {testResults}")
    conn.send(pickledResults)
    awaitingResults = False
    print('Send Successful')
    conn.close()

def dataReceiver(conn,_):
    print("launch receiver")
    pickledConf = b''
    while True:
        netChunk = conn.recv(1024)
        if not netChunk:
            break
        pickledConf += netChunk
    conn.close()
    unPickledConf = pickle.loads(pickledConf)
    print(f"dict_pickled type is: {type(unPickledConf)} \n\n data itself is {unPickledConf}")
    payloadFunc = None
    if unPickledConf['mode'] == 'server':
        payloadFunc = threading.Thread(target=launchIperf3Server, kwargs=unPickledConf)
        print("setting name of server thread")
        payloadFunc.setName('iperf3_server')
    elif unPickledConf['mode'] == 'client':
        unPickledConf.pop('mode')
        payloadFunc = threading.Thread(target=launchIperf3Client, kwargs=unPickledConf)
        print("setting name of client thread")
        payloadFunc.setName('iperf3_client')

    elif unPickledConf['mode'] == 'collect_results':
        if awaitingResults == True:
            print('still waiting results')
        else:
            print(8*"\|/")
            print(f"+++test results is: {testResults}")

    else:
        raise Exception('wrong input data!')

    print("we'll launching thread if required")
    if payloadFunc != None:
        payloadFunc.start()

def netLauncher(sock,payload):
    while True:
        conn,addr = sock.accept()
        print('connected:', addr)
        dataReceiverThread = threading.Thread(target=eval(payload),args=(conn,addr))
        dataReceiverThread.start()

def main():
    sock1 = socket.socket()
    sock2 = socket.socket()
    print("test from main()")
    try:
        sock1.bind((host2BindAdress, commandPort))
        sock1.listen(1)
        sock2.bind((host2BindAdress, dataReportPort))
        sock2.listen(1)
    except:
        print("cant bind to socket!")
        sys.exit(1)
    listenerThread = threading.Thread(target=netLauncher, args=(sock1,'dataReceiver'))
    listenerThread.setName('listenerLauncher')
    listenerThread.start()
    senderThread = threading.Thread(target=netLauncher, args=(sock2, 'dataSender'))
    senderThread.setName('senderLauncher')
    senderThread.start()
    while awaitingResults is True:
        time.sleep(5)
    print(awaitingResults)
    print("time to exit")

if __name__ == "__main__":
    main()
