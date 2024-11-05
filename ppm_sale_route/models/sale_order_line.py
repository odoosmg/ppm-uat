
# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    foc = fields.Float(string="FOC")
