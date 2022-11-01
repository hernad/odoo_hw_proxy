# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

proxy_drivers = {}

class ProxyController(http.Controller):
    #@http.route('/hw_proxy/hello', type='http', auth='public', website=True, csrf=False)
    @http.route('/hw_proxy/hello', type='http', auth='none', cors='*')
    def hello(self):
        return "ping"

    #@http.route('/hw_proxy/handshake', type='json', auth='public', csrf=False)
    @http.route('/hw_proxy/handshake', type='json', auth='none', cors='*')
    def handshake(self):
        return True

    #@http.route('/hw_proxy/status_json', type='json', auth='none', cors='*')
    @http.route('/hw_proxy/status_json', type='json', auth='public')
    def status_json(self):
        statuses = {}
        for driver in proxy_drivers:
            statuses[driver] = proxy_drivers[driver].get_status()
        return statuses

    # ovo ide u hw_fiscal controller
    #@http.route('/hw_proxy/default_printer_action', type='json', auth='none', cors='*')
    #def default_printer_action(self, data):
    #    for driver in proxy_drivers:
    #        # action = print_receipt
    #        if data['action'] == 'print_receipt':
    #           proxy_drivers[driver].push_task('receipt', data['receipt'])


