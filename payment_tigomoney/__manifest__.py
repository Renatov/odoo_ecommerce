# -*- coding: utf-8 -*-

{
    "author": "PROSBOL",
    'name': 'Tigomoney Payment Acquirer',
    'category': 'Account',
    'license': 'AGPL-3',
    'summary': 'Payment Acquirer: Tigomomey Implementation',
    'version': '14.1.1',
    'description': """Tigomoney Payment Acquirer por favor instale primero la libreria pip3 install zeep""",
    'depends': ['payment', 'base_currency_iso_4217', "website_sale"],
    'data': [
        'views/payment_views.xml',
        'views/payment_tigomoney_templates.xml',
        'views/account_config_settings_views.xml',
        'data/payment_acquirer_data.xml',
        'views/templates.xml'
    ],
    'images': ['static/description/thumb.png'],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
