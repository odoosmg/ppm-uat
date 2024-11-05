# _*_ coding: utf-8 _*_

from odoo import fields, models


class View(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(selection_add=[('google_map_view', "Google Map")])
