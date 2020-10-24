#!/usr/bin/env python3
import ansible_runner
import datetime
import argparse
import sys
import json
from perf_tester_modules import ini_parser, commander, iperf_receiver

clientHost = ini_parser.returnVar('iperf3_client_host','connections')

awsCreds = {
    'aws_access_key' : ini_parser.returnVar('aws_access_key','aws'),
    'aws_secret_key': ini_parser.returnVar('aws_secret_key','aws'),
}

sshCreds = {
    'path2folder_with_ssh_key': ini_parser.returnVar('path2folder_with_ssh_key','aws'),
    'ssh_key_name': ini_parser.returnVar('ssh_key_name','aws'),
}

gitSettings = {
    'git_repo':  ini_parser.returnVar('git_repo','git'),
    'git_puppet_dest': ini_parser.returnVar('git_puppet_dest','git'),
    'puppet_requirements': ini_parser.returnVar('puppet_requirements','git'),
    'puppet_name':ini_parser.returnVar('puppet_name','git')
}

firewallSettings = {
'iperf3_server_port': int(ini_parser.returnVar('iperf3_server_port','iperf3')),
'data_port': int(ini_parser.returnVar('data_port','connections')),
'command_port': int(ini_parser.returnVar('command_port','connections')),
}

def list_regions():
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_collect_regions.yml',
            quiet=quietPlaybooks )
    return r.get_fact_cache('localhost')['availabile_regions']

def list_subnets(region):
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_collect_subnets.yml',
            quiet=quietPlaybooks, extravars={'region':region, **awsCreds})
    return r.get_fact_cache('localhost')['subnets_list']

def list_ami(region):
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_collect_ami.yml',
            quiet=quietPlaybooks, extravars={'region': region, **awsCreds})
    return r.get_fact_cache('localhost')['ami_dict']

def image(region):
    dictAmi = list_ami(region)
    for i in range(len(dictAmi)):
        creationDate, creationTime = dictAmi[i]['creation_date'].split('T')
        creationDate = datetime.datetime.strptime(creationDate, '%Y-%m-%d').date()
        creationTime = datetime.datetime.strptime(creationTime.split(".")[0], '%H:%M:%S').time()
        date_obj_final = datetime.datetime.combine(creationDate, creationTime)
        dictAmi[i]["creationTimeFormatted"] = date_obj_final

    dictAmi.sort(reverse=True, key=lambda x: x["creationTimeFormatted"])
    return dictAmi[1]['image_id']


#ToDo: write it
def cleanup(*args):
    #Todo: Fix it, terrbile
    if args[0]:
        extraVars = locals()
        print(f"extraVars= {extraVars}")
        r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_clean_up.yml',
                quiet=quietPlaybooks, extravars={**extraVars,**awsCreds})
        return r.get_fact_cache('localhost')['ami_dict']
    else:
        pass


def ssh_key_add(**kwargs):
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_ssh_key.yml',
            quiet=quietPlaybooks, extravars={**kwargs, **awsCreds, **sshCreds})

def sendCommands2Puppet():
    result = None
    status = False
    if ready4test():
        sampleDict = {}
        commandsResult = []
        print("send commands to puppets")
        commandsResult = commander.commandWrapper(sampleDict)
        if False in commandsResult:
            result = f"Something wrong in the process of sending commands. Details:\n " \
                     f"clientPrepareResult: {commandsResult[0]}, serverPrepareResult {1}, clientResult {2}, serverResult {3}"
            status = False

        else:
            result =  "I've just send commands to server and client"
            status = True
    else:
        result = "system is not ready for test"
        status = False

    return status, result

def iperf():
    status, result = sendCommands2Puppet()
    print(result)
    if status:
        maxSpeed, maxSpeedHumanize = iperf_receiver.max_speed()
        print(f"max speed is: {maxSpeed} bytes/sec\n\nor, in the human form,{maxSpeedHumanize}/sec")

def ready4test():
    iniOptions = []
    iniOptions.append(ini_parser.returnVar('iperf3_server_host', 'connections'))
    iniOptions.append(ini_parser.returnVar('iperf3_client_host', 'connections'))
    iniOptions.append(ini_parser.returnVar('ready4test', 'connections'))
    if None in iniOptions:
        return None
    else:
        if json.loads(iniOptions[2].lower()):
            return True
        else:
            return False

