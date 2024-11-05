# -*- coding: utf-8 -*-
{
    'name': "Google Map View",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['web', 'contacts', 'base_setup', 'base_geolocalize', 'sale'],

    # always loaded
    'data': [

    ],
    'assets': {
        'web.assets_backend': [
            'google_map_view/static/src/**/*',
        ],
    }
}
