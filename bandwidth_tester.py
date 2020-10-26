#!/usr/bin/env python3
import ansible_runner
import datetime
import argparse
import sys
from perf_tester_modules import ini_parser
import random
from distutils.util import strtobool
import time

#from perf_tester_modules import commander
#ToDo: rewrite?
try:
    from perf_tester_modules import commander
except:
    pass

try:
    from perf_tester_modules import iperf_receiver
except:
    pass

#clientHost = ini_parser.returnVar('iperf3_client_host','connections')

awsCreds = {
    'aws_access_key' : ini_parser.returnVar('aws_access_key','aws'),
    'aws_secret_key': ini_parser.returnVar('aws_secret_key','aws'),
}

sshCreds = {
    #'path2folder_with_ssh_key': ini_parser.returnVar('path2folder_with_ssh_key','aws'),
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

host2BindAdress = {'iperf3_bind_address' : ini_parser.returnVar('iperf3_bind_address','iperf3') }

# def str2Bool(strVar):
#     """
#     simply converts text to bool
#     :param strVar: Yes/True/No/False/etc in text
#     :return: bool
#     """
#     return json.loads(strVar.lower())

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



def cleanup():
    """

    :return:
    """
    cleanupSettings = {}
    try:
        cleanupSettings = {
            'ec2_server_id': ini_parser.returnVar('ec2_server_id', 'aws'),
            'ec2_client_id': ini_parser.returnVar('ec2_client_id', 'aws'),
            'vpc_id': ini_parser.returnVar('vpc_id', 'aws'),
            'region': ini_parser.returnVar('region', 'aws'),
        }
    except:
        print("can't cleanup. Looks like created AWS objects not defined in the list")
        return False

    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_cleanup.yml',quiet=quietPlaybooks, extravars={**cleanupSettings,**awsCreds, **sshCreds})
    #print(f"r.rc={r.rc}")
    if r.rc == 0:
        ini_parser.deleteVar('ec2_server_id','aws')
        ini_parser.deleteVar('ec2_client_id','aws')
        ini_parser.deleteVar('vpc_id','aws')
        ini_parser.deleteVar('iperf3_server_host','connections')
        ini_parser.deleteVar('iperf3_client_host', 'connections')
        ini_parser.deleteVar('region','aws')
        ini_parser.deleteVar('iperf3_int_server','iperf3')
        ini_parser.deleteVar('iperf3_int_client','iperf3')
        ini_parser.deleteVar('vcpu_server', 'aws')
        ini_parser.deleteVar('vcpu_client', 'aws')
        ini_parser.deleteVar('instance_type_client','aws')
        ini_parser.deleteVar('instance_type_server','aws')
        ini_parser.writeVar('ready4test', 'False', 'connections')

        print("I've just done a clean up job")
        return True
    else:
        print("can't do clean up in the AWS side. Please do it manually")
        return False

def ssh_key_add(**kwargs):
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_ssh_key.yml',
            quiet=quietPlaybooks, extravars={**kwargs, **awsCreds, **sshCreds})

def sendCommands2Puppet():
    result = None
    status = False
    if ready4Test():
        sampleDict = {}
        commandsResult = []
        print("send commands to puppets")
        time.sleep(2)
        # commandsResult = commander.commandWrapper(sampleDict)
        # print(f"clientPrepareResult: {commandsResult[0]}, {commandsResult[1]}, {commandsResult[2]}, {commandsResult[3]}")
        # time.sleep(5)
        # print("send commands to puppets")
        commandsResult = commander.commandWrapper(sampleDict)
        if False in commandsResult:
            result = f"Something wrong in the process of sending commands. Details:\n " \
                     f"clientPrepareResult: {commandsResult[0]}, {commandsResult[1]}, {commandsResult[2]}, {commandsResult[3]}"
            status = False

        else:
            result =  "I've just send commands to server and client"
            status = True
    else:
        result = "system is not ready for test"
        status = False

    return status, result

def iperf():
    if 'iperf_receiver' not in sys.modules:
        from perf_tester_modules import iperf_receiver
    if 'commander' not in sys.modules:
        from perf_tester_modules import commander
    status, result = sendCommands2Puppet()
    print(result)
    if status:
        maxSpeed, maxSpeedHumanize = iperf_receiver.max_speed()
        print(f"max speed is: {maxSpeed} bytes/sec\n\nor, in the human form,{maxSpeedHumanize}/sec")
        return maxSpeed

def ready4Test():
    iniOptions = []
    iniOptions.append(ini_parser.returnVar('ready4test', 'connections'))
    iniOptions.append(ini_parser.returnVar('iperf3_server_host', 'connections'))
    iniOptions.append(ini_parser.returnVar('iperf3_client_host', 'connections'))
    iniOptions.append(ini_parser.returnVar('iperf3_int_server', 'iperf3'))
    iniOptions.append(ini_parser.returnVar('iperf3_int_client', 'iperf3'))
    if None in iniOptions:
        return None
    else:
        if strtobool(iniOptions[0]):
            return True
        else:
            return False

