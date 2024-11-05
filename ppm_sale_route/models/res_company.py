# -*- coding: utf-8 -*-

from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    default_gps_range = fields.Float()
