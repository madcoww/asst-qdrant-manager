"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import os

from src.utils.ConfigUtils import ConfigUtils
from src.utils.FileUtils import FileUtils
from src.utils.Singleton import Singleton


class ConfigManager(metaclass=Singleton):
    """
    class : ConfigManager
    """

    def __init__(self):
        conf_filename = f"{os.getcwd()}/conf/qdrant-manager-conf.xml"
        # Dev
        if not FileUtils.is_exist(conf_filename):
            conf_filename = f"{FileUtils.get_realpath(__file__)}/../../conf/qdrant-manager-conf.xml"
        self.conf = ConfigUtils.load_conf_xml(conf_filename)

    def get(self, key, default=None) -> object:
        return self.conf.get(key, default)
