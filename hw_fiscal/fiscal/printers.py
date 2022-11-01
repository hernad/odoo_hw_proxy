#!/usr/bin/python

from __future__ import print_function

from .fiscal import *
from .constants import *
from .exceptions import *
from time import sleep


import logging
_logger = logging.getLogger(__name__)


class FiscalTremol(Fiscal):
    """ Define Network printer """

    def __init__(self,host='localhost',port=9100):
        """
        @param host : Printer's hostname or IP address
        @param port : Port to write to
        """
        self.host = host
        self.port = port
        self.open()


    def open(self):
        """ Open TCP socket and set it as escpos device """
        #self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.device.connect((self.host, self.port))

        #if self.device is None:
        #    print("Could not open socket for %s" % self.host)
        _logger.debug("DUMMY FiscalTremol open")


    def _raw(self, msg):
        #self.device.send(msg)
        _logger.debug("DUMMY FiscalTremol _raw send msg %s", msg)

    def send(self, msg):
        #self.device.send(msg)
        _logger.debug("DUMMY FiscalTremol SEND msg %s", msg)

    def close(self):
        _logger.debug("DUMMY FiscalTremol close")

    def __del__(self):
        """ Close TCP connection """
        #self.device.close()
        _logger.debug("DUMMY close fiscal")
