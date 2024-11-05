# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class SaleMember(models.Model):
    _name = "ppm.sale.member"
    _description = "PPM Sale Member"

    name = fields.Char(related="user_id.name")
    company_id = fields.Many2one(related="team_id.company_id")
    user_id = fields.Many2one('res.users', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('id', 'not in', existing_user_ids)]", required=True)
    existing_user_ids = fields.Many2many('res.users', compute="_compute_existing_user_ids")
    phone = fields.Char(related="user_id.phone")
    login_id = fields.Char(related="user_id.login")
    email = fields.Char(related="user_id.email")
    last_login_date = fields.Datetime(related="user_id.login_date")
    team_id = fields.Many2one('ppm.sale.team')
    manager_id = fields.Many2one(related="team_id.manager_id")

    @api.depends('team_id.member_ids.user_id')
    def _compute_existing_user_ids(self):
        for rec in self:
            rec.existing_user_ids = self.mapped("team_id.member_ids.user_id")._origin

    def action_change_password(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('ppm_sale_route.action_sale_member_change_password')
        action['context'] = {'active_user_id': self.user_id.id}
        return action

    def action_view_partner(self):
        self.ensure_one()
        return {
            'name': _('Detail'),
            'res_model': 'res.partner',
            'views': [[False, 'form']],
            'type': 'ir.actions.act_window',
            "res_id": self.user_id.partner_id.id,
            'context': dict(
                self.env.context,
                edit=True,
                form_view_initial_mode='edit',
            ),
        }

    def action_open_route(self):
        self.ensure_one()
        sale_route = self.env['ppm.sale.route'].search([('user_id', '=', self.user_id.id)], limit=1)
        return {
            'name': _('Route'),
            'res_model': 'ppm.sale.route',
            'views': [[False, 'form']],
            'type': 'ir.actions.act_window',
            "res_id": sale_route.id,
            'context': dict(
                self.env.context,
                edit=True,
                form_view_initial_mode='edit',
                default_user_id=self.user_id.id,
                default_team_id=self.team_id.id,
            ),
            'domain': [('user_id', '=', self.user_id.id)]
        }
