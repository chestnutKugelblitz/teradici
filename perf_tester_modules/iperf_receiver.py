#!/usr/bin/env python3
import socket
import pickle
import humanize
from perf_tester_modules import ini_parser

sender_bind_port = int(ini_parser.returnVar('data_port','connections'))
sender_bind_address = ini_parser.returnVar('iperf3_client_host', 'connections')
bitSecList = []

def traverseDataStructure(data):
    if isinstance(data, dict):
        if 'bits_per_second' in data:
            bitSecList.append(data['bits_per_second'])
        for key in data:
            traverseDataStructure(data[key])
    elif isinstance(data, list):
        for val in data:
            traverseDataStructure(val)

def max_speed():
    pickledResults = b''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((sender_bind_address, sender_bind_port))
        while True:
            netChunk = s.recv(1024)
            if not netChunk:
                break
            pickledResults += netChunk

    unPickledResults = pickle.loads(pickledResults)
    traverseDataStructure(unPickledResults)
    maxSpeed = bitSecList[0]
    maxSpeedHumanize = humanize.naturalsize(maxSpeed)
    return maxSpeed, maxSpeedHumanize

if __name__ == "__main__":
    maxSpeed, maxSpeedHumanize = max_speed()
    print(f"max speed is:\n{maxSpeed} bytes/sec\n\nor, in the human form,\n{maxSpeedHumanize}/sec")

if __name__ == '__init__':
    pass
