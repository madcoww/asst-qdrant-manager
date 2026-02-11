"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import os
import shutil


class FileUtils:
    @staticmethod
    def read_dir(directory='./', ext='.done'):
        file_names = os.listdir(directory)

        res_file_names = []
        for file_name in file_names:
            if ext == os.path.splitext(file_name)[-1]:
                res_file_names.append(f"{directory}/{file_name}")

        return res_file_names

    @staticmethod
    def get_filenames(directory='./', ext='.done'):
        file_names = os.listdir(directory)
        res_file_names = []
        for file_name in file_names:
            if ext == os.path.splitext(file_name)[-1]:
                res_file_names.append(os.path.splitext(file_name)[0])

        return res_file_names

    @staticmethod
    def get_realpath(file=None):
        return os.path.dirname(os.path.realpath(file))

    @staticmethod
    def mkdir(dir_name):
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    @classmethod
    def remove_dir(cls, dir_name):
        if cls.is_exist(dir_name):
            shutil.rmtree(dir_name)

    @classmethod
    def move_dir(cls, src_dir, dst_dir):
        if cls.is_exist(src_dir):
            shutil.move(src=src_dir, dst=dst_dir)

    @classmethod
    def search(cls, dirname, exclude_list):
        result_list = []
        try:
            filenames = os.listdir(dirname)
            for filename in filenames:
                full_filename = os.path.join(dirname, filename)
                if os.path.isdir(full_filename):
                    result_list += cls.search(full_filename, exclude_list)
                else:
                    ext = os.path.splitext(full_filename)[-1]
                    if ext == '.py' and filename not in exclude_list:
                        result_list.append(full_filename)
        except PermissionError:
            pass

        return result_list

    @classmethod
    def search_package(cls, dirname, exclude_list):
        result_list = []
        try:
            filenames = os.listdir(dirname)
            for filename in filenames:
                full_filename = os.path.join(dirname, filename)
                if os.path.isdir(full_filename):
                    result_list += cls.search_package(
                        full_filename, exclude_list,
                    )
                else:
                    ext = os.path.splitext(full_filename)[-1]
                    if ext in {'.py', '.pyc'}:
                        if dirname not in result_list and filename not in exclude_list:
                            result_list.append(dirname)

        except PermissionError:
            pass

        return result_list

    @staticmethod
    def get_package_py_files(dir_name):
        exclude_nm = '__init__.py'
        result_list = []
        try:
            filenames = os.listdir(dir_name)
            for filename in filenames:
                full_filename = os.path.join(dir_name, filename)
                if os.path.isdir(full_filename):
                    continue
                _split_filename = os.path.splitext(filename)
                _filename = _split_filename[0]
                ext = _split_filename[-1]
                if ext == '.py' or ext == '.pyc' and not filename == exclude_nm:
                    result_list.append(_filename)
        except PermissionError:
            pass

        return result_list

    @staticmethod
    def is_exist(file):
        return os.path.exists(file)

    @staticmethod
    def file_pointer(filename, mode):
        return open(filename, mode, encoding='UTF-8', errors='ignore')

    # txt 파일을 읽기 위한 메서드 추가
    @staticmethod
    def read_file(file: str) -> str:
        with open(file, encoding='utf-8') as f:
            return f.read()
