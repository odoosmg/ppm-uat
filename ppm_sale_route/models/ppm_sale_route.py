# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class PPMSaleRoute(models.Model):
    _name = "ppm.sale.route"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "PPM Sale route"

    name = fields.Char()
    team_id = fields.Many2one('ppm.sale.team', required=True)
    manager_id = fields.Many2one(related="team_id.manager_id")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    user_id = fields.Many2one('res.users', required=True, string="Sale Man")
    line_ids = fields.One2many('ppm.sale.route.line', 'route_id', copy=True, auto_join=True)

    def action_view_sale_route_activity(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('ppm_sale_route.ppm_sale_route_line_activity_action')
        action['domain'] = [('user_id', '=', self.user_id.id)]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            sale_man = self.env['res.users'].browse(val['user_id'])
            val['name'] = "Route for: %s" % (sale_man.name)
        return super().create(vals_list)
