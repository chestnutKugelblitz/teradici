#!/usr/bin/env python3
import configparser

# configFile = "perf_tool.ini"
# config = configparser.ConfigParser()
# config.read(configFile)

def reReadConfig():
    configFile = "perf_tool.ini"
    config = configparser.ConfigParser()
    config.read(configFile)
    return configFile, config


def writeVar(var2WriteName, var2WriteValue, iniSection):
    """

    :param var2WriteName:
    :param var2WriteValue:
    :param iniSection:
    :return:
    """
    configFile, config = reReadConfig()
    config[iniSection][var2WriteName] = var2WriteValue
    with open(configFile, 'w') as f:
        config.write(f)


def deleteVar(reqVar, iniSection):
    """

    :param reqVar:
    :param iniSection:
    :return:
    """
    configFile, config = reReadConfig()
    config.remove_option(iniSection,reqVar)
    with open(configFile,'w') as f:
        config.write(f)

def returnVar(reqVar, iniSection):
    """

    :param reqVar:
    :param iniSection:
    :return:
    """
    _, config = reReadConfig()
    try:
        return config.get(iniSection, reqVar)
    except configparser.NoOptionError:
        return None


if __name__ == "__main__":
    pass

if __name__ == '__init__':
    pass
