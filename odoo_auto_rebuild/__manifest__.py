# -*- coding: utf-8 -*-
{
    'name': 'Odoo Auto Rebuild',
    'version': '1.0',
    'summary': 'Automatically rebuild database and filestore from production to UAT',
    'description': 'This module automates the process of rebuilding the database and filestore from production to UAT.',
    'author': 'Vutha',
    'category': 'Tools',
    'depends': [],
    'data': [
        'security/ir.model.access.csv',
        'data/auto_rebuild_cron.xml',
        'views/auto_rebuild_view.xml',
    ],
    'website': "http://www.somagroup.com.kh/",
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'demo': [],
    'images': ['static/description/coverv16.gif'],
    'auto_install': False,
}