# See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Multi-Image Zoom',
    'category': 'Website',
    'summary': 'Image Zoom For Product In WebSite',
    'author': 'PROSBOL',
    'maintainer': 'PROSBOL.',
    'website': 'https://www.prosbol.com',
    'version': '14.0.2',
    'license': 'AGPL-3',
    'depends': [
        'website_sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_images.xml',
        'views/templates.xml',
    ],
    'images': ['static/description/zoom.png'],
    'installable': True,
}
