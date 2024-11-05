# -*- coding: utf-8 -*-

from odoo import fields, api, models, _


class PartnerType(models.Model):
    _name = "res.partner.type"

    name = fields.Char(required=True)
    color_code = fields.Char(default="#e9ecef")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
