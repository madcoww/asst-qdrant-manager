"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import logging
import multiprocessing
import threading
import time
from logging import FileHandler
from logging import StreamHandler


class MPLogHandler(logging.Handler):
    """multiprocessing log handler

    This handler makes it possible for several processes
    to log to the same file by using a queue.

    """

    def __init__(self, filename=None):
        self.terminate = False
        self._f_handler = None
        logging.Handler.__init__(self)
        if filename is not None:
            self._f_handler = FileHandler(filename)
            self._f_handler.suffix = '%Y-%m-%d'

        self._s_handler = StreamHandler()

        self.queue = multiprocessing.Queue(-1)

        self.thread = threading.Thread(target=self.receive)
        self.thread.daemon = True
        self.thread.start()

    def setFormatter(self, fmt):
        logging.Handler.setFormatter(self, fmt)
        if self._f_handler is not None:
            self._f_handler.setFormatter(fmt)
        self._s_handler.setFormatter(fmt)

    def receive(self):
        while self.terminate is False:
            try:
                if self.queue is None:
                    break
                record = self.queue.get()
                if self._f_handler is not None:
                    self._f_handler.emit(record)
                self._s_handler.emit(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except EOFError:
                break
            except OSError:
                break
            except TypeError:
                break
            except ValueError:
                break
            # except Exception:
            #     traceback.print_exc(file=sys.stderr)

    def send(self, s):
        self.queue.put_nowait(s)

    def _format_record(self, record):
        if record.args:
            record.msg = record.msg % record.args
            record.args = None
        if record.exc_info:
            _ = self.format(record)
            record.exc_info = None

        return record

    def emit(self, record):
        try:
            s = self._format_record(record)
            self.send(s)
        except (KeyboardInterrupt, SystemExit):
            raise
        # except Exception:
        #     self.handleError(record)

    def setLevel(self, level):
        logging.Handler.setLevel(self, level)
        if self._f_handler is not None:
            self._f_handler.setLevel(level)
        self._s_handler.setLevel(level)

    def close(self):
        self.terminate = True
        if self._f_handler is not None:
            self._f_handler.close()
        self._s_handler.close()
        logging.Handler.close(self)
        self.thread.join()
        time.sleep(1)
        self.queue.close()
