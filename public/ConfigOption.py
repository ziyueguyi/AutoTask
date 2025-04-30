# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :ConfigOption.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/4/29 17:50
# @文件介绍 :
"""
import configparser
from pathlib import Path


class ConfigOption:
    def __init__(self, file_path):
        self.file_path = file_path
        self.config = configparser.ConfigParser()

    def write_config(self, section, key, val=None, file_path=None):
        """
        写配置
        :params section
        :params key
        :params val
        :return
        """
        file_path = file_path if file_path else self.file_path
        # 方法1: 使用dump函数将数据写入文件
        Path.mkdir(file_path, exist_ok=True)
        if Path.exists(Path.joinpath(file_path, 'config.ini')):
            self.config.read(Path.joinpath(file_path, 'config.ini'), encoding="UTF8")
        if section not in self.config.sections():
            self.config.add_section(section)
        self.config.set(section, key, val)
        # 写入配置到文件
        with open(Path.joinpath(file_path, 'config.ini'), 'w', encoding="UTF8") as configfile:
            self.config.write(configfile)

    def read_config_key(self, section=None, key=None, file_path=None, field_type=str):
        """
        读配置
        """
        file_path = file_path if file_path else self.file_path
        if Path.exists(Path.joinpath(file_path, 'config.ini')):
            self.config.read(Path.joinpath(file_path, 'config.ini'), encoding="UTF8")
            if not section:
                return self.config.sections()
            elif not key:
                return self.config.options(section)
            else:
                if field_type == int:
                    return self.config.getint(section, key)
                elif field_type == float:
                    return self.config.getfloat(section, key)
                elif field_type == bool:
                    return self.config.getboolean(section, key)
                else:
                    return self.config.get(section, key)
        else:
            return None
