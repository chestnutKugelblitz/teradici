#!/usr/bin/env python3
import configparser

configFile = "perf_tool.ini"
config = configparser.ConfigParser()
config.read(configFile)


def writeVar(var2WriteName, var2WriteValue, iniSection):
    """

    :param var2WriteName:
    :param var2WriteValue:
    :param iniSection:
    :return:
    """
    config[iniSection][var2WriteName] = var2WriteValue
    with open(configFile, 'w') as f:
        config.write(f)


def deleteVar(reqVar, iniSection):
    """

    :param reqVar:
    :param iniSection:
    :return:
    """
    config.remove_option(iniSection,reqVar)
    with open(configFile,'w') as f:
        config.write(f)

def returnVar(reqVar, iniSection):
    """

    :param reqVar:
    :param iniSection:
    :return:
    """
    return config.get(iniSection, reqVar)


if __name__ == "__main__":
    pass

if __name__ == '__init__':
    pass
