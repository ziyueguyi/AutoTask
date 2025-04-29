# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :FileOption.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/4/27 11:43
# @文件介绍 :
"""
import json
from pathlib import Path


class FileOption:
    def __init__(self, file_path):
        self.file_path = file_path

    def write_file(self, content, file_path=None):
        file_path =file_path if file_path else self.file_path
        # 方法1: 使用dump函数将数据写入文件
        if not Path.exists(Path.joinpath(file_path, 'config.json')):
            Path.mkdir(file_path, exist_ok=True)
            with open(Path.joinpath(file_path, 'config.json'), 'w') as f:
                f.write(json.dumps(content, indent=2, sort_keys=True))

    def read_file(self, file_path=None):
        file_path = file_path if file_path else self.file_path
        if Path.exists(Path.joinpath(file_path, 'config.json')):
            with open(Path.joinpath(file_path, 'config.json'), 'r') as file:
                data = json.load(file)
            return data
        else:
            return []
