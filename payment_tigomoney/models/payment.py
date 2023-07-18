# coding: utf-8
import json
import logging
from urllib.parse import urljoin
import sys
from base64 import b64encode, b64decode
from Crypto.Cipher import DES3
import dateutil.parser
import pytz
from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_tigomoney.controllers.main import TigomoneyController
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


class AcquirerTigomoney(models.Model):
    _inherit = 'payment.acquirer'
    provider = fields.Selection(selection_add=[('tigomoney', 'Tigomoney')], ondelete={'tigomoney': 'set default'})
    tgm_hkey = fields.Char(string='Llave de usuario tigomoney', groups='base.group_user', required_if_provider='tigomoney')
    tgm_url_produccion = fields.Char(string='URL proporcionada por le proveedor', groups='base.group_user', required_if_provider='tigomoney')
    tgm_hkey_encript = fields.Char(string='Llave de encriptacion tigomoney', size=24, groups='base.group_user', required_if_provider='tigomoney')
    

    def _get_feature_support(self):
        """Get advanced feature support by provider.
        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(AcquirerTigomoney, self)._get_feature_support()
        res['fees'].append('tigomoney')
        return res

    @api.model
    def _get_tigomoney_urls(self, environment):
        """ Tigomoney URLS """      
        if environment == 'prod':
            paytrnas_id = self.variables_encript['paytrnas_id']
            idtr = str(paytrnas_id.id)
            return {
                'tigomoney_form_url': '/payment/tigomoney/url_transfer/'+idtr+'/',
            }
        else:
            paytrnas_id = self.variables_encript['paytrnas_id']
            idtr = str(paytrnas_id.id)
            return {
                'tigomoney_form_url':'/payment/tigomoney/url_transfer/'+idtr+'/',
            }

     
    def tigomoney_compute_fees(self, amount, currency_id, country_id):
        """ Compute paypal fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    #FUNCION INICIAL para #tigomoney #payment.acuierier
    def tigomoney_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        valuest = values['reference']
        if valuest != str('/'):
            if valuest.split('-'):
                s_order = valuest.split('-')
                s_order = s_order[0]
            sal_order_trans = self.env['payment.transaction'].search([('reference','=',valuest)])
            sal_order_id = self.env['sale.order'].search([('id','=',sal_order_trans.sale_order_ids.id)])
        else:
            sal_order_id = self.env['sale.order'].search([('name','=',valuest)])
        tigomoney_tx_values = dict(values)
        tigomoney_tx_values.update({
            'cmd': '_xclick',
            'business': self.env.user.email,
            'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency_id'] and values['currency'].name or '',
            'address1': values.get('billing_partner_address'),
            'city': values.get('billing_partner_city'),
            'country': values.get('billing_partner_country') and values.get('partner_country').code or '',
            'state': values.get('billing_partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
            'email': values.get('billing_partner_email'),
            'zip_code': values.get('billing_partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'tigomoney_return': '%s' % urljoin(base_url,TigomoneyController._return_url),
            'notify_url': '%s' % urljoin(base_url, TigomoneyController._notify_url),
            'cancel_return': '%s' % urljoin(base_url, TigomoneyController._cancel_url),
            'handling': '%.2f' % tigomoney_tx_values.pop('fees', 0.0) if self.fees_active else False,
            'custom': json.dumps({'return_url': '%s' % tigomoney_tx_values.pop('return_url')}) if tigomoney_tx_values.get('return_url') else False,
            'tigomoney_form_url' : self.tgm_url_produccion,
        })
        products = self.env['sale.order'].search([('name','=',sal_order_id.name)])
        product_ids=self.env['sale.order.line'].search([('order_id','=',sal_order_id.id)])
        i=0
        pv_items = str("")
        for product_id in product_ids: #pv_items==*i1|1|Producto 1|15.50|15.50*i2|3|Producto2|25.00|30.00
            i=i+1
            cantidad = product_id.product_uom_qty
            nombre = product_id.name
            precio_subtotal = product_id.price_subtotal
            precio_total = product_id.price_total
            pv_items = pv_items+"*i"+str(int(i))+"|"+str(int(cantidad))+"|"+str(nombre)+"|"+str(float(precio_subtotal))+"|"+str(float(precio_total))
        text = "pv_nroDocumento="+str(tigomoney_tx_values['item_name'])+";pv_linea="+ str(tigomoney_tx_values['billing_partner_phone'])+";pv_monto="+ str(tigomoney_tx_values['amount'])+";pv_orderId="+ str(tigomoney_tx_values['item_number'])+";pv_nombre="+ str(tigomoney_tx_values['billing_partner_name'])+";pv_confirmacion="+ str(self.company_id.name)+";pv_notificacion=Codigo:"+ str(tigomoney_tx_values['item_number'])+";pv_urlCorrecto="+ str(tigomoney_tx_values['tigomoney_return'])+";pv_urlError="+ str(tigomoney_tx_values['notify_url'])+";pv_items=="+str(pv_items)+";pv_razonSocial="+ str(self.company_id.name)+";pv_nit="+ str(self.company_id.vat)
        variables_encript = {'key': self.tgm_hkey_encript,
                             'type': 'encr'}
        text_encrypt = self._encrypt_text_tigo(text, variables_encript)
        write_encrypt =  sal_order_trans.id
        variables_encript = {'key': self.tgm_hkey_encript,
                     'type': 'encr', 
                     'text_encrypt': text_encrypt,
                     'paytrnas_id':write_encrypt}
        self.variables_encript = variables_encript
        write_encrypt.write({'tgm_datos_encript':text_encrypt})
        return tigomoney_tx_values
    
    def tigomoney_respuesta_decrypt(self, data, aqid):
        data =  b64decode(data)
        retorno_datos = self.des3_decrypt(aqid, data)
        return retorno_datos
    
    def _encrypt_text_tigo(self, text, varealbes_encript):
        try:
            if varealbes_encript['type'] == 'encr':
                encrypted_text = b64encode(self.des3_encrypt(varealbes_encript['key'], text))
            if varealbes_encript['type']=='dencr':
                rsult = b64decode(text)
                encrypted_text = self.des3_decrypt(varealbes_encript['key'], rsult)
        except Exception as e:
            strstring = "codRes=1002&mensaje=Hay un error en la configuracion del metodo de pago favor comuniquese con el administrador del servidor&orderId=#noexiste&transaccion=#noseobutuvo"
            return strstring
        return encrypted_text
    def _make_des3_encryptor(self, key):
        encryptor = DES3.new(key, DES3.MODE_ECB)
        return encryptor
    def des3_encrypt(self, key, data):
        encryptor = self._make_des3_encryptor(key)
        pad_len = 8 - len(data) % 8 # length of padding
        padding = chr(0) * pad_len # PKCS5 padding content
        data += padding
        return encryptor.encrypt(data)
    def des3_decrypt(self, key, data):
        encryptor = self._make_des3_encryptor(key)
        result = encryptor.decrypt(data)
        return result
     
    def tigomoney_get_form_action_url(self):
        return self._get_tigomoney_urls(self.environment)['tigomoney_form_url']


class TxTigomoney(models.Model):
    _inherit = 'payment.transaction'

    tigomoney_txn_type = fields.Char('Transaction type')
    tgm_datos_encript = fields.Char(string='Datos encriptados tigomoney')
    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _tigomoney_form_get_tx_from_data(self, data):
        reference = data.get('item_number') #, data.get('txn_id')
        if not reference:
            error_msg = _('Tigomoney: received data with missing reference (%s) or txn_id (%s)') % (reference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Tigomoney: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

     
    def _tigomoney_form_get_invalid_parameters(self, data):
        status = data.get('codRes')
        invalid_parameters = []
        res ={}
        if status == '14':
            _logger.info('Received notification for Tigomoney payment %s: set as pending' % (self.reference))
            invalid_parameters.append(('state', 'error', 'Favor verifique si el numero de telefono ingresado en sus datos es el correcto y si su billetera tiene saldo suficiente GRACIAS!'))
            self.state = 'error'
        elif status =='1002': #transaccion
            invalid_parameters.append(('state', 'error', self.acquirer_reference))
            self.state = 'error'      
        return invalid_parameters

     
    def _tigomoney_form_validate(self, data):
        status = data.get('codRes')
        transaccion = data.get('transaccion').replace("\x00", " ")
        res = {
            'acquirer_reference': data.get('item_number'),
            'tigomoney_txn_type': transaccion,
        }
        if status =='0':
            _logger.info('Validated Tigomoney payment for tx %s: set as done' % (self.reference))
            
            res.update(state='done')
            return self.write(res)
        else:
            error = 'Received unrecognized status for Tigomoney payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='error', state_message=error)
            return self.write(res)