def launch(**kwargs):
    extraVars = locals()
    print(
        "I'm deploying two ec2 instances. It can take several minutes. If you want to observe a process, please use -v (verbose) key")
    ssh_key_add(**kwargs)
    if kwargs.get('launch_mode_with_vcpu') is None:
        kwargs['launch_mode_with_vcpu'] = True
    r = ansible_runner.run(private_data_dir='./', playbook='playbooks/playbook_aws_install.yml', quiet=quietPlaybooks, extravars={**kwargs, **awsCreds, **sshCreds, **gitSettings, **firewallSettings, **host2BindAdress})
    ini_parser.writeVar('ready4test', str(not r.rc), 'connections')
    if r.rc == 0:
        vpc_id = r.get_fact_cache('localhost')['vpc_id']
        ini_parser.writeVar('ec2_server_id',r.get_fact_cache('localhost')['server_ec2_id'],'aws')
        ini_parser.writeVar('ec2_client_id',r.get_fact_cache('localhost')['client_ec2_id'],'aws')
        ini_parser.writeVar('vpc_id',vpc_id,'aws')
        ini_parser.writeVar('iperf3_server_host', r.get_fact_cache('localhost')['ext_server'], 'connections')
        ini_parser.writeVar('iperf3_int_server',r.get_fact_cache('localhost')['int_server'], 'iperf3')
        ini_parser.writeVar('iperf3_client_host',r.get_fact_cache('localhost')['ext_client'], 'connections')
        ini_parser.writeVar('iperf3_int_client',r.get_fact_cache('localhost')['int_client'],'iperf3')
        ini_parser.writeVar('region', kwargs['region'], 'aws')
        ini_parser.writeVar('launch_mode_with_vcpu', str(kwargs['launch_mode_with_vcpu']),'aws')
        ini_parser.writeVar('instance_type_client',kwargs['instance_type_client'], 'aws')
        ini_parser.writeVar('instance_type_server',kwargs['instance_type_server'], 'aws')
        if kwargs['launch_mode_with_vcpu']:
            ini_parser.writeVar('vcpu_server',str(kwargs['vcpu_server']),'aws')
            ini_parser.writeVar('vcpu_client', str(kwargs['vcpu_client']), 'aws')

        result = f"I've just deployed two ec2 instances, both are ready to launch a performance tests"

    else:
        result = "I failed ansible playbook. Installation can be partly finished. Please perform manual cleanp using your AWS console. " \
                 "to understand why it happen please launch a tool with -v (verbose) key"
    return result


def fullTest(**kwargs):
    def localClean():
        print("looks like current configuration is not suitable. Clean it up")
        cleanup()

    def localInstall():
        print("so, we need new a installation")
        print("Determing the last Ubuntu 20.04 AMI image")
        kwargs['image'] = image(kwargs['region'])
        print(f"Selecting random VPC in the {kwargs['region']}")
        kwargs['vpc_subnet'] = random.sample(list_subnets(kwargs['region']), 1)[0]
        launch(**kwargs)

    def reinstallReqChecker():
        print("hmm... Looks like we already have installed instances! Checking it's settings...")
        needReinstall = False
        #print('debug1')
        if ini_parser.returnVar('instance_type_server', 'aws') == kwargs['instance_type_server'] \
                and ini_parser.returnVar('instance_type_client', 'aws') == kwargs['instance_type_client']:
            print("instances types are same!")
            #print('debug2')
        else:
            print("instance types are not same!")
            needReinstall = True
            #print('debug3')

        if ini_parser.returnVar('region','aws') == kwargs['region']:
            print("Regions is same!")
            #print('debug4')
        else:
            print("region is not same!")
            needReinstall = True
            #print('debug5')
        #print(f"debug. ini: {ini_parser.returnVar('launch_mode_with_vcpu','aws')}, kwargs: {kwargs['launch_mode_with_vcpu']}")
        if strtobool(ini_parser.returnVar('launch_mode_with_vcpu','aws')) == kwargs['launch_mode_with_vcpu']:
        #if strtobool(ini_parser.returnVar('launch_mode_with_vcpu', 'aws')) == kwargs['launch_mode_with_vcpu']:
            print(f"looks like we already installed instances in the required mode(vCpu or general instances)")
            #print('debug6')
            # print(f"debug vcpu amount: {ini_parser.returnVar('vcpu_server', 'aws')}")
            #print('debug6.6')
            # print(f"debug vcpu_amount: {kwargs['vcpu_server']}")
            if kwargs['launch_mode_with_vcpu'] == True:
                if int(ini_parser.returnVar('vcpu_server', 'aws')) == kwargs['vcpu_server'] and int(ini_parser.returnVar('vcpu_client','aws')) == kwargs['vcpu_client']:
                    print('we have same amount of vCpus in both - client and server!')
                    #print('debug7')
                else:
                    #print('vCPU amount mistmatch!')
                    needReinstall = True

        else:
            print("looks like we have a different mode here!")
            needReinstall = True
            #print('debug9')
        #print('debug10')
        return needReinstall


    print('determing if we need to reinstall')
    readyStatus = ready4Test()
    #print(1)
    if readyStatus:
        print("hmm... Looks like we already have installed instances! Checking it's settings...")
        #print("0.1")
        if reinstallReqChecker():
            #print("0.2")
            localClean()
            localInstall()
            #return iperf()
        else:
            #print("0.3")
            print("so, our previous configuration is good enough for us. Do nothing, just launch tests")
            return iperf()
            #return iperf()

    elif readyStatus == None:
        print("looks like configuration is inconsitent, but we can't launch a cleanup. We need a new installation")
        #print("0.4")
        localInstall()
        #return iperf()
    else:
        #print("0.5")
        print("our configuration is not ready. Perform cleaning.")
        localClean()
        localInstall()
    #print(8)
    #print("0.6")
    # if ready4Test():
    return iperf()
    # else:
    #     print("can't launch test! System is not ready. Please clean up everything manually and launch with debug option -v again")


