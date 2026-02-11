"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import logging.config

from src.utils.logger.MPLogHandler import MPLogHandler


class MPLogger:
    # Static variables
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARN = 'WARN'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'

    def __init__(self, log_dir=None, log_name='AIP-mlps', log_level='INFO'):
        # custom logger variables
        self.log_dir = log_dir
        self.log_name = log_name
        self.log_level = MPLogger._get_level(log_level)

        root = logging.getLogger()
        root.setLevel(self.log_level)

        logger = logging.getLogger(self.log_name)

        log_path = None
        if log_dir is not None:
            log_path = f"{self.log_dir}/{self.log_name}.log"

        self.mp_log_handler = MPLogHandler(log_path)
        self.mp_log_handler.setLevel(self.log_level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)-5s - %(processName)-15s - %(filename)-22s:%(lineno)-3s - %(message)s',
        )
        self.mp_log_handler.setFormatter(formatter)

        # Add handlers
        logger.addHandler(self.mp_log_handler)
        logger.propagate = False

        self.logger = logger

    def get_logger(self):
        return self.logger

    @staticmethod
    def _get_level(level):
        if level == 'DEBUG':
            return logging.DEBUG
        if level == 'INFO':
            return logging.INFO
        if level == 'WARN':
            return logging.WARN
        if level == 'ERROR':
            return logging.ERROR
        if level == 'CRITICAL':
            return logging.CRITICAL
        return logging.INFO