def ec2_instance_launch(**kwargs):
    extraVars = locals()

    ssh_key_add(**kwargs)

    print("I'm deploying two ec2 instances. It can take several minutes. If you want to observe a process, please use -v (verbose) key")
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_aws_install.yml', quiet=quietPlaybooks, extravars={**kwargs, **awsCreds, **sshCreds, **gitSettings, **firewallSettings})
    ini_parser.writeVar('ready4test', str(not r.rc), 'connections')
    if r.rc == 0:
        ec2hosts = r.get_fact_cache('localhost')['ec2hosts']
        vpc_id = r.get_fact_cache('localhost')['vpc_id']
        ec2ids = r.get_fact_cache('localhost')['ec2ids']
        ini_parser.writeVar('ec2_server_id',ec2ids[0],'aws')
        ini_parser.writeVar('ec2_client_id',ec2ids[1],'aws')
        ini_parser.writeVar('vpc_id',vpc_id,'aws')
        ini_parser.writeVar('iperf3_server_host', ec2hosts[0], 'connections')
        ini_parser.writeVar('iperf3_client_host',ec2hosts[1], 'connections')

        result = f"I've deployed two ec2 instances, and assigned first with ec2-id {ec2ids[0]} to the iperf3 server with hostname {ec2hosts[0]}," \
                 f"and the second with ec2-id {ec2ids[1]} to the iperf3 client with hostname {ec2hosts[0]} \n" \
                 f"both are ready to launch a performance tests"

    else:
        result = "I failed ansible playbook. Installation can be partly finished. Please perform manual cleanp using your AWS console. " \
                 "to understand why it happen please launch a tool with -v (verbose) key"
    return result


def getArgs():
    rootParser = argparse.ArgumentParser(add_help=False)
    rootParser.add_argument('-v', '--verbose', action='store_true')
    mainParser = argparse.ArgumentParser('Tool to test bandwidth between AWS ec2 instances')

    subParsers = mainParser.add_subparsers(title='subcommands', dest='command', description='list of commands', help='description')
    infoParser = subParsers.add_parser('info', parents = [rootParser], help='get info from AWS EC2')
    infoParser.add_argument('-r', '--list_regions', action='store_true',
                        help='list regions. Usage: bandwidth_tester info -r')
    infoParser.add_argument('-s', '--list_subnets', type=str,
                        help='list avaible subnets for the region. Usage: bandwidth_tester info -s <AWS region>|bandwidth_tester --list_subnets <AWS region>')
    infoParser.add_argument('-a', '--list_ami', type=str,
                        help='list avaible Ubuntu 20.04 ami images for region. Usage: bandwidth_tester info -a <AWS region>|bandwidth_tester --list_ami <AWS region>')
    infoParser.add_argument('-i', '--image', type=str,
                        help='Get the most recent Ubuntu 20.04 image ID for region. Usage: bandwidth_tester info -i <AWS region>|bandwidth_tester --image <AWS region>')

    launchParser = subParsers.add_parser('launch', parents = [rootParser], help='Launch ec2 instance in the selected region and with the selected subnet. Usage: bandwidth_tester launch -s <VPC subnet> -r <region>')
    launchParser.add_argument('-s', '--vpc_subnet', type=str,
                        help='Launch ec2 instance in selected subnet.', required=True)
    launchParser.add_argument('-r', '--region', type=str,
                        help='Launch ec2 instance in the selected region', required=True)
    launchParser.add_argument('-i', '--image', type=str,
                        help='Launch ec2 instance using selected image', required=True)

    getParser = subParsers.add_parser('get', parents = [rootParser], help='get current status, clean up, run tests, etc')
    getParser.add_argument('-c', '--cleanup', action='store_true',
                        help='Clean up ec2 instances')
    getParser.add_argument('-r','--ready4test', action="store_true",
                        help='Report if tool is ready for test. Required launched and prepared two of ec2 instances')
    getParser.add_argument('-t', '--iperf', action='store_true',
                        help="Launch test itself")

    args = mainParser.parse_args()

    return args.__dict__


def main():
    argsDict = getArgs()
    print(f"{argsDict}")

    global quietPlaybooks
    if argsDict['verbose'] == True:
        quietPlaybooks = False
    else:
        quietPlaybooks = True
    del argsDict['verbose']

    commandMode = argsDict['command']
    del argsDict['command']

    if commandMode == 'launch':
        output = ec2_instance_launch(**argsDict)
        print(f"result={output}")

    if commandMode == 'info':
        for key, value in argsDict.items():
            if key == 'list_regions' and value:
                print(f"launch {key}")
                output = list_regions()
                print(f"result={output}")
            if key != 'list_regions' and value is not None:
                print(f"launch function {key}({value})")
                output = globals()[key](value)
                print(f"result={output}")

    if commandMode == 'get':
        for key, value in argsDict.items():
            if value:
                print(f"launch function {key}()")
                output = globals()[key]()
                print(f"result={output}")


if __name__ == "__main__":
    main()
