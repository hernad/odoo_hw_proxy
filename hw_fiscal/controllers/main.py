# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import print_function
import logging
import math
import os
import os.path
import subprocess
import time
import traceback

try:
    from .. fiscal import *
    from .. fiscal.exceptions import *
    from .. fiscal.printers import FiscalTremol
except ImportError:
    fiscal = printerd = None

from queue import Queue
from threading import Thread, Lock



from odoo import http, _
from odoo.addons.hw_drivers_desk.controllers import proxy

_logger = logging.getLogger(__name__)

# workaround https://bugs.launchpad.net/openobject-server/+bug/947231
# related to http://bugs.python.org/issue7980
from datetime import datetime
datetime.strptime('2012-01-01', '%Y-%m-%d')

class FiscalDriver(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.queue = Queue()
        self.lock = Lock()
        #self.status = {'status':'connecting', 'messages':[]}
        self.status = {'status': 'connected', 'messages': []}


    def connected_fiscal_devices(self):
        connected = [{ 'vendor': 'tremol', 'product': 'Epson Tremol' }]

        return connected

    def lockedstart(self):
        with self.lock:
            if not self.is_alive():
                self.daemon = True
                self.start()

    def get_fiscal_printer(self):

        printers = self.connected_fiscal_devices()
        #if len(printers) > 0:
        #    try:
        #        print_dev = Usb(printers[0]['vendor'], printers[0]['product'])
        #    except HandleDeviceError:
        #        # Escpos printers are now integrated to PrinterDriver, if the IoTBox is printing
        #        # through Cups at the same time, we get an USBError(16, 'Resource busy'). This means
        #        # that the Odoo instance connected to this IoTBox is up to date and no longer uses
        #        # this escpos library.
        #        return None
        #    self.set_status(
        #        'connected',
        #        "Connected to %s (in=0x%02x,out=0x%02x)" % (printers[0]['name'], print_dev.in_ep, print_dev.out_ep)
        #    )
        #    return print_dev
        #else:
        #    self.set_status('disconnected','Printer Not Found')
        #    return None
        if len(printers) > 0:
            self.set_status(
                'connected',
                "Connected to fiscal printer %s" % printers[0]['vendor']
            )
        return FiscalTremol()


    def get_status(self):
        self.push_task('status')
        return self.status

    def open_cashbox(self, printer):
        printer.cashdraw(2)
        printer.cashdraw(5)

    def set_status(self, status, message = None):
        _logger.info(status+' : '+ (message or 'no message'))
        if status == self.status['status']:
            if message != None and (len(self.status['messages']) == 0 or message != self.status['messages'][-1]):
                self.status['messages'].append(message)
        else:
            self.status['status'] = status
            if message:
                self.status['messages'] = [message]
            else:
                self.status['messages'] = []

        if status == 'error' and message:
            _logger.error('Fiscal Error: %s', message)
        elif status == 'disconnected' and message:
            _logger.warning('Fiscal Device Disconnected: %s', message)

    def run(self):
        printer = None
        if not fiscal:
            _logger.error('Fiscal cannot initialize, please verify system dependencies.')
            return
        while True:
            try:
                error = True
                timestamp, task, data = self.queue.get(True)

                printer = self.get_fiscal_printer()
                _logger.debug('Fiscal RUN task=%s', task)

                if printer == None:
                    if task != 'status':
                        self.queue.put((timestamp, task, data))
                    error = False
                    time.sleep(5)
                    continue
                elif task == 'receipt':
                    #if timestamp >= time.time() - 1 * 60 * 60:
                    #    self.print_receipt_body(printer, data)
                    #    printer.cut()
                    printer.send(data)
                elif task == 'xml_receipt':
                    if timestamp >= time.time() - 1 * 60 * 60:
                        printer.receipt(data)
                #elif task == 'cashbox':
                #    if timestamp >= time.time() - 12:
                #        self.open_cashbox(printer)
                elif task == 'send_raw':
                    printer.send(data)
                elif task == 'status':
                    pass
                error = False

            except NoDeviceError as e:
                print("No device found %s" % e)
            except HandleDeviceError as e:
                printer = None
                print("Impossible to handle the device due to previous error %s" % e)
            except TicketNotPrinted as e:
                print("The ticket does not seems to have been fully printed %s" % e)
            except NoStatusError as e:
                print("Impossible to get the status of the printer %s" % e)
            except Exception as e:
                self.set_status('error')
                _logger.exception(e)
            finally:
                if error:
                    self.queue.put((timestamp, task, data))
                if printer:
                    printer.close()
                    printer = None

    def push_task(self, task, data=None):
        self.lockedstart()
        self.queue.put((time.time(), task, data))

    def print_receipt_body(self, eprint, receipt):

        def check(string):
            return string != True and bool(string) and string.strip()

        def price(amount):
            return ("{0:."+str(receipt['precision']['price'])+"f}").format(amount)

        def money(amount):
            return ("{0:."+str(receipt['precision']['money'])+"f}").format(amount)

        def quantity(amount):
            if math.floor(amount) != amount:
                return ("{0:."+str(receipt['precision']['quantity'])+"f}").format(amount)
            else:
                return str(amount)

        def printline(left, right='', width=40, ratio=0.5, indent=0):
            lwidth = int(width * ratio)
            rwidth = width - lwidth
            lwidth = lwidth - indent

            left = left[:lwidth]
            if len(left) != lwidth:
                left = left + ' ' * (lwidth - len(left))

            right = right[-rwidth:]
            if len(right) != rwidth:
                right = ' ' * (rwidth - len(right)) + right

            return ' ' * indent + left + right + '\n'

        def print_taxes():
            taxes = receipt['tax_details']
            for tax in taxes:
                eprint.text(printline(tax['tax']['name'],price(tax['amount']), width=40,ratio=0.6))

        # Receipt Header
        if receipt['company']['logo']:
            eprint.set(align='center')
            eprint.print_base64_image(receipt['company']['logo'])
            eprint.text('\n')
        else:
            eprint.set(align='center',type='b',height=2,width=2)
            eprint.text(receipt['company']['name'] + '\n')

        eprint.set(align='center',type='b')
        if check(receipt['company']['contact_address']):
            eprint.text(receipt['company']['contact_address'] + '\n')
        if check(receipt['company']['phone']):
            eprint.text('Tel:' + receipt['company']['phone'] + '\n')
        if check(receipt['company']['vat']):
            eprint.text('VAT:' + receipt['company']['vat'] + '\n')
        if check(receipt['company']['email']):
            eprint.text(receipt['company']['email'] + '\n')
        if check(receipt['company']['website']):
            eprint.text(receipt['company']['website'] + '\n')
        if check(receipt['header']):
            eprint.text(receipt['header']+'\n')
        if check(receipt['cashier']):
            eprint.text('-'*32+'\n')
            eprint.text('Served by '+receipt['cashier']+'\n')

        # Orderlines
        eprint.text('\n\n')
        eprint.set(align='center')
        for line in receipt['orderlines']:
            pricestr = price(line['price_display'])
            if line['discount'] == 0 and line['unit_name'] == 'Units' and line['quantity'] == 1:
                eprint.text(printline(line['product_name'],pricestr,ratio=0.6))
            else:
                eprint.text(printline(line['product_name'],ratio=0.6))
                if line['discount'] != 0:
                    eprint.text(printline('Discount: '+str(line['discount'])+'%', ratio=0.6, indent=2))
                if line['unit_name'] == 'Units':
                    eprint.text( printline( quantity(line['quantity']) + ' x ' + price(line['price']), pricestr, ratio=0.6, indent=2))
                else:
                    eprint.text( printline( quantity(line['quantity']) + line['unit_name'] + ' x ' + price(line['price']), pricestr, ratio=0.6, indent=2))

        # Subtotal if the taxes are not included
        taxincluded = True
        if money(receipt['subtotal']) != money(receipt['total_with_tax']):
            eprint.text(printline('', '-------'))
            eprint.text(printline(_('Subtotal'),money(receipt['subtotal']),width=40, ratio=0.6))
            print_taxes()
            #eprint.text(printline(_('Taxes'),money(receipt['total_tax']),width=40, ratio=0.6))
            taxincluded = False

        # Total
        eprint.text(printline('', '-------'))
        eprint.set(align='center',height=2)
        eprint.text(printline(_('         TOTAL'),money(receipt['total_with_tax']),width=40, ratio=0.6))
        eprint.text('\n\n')

        # Paymentlines
        eprint.set(align='center')
        for line in receipt['paymentlines']:
            eprint.text(printline(line['journal'], money(line['amount']), ratio=0.6))

        eprint.text('\n')
        eprint.set(align='center',height=2)
        eprint.text(printline(_('        CHANGE'),money(receipt['change']),width=40, ratio=0.6))
        eprint.set(align='center')
        eprint.text('\n')

        # Extra Payment info
        if receipt['total_discount'] != 0:
            eprint.text(printline(_('Discounts'),money(receipt['total_discount']),width=40, ratio=0.6))
        if taxincluded:
            print_taxes()
            #eprint.text(printline(_('Taxes'),money(receipt['total_tax']),width=40, ratio=0.6))

        # Footer
        if check(receipt['footer']):
            eprint.text('\n'+receipt['footer']+'\n\n')
        eprint.text(receipt['name']+'\n')
        eprint.text(      str(receipt['date']['date']).zfill(2)
                    +'/'+ str(receipt['date']['month']+1).zfill(2)
                    +'/'+ str(receipt['date']['year']).zfill(4)
                    +' '+ str(receipt['date']['hour']).zfill(2)
                    +':'+ str(receipt['date']['minute']).zfill(2) )


driver = FiscalDriver()

proxy.proxy_drivers['fiscal'] = driver


class FiscalProxy(proxy.ProxyController):

    #@http.route('/hw_proxy/open_cashbox', type='json', auth='none', cors='*')
    #def open_cashbox(self):
    #    _logger.info('Fiscal: OPEN CASHBOX')
    #    driver.push_task('cashbox')

    @http.route('/hw_proxy/print_receipt', type='json', auth='none', cors='*')
    def print_receipt(self, receipt):
        _logger.info('Fiscal: PRINT RECEIPT')
        driver.push_task('receipt', receipt)

    @http.route('/hw_proxy/print_xml_receipt', type='json', auth='none', cors='*')
    def print_xml_receipt(self, receipt):
        _logger.info('Fiscal: PRINT XML RECEIPT')
        driver.push_task('xml_receipt', receipt)

    @http.route('/hw_proxy/default_printer_action', type='json', auth='none', cors='*')
    def default_printer_action(self, data):
        if data['action'] == 'print_receipt':
             driver.push_task('receipt', data['receipt'])

