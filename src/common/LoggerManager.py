"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from logging import Logger

from src.utils.logger.MPLogger import MPLogger
from src.utils.Singleton import Singleton


class LoggerManager(metaclass=Singleton):
    def __init__(self):
        self.logger = MPLogger(log_name='Asst-Qdrant-Manager', log_level='DEBUG', log_dir=None).get_logger()
        self.logger.info('Asst-Qdrant-Manager Logger initialized...')

    @staticmethod
    def get() -> Logger:
        return LoggerManager().logger
