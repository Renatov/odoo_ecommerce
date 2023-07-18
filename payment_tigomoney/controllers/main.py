# -*- coding: utf-8 -*-
import json
import logging
import pprint
import urllib
from urllib.request import urlopen
import werkzeug
from odoo import http, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from zeep import Client
_logger = logging.getLogger(__name__)

class TigomoneyController(http.Controller):
    _notify_url = '/payment/tigomoney/url_error/'
    _return_url = '/payment/tigomoney/url_correcto/'
    _cancel_url = '/payment/tigomoney/cancel/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from tigomoney. """
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', False) or post.pop('cm', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    def _parse_pdt_response(self, response):
        lines = filter(None, response.split('\n'))
        status = lines.pop(0)
        pdt_post = dict(line.split('=', 1) for line in lines)
        for post in pdt_post:
            pdt_post[post] = urlopen(pdt_post[post]).decode('utf8')
        return status, pdt_post

    def tigomoney_validate_data(self, **post):
        res = False
        new_post = dict(post, cmd='_notify-validate')
        id_payment_transaccion = post.get('id_trans')
        tx = None
        if id_payment_transaccion:
            tx = request.env['payment.transaction'].sudo().search([('id', '=', id_payment_transaccion)])
            if tx.currency_id.code !=int('68'):
                strstring = "otroerror&Este metodo de pago solo acepta pago en moneda Bolivianos BOB"
                strstring = strstring.split('&')
                return strstring
            reference = post.update({'item_number':tx.reference})
            tgm_url_produccion = tx.acquirer_id.tgm_url_produccion
            try:
                client = Client(tgm_url_produccion)
                respuesta_tigo =  client.service.solicitarPago(tx.acquirer_id.tgm_hkey, tx.tgm_datos_encript)
            except Exception as e:
                error = 'otroerror&El servidor tigomoney no esta habilitado favor comuniquese con el administrador de la pagina, error-codigo FCLL'
                error = error.split('&')
                return error
        payment_acquirer_id = request.env['payment.acquirer'].sudo() #recuperamos la tabla payment aquuirer 
        id_acquirer = payment_acquirer_id.search([('id','=',tx.acquirer_id.id)]) #row de la tabla payment.acquirer
        varealbes_dencript=({'type':'dencr',
                             'key': id_acquirer.tgm_hkey_encript})
        respuesta_decrypt = payment_acquirer_id._encrypt_text_tigo(respuesta_tigo, varealbes_dencript)       
        respuesta_decrypt = respuesta_decrypt.split("&")
        v_dencrypt = ({})
        for item in respuesta_decrypt: # comma, or other
            nuevo_item = item.split("=")
            v_dencrypt.update({nuevo_item[0]:nuevo_item[1]})
        v_dencrypt.update(post) 
        v_dencrypt.update({'id_aquirer':id_acquirer})
        res = request.env['payment.transaction'].sudo().form_feedback(v_dencrypt, 'tigomoney')            
        return res, v_dencrypt
    @http.route('/payment/tigomoney/url_error/', type='http', auth='none', methods=['POST'], csrf=False)
    def tigomoney_url_error(self, **post):
        """ Pagosnet IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        try:
            self.tigomoney_validate_data(**post)
        except ValidationError:
            _logger.exception('Unable to validate the Paypal payment')
        return ''

    @http.route('/payment/tigomoney/url_correcto/<name>', type='http', auth="none", methods=['POST', 'GET'], csrf=False)
    def tigomoney_url_correcto(self, name, **post):
        """ Tigomoney DPN """
        _logger.info('Beginning Tigomoney DPN form_feedback with post data %s', pprint.pformat(post))  # debug
        post.update({'id_trans':name})
        return_url = self._get_return_url(**post)
        self.tigomoney_validate_data(**post)
        return werkzeug.utils.redirect(return_url)

    @http.route('/payment/tigomoney/cancel', type='http', auth="none", csrf=False)
    def tigomoney_cancel(self, **post):
        """ When the user cancels its Paypal payment: GET on this route """
        _logger.info('Beginning Paypal cancel with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
    @http.route('/payment/tigomoney/url_transfer/<idtrans>', auth="public", website=True, csrf=False)
    def tigomoney_url_transfer(self, idtrans, **post):
        """ Tigomoney Comprobacion de transferencia con datos encriptados """
        _logger.info('Empieza la transferencia de tigomoney %s', pprint.pformat(post))  # debug
        post.update({'id_trans':idtrans})
        return_url = '/'
        respuesta = self.tigomoney_validate_data(**post)
        respuesta_final = respuesta[0]
        if respuesta_final == False:
            respuesta = "Verifique porfavor si el numero de celular insertado en sus datos es correcto, como tambien si tiene saldo suficiente en Tigo money     " + respuesta[1].get('mensaje')
            return http.request.render('payment_tigomoney.index', {
            'error': respuesta})
        if respuesta_final == True:
            respuesta = "Compra realizada con exito:  " + respuesta[1].get('mensaje')
            self_transaction = request.env['payment.transaction'].sudo().search([('id','=', idtrans)])
            sale_order_request = request.env['sale.order'].sudo().search([('id','=', self_transaction.sale_order_id.id)])
            request.website.sale_reset()
            return request.render("website_sale.confirmation", {'order': sale_order_request})
        if respuesta_final == 'otroerror':
            respuesta = respuesta[1]
            return http.request.render('payment_tigomoney.index', {
            'error': respuesta})
