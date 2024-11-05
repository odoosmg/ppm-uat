# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class ppm_sale_route(models.Model):
#     _name = 'ppm_sale_route.ppm_sale_route'
#     _description = 'ppm_sale_route.ppm_sale_route'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
