#!/usr/bin/env python3
import pickle
import socket
from perf_tester_modules import ini_parser
import time
import logging

logging.basicConfig(level = logging.DEBUG)

clientHost = ini_parser.returnVar('iperf3_client_host','connections')
serverHost = ini_parser.returnVar('iperf3_server_host','connections')
#iperf3_int_client = ini_parser.returnVar('iperf3_client_host','iperf3')
iperf3_int_server = ini_parser.returnVar('iperf3_int_server','iperf3')
commandPort = int(ini_parser.returnVar('command_port', 'connections'))
durationSecs = int(ini_parser.returnVar('duration','iperf3'))
numStreams = int(ini_parser.returnVar('num_streams','iperf3'))
waitUntilCheck = int(ini_parser.returnVar('wait_until_check','connections'))
iperf3ServerPort = int(ini_parser.returnVar('iperf3_server_port','iperf3'))
iperf3BindAddress = ini_parser.returnVar('iperf3_bind_address','iperf3')

iperf3ServerHost = ini_parser.returnVar('iperf3_server_host','connections')


def commandSender(commandsDict,host4Command,commandPort):
    """
    Function to send dict of commands to server.
    :param commandsDict:
    :param serverHost:
    :param commandPort:
    :return: Returns True if commands had been send. And Else if can't connect (by timeout)
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host4Command, commandPort))
            s.sendall(pickle.dumps(commandsDict))
        return True
    except socket.timeout:
        return False

def commandWrapper(commandsDict):
    """
    :param commandsDict:
    :return: booleans: server prepare, client prepare, server ready to collect results, client ready to collect results
    """

    if clientHost == None or serverHost == None:
        return None, None, False, False
    commandsDict['mode'] = 'server'
    commandsDict['iperf3ServerPort'] = iperf3ServerPort
    commandsDict['iperf3BindAddress'] = iperf3BindAddress
    serverPrepareResult = commandSender(commandsDict=commandsDict,host4Command=serverHost,commandPort=commandPort)
    commandsDict['mode'] = 'client'
    commandsDict['iperf3IntServer'] = iperf3_int_server
    commandsDict['durationSecs'] = durationSecs
    commandsDict['numStreams'] = numStreams
    commandsDict['iperf3ServerHost'] = iperf3ServerHost
    clientPrepareResult = commandSender(commandsDict=commandsDict,host4Command=clientHost,commandPort=commandPort)
    if clientPrepareResult is not True or serverPrepareResult is not True:
        return clientPrepareResult, serverPrepareResult, False, False

    logging.info(msg=f"commands to client and server has been done. Waiting...")
    time.sleep(waitUntilCheck)
    commandsDict = {'mode': 'collect_results'}
    serverRunResult = commandSender(commandsDict=commandsDict, host4Command=serverHost, commandPort=commandPort)
    clientRunResult = commandSender(commandsDict=commandsDict,host4Command=clientHost,commandPort=commandPort)
    return True, True, clientRunResult, serverRunResult


def main():
    sampleDict = { }
    clientPrepareResult, serverPrepareResult, clientResult, serverResult = commandWrapper(sampleDict)
    print(f"client prepare result: {clientPrepareResult}\nserverPrepareResult: {serverPrepareResult}\nclient result: {clientResult}\nserver result: {serverResult}")


if __name__ == "__main__":
    main()

if  __name__ == "__init__":
    pass

