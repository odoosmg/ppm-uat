# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import fields, Command, models, api, _


class PPMDistributor(models.Model):
    _name = "ppm.distributor"
    _description = "PPM Distributor"

    name = fields.Char(required=True)
    phone = fields.Char()
    email = fields.Char()
    address = fields.Char()
