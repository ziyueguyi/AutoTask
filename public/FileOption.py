# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :FileOption.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/4/27 11:43
# @文件介绍 :
"""


class FileOption:
    def __init__(self, file_name):
        self.file_name = file_name

    def write_file(self, content):
        with open(self.file_name, "a", encoding="utf-8") as f:
            f.write(content)

    def read_file(self):
        with open(self.file_name, "r", encoding="utf-8") as f:
            content = f.read()
        return content