# -*- coding: utf-8 -*-
{
    'name': "PPM Pharmacy sale route",

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
    'version': '0.3.5',
    'license': 'OEEL-1',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'base_geolocalize', 'sale_crm', 'google_map_view', 'mail'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        "security/sale_order_rule.xml",
        "security/res_partner_rule.xml",
        "security/ppm_sale_member_rule.xml",
        "security/ppm_sale_team_rule.xml",
        "security/ppm_sale_route_rule.xml",
        "security/ppm_sale_route_line_rule.xml",
        "security/ppm_sale_route_line_activity_rule.xml",

        'data/ir_cron_data.xml',
        'data/mail_activity_type_data.xml',
        'data/ppm_sale_route_line_acitvity_subtype.xml',

        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/ppm_sale_team_views.xml',
        'views/ppm_sale_route_views.xml',
        'views/ppm_sale_route_line_views.xml',
        'views/ppm_sale_route_line_activity_views.xml',
        'views/sale_order_views.xml',
        'views/product_product_views.xml',
        'views/res_partner_type_views.xml',
        'views/sale_order_templates.xml',
        'views/ppm_sale_member_views.xml',
        'views/ppm_distributor_views.xml',

        'wizards/wizard_sale_member_change_password_views.xml',
        'wizards/wizard_assgin_customer_to_saleman_views.xml',

        'views/menu_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ppm_sale_route/static/src/views/fields/ppm_one2many/ppm_one2many.js'
            # 'ppm_sale_route/static/src/views/fields/ppm_activity/*'
        ]
    }
}