def instancetest(**kwargs):
    kwargs['launch_mode_with_vcpu'] = False
    return fullTest(**kwargs)


def cputest(**kwargs):
    kwargs['launch_mode_with_vcpu'] = True
    return fullTest(**kwargs)


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

    launchParser.add_argument('-t', '--instance_type_client', type=str,
                        help='Launch ec2 instance using selected type', required=True)

    launchParser.add_argument('-c', '--vcpu_client', type=int,
                        help='Launch ec2 instance with selected amount of vCPU', required=True)

    launchParser.add_argument('-T', '--instance_type_server', type=str,
                        help='Launch ec2 instance using selected type', required=True)

    launchParser.add_argument('-C', '--vcpu_server', type=int,
                        help='Launch ec2 instance with selected amount of vCPU', required=True)

    getParser = subParsers.add_parser('get', parents = [rootParser], help='get current status, clean up, run tests, etc')
    getParser.add_argument('-c', '--cleanup', action='store_true',
                        help='Clean up ec2 instances')
    getParser.add_argument('-r','--ready4test', action="store_true",
                        help='Report if tool is ready for test. Required launched and prepared two of ec2 instances')
    getParser.add_argument('-t', '--iperf', action='store_true',
                        help="Launch test itself")

    cputest = subParsers.add_parser('cputest', parents = [rootParser], help='run tests and do everything underhood - user can configure vcpu and instance type')
    cputest.add_argument('-r', '--region', type=str,
                        help='Launch ec2 instance in the selected region', required=True)

    cputest.add_argument('-t', '--instance_type_client', type=str,
                        help='Launch ec2 instance using selected type', required=True)

    cputest.add_argument('-c', '--vcpu_client', type=int,
                        help='Launch ec2 instance with selected amount of vCPU', required=True)

    cputest.add_argument('-T', '--instance_type_server', type=str,
                        help='Launch ec2 instance using selected type', required=True)

    cputest.add_argument('-C', '--vcpu_server', type=int,
                        help='Launch ec2 instance with selected amount of vCPU', required=True)

    instancetest = subParsers.add_parser('instancetest', parents=[rootParser], help='run tests and do everything underhood - user can configure instance type')
    instancetest.add_argument('-r', '--region', type=str,
                         help='Launch ec2 instance in the selected region', required=True)

    instancetest.add_argument('-t', '--instance_type_client', type=str,
                         help='Launch ec2 instance using selected type', required=True)

    instancetest.add_argument('-T', '--instance_type_server', type=str,
                         help='Launch ec2 instance using selected type', required=True)

    args = mainParser.parse_args()

    return args.__dict__


def main():
    if not len(sys.argv) > 1:
        print(f"See help: {sys.argv[0]} -h")
        sys.exit(1)

    argsDict = getArgs()
    global quietPlaybooks
    if argsDict['verbose'] == True:
        quietPlaybooks = False
    else:
        quietPlaybooks = True
    del argsDict['verbose']

    if quietPlaybooks is False:
        print(f"launch arguments of program is: {argsDict}")

    commandMode = argsDict['command']
    del argsDict['command']

    if commandMode in ('launch','cputest', 'instancetest'):
        output = eval(commandMode)(**argsDict)
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


if __name__ == '__init__':
    global quietPlaybooks
    quietPlaybooks = True
