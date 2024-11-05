# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SaleTeam(models.Model):
    _name = "ppm.sale.team"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "PPM sale team"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    telegram_chat_id = fields.Char()
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    manager_id = fields.Many2one('res.users', domain="[('company_id', '=', company_id)]", required=True, tracking=True)
    member_ids = fields.One2many('ppm.sale.member', 'team_id', tracking=True)
    can_edit_manager_id = fields.Boolean(compute="_compute_can_edit_manager_id")

    def _compute_can_edit_manager_id(self):
        for rec in self:
            rec.can_edit_manager_id = self.env.user.has_group('ppm_sale_route.ppt_pharmacy_group_administrator')
