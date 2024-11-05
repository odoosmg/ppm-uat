# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import fields, Command, models, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_code = fields.Char()
    customer_address = fields.Char()
    gps_range = fields.Float(default=20)
    customer_status = fields.Selection([('pending', 'Pending'), ('approve', 'Approve'), ('reject', 'Reject')],
                                       default="pending", tracking=True)
    customer_type = fields.Many2one('res.partner.type')
    ppm_sale_man = fields.Many2many('res.users', string="Salesman")
    link_to_map = fields.Char(compute="_compute_link_to_map", store=True)
    show_approve_button = fields.Boolean(compute="_compute_show_approve_button", store=True)
    show_gps_range = fields.Boolean(compute="_compute_show_gps_range")
    is_link_to_user = fields.Boolean(compute="_compute_is_link_to_user")

    def _compute_is_link_to_user(self):
        for rec in self:
            rec.is_link_to_user = True if rec.user_ids else False

    def _compute_show_gps_range(self):
        for rec in self:
            rec.show_gps_range = False if rec.user_ids else True

    @api.depends('user_ids', 'customer_status', 'type')
    def _compute_show_approve_button(self):
        for rec in self:
            rec.show_approve_button = rec.type == 'contact' and rec.customer_status not in ['approve', 'reject'] and not rec.user_ids

    def action_open_google_map(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.link_to_map,
            "target": "new",
        }

    @api.depends('partner_latitude', 'partner_longitude')
    def _compute_link_to_map(self):
        map_base = 'https://www.google.com/maps/search/?api=1&query='
        for rec in self:
            rec.link_to_map = f'{map_base}{rec.partner_latitude},{rec.partner_longitude}'

    _sql_constraints = [
        ('customer_code_uniq', 'unique (customer_code)', 'The customer code must be unique!')
    ]

    def _act_clear_activities(self):
        """
        When Any approver approved, it will automatically make another approver as done action
        :return:
        """
        domain = [
            ('res_model', '=', 'res.partner'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ppm_sale_route.mail_activity_data_customer_to_approve').id),
        ]
        activities = self.env['mail.activity'].search(domain)
        for activity in activities:
            activity.action_done()

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'res.partner'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ppm_sale_route.mail_activity_data_customer_to_approve').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain, limit=1)
        return activities

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['gps_range'] = self.env.company.default_gps_range
            if 'customer_code' in val and not val['customer_code']:
                val['customer_status'] = 'pending'
        res = super().create(vals_list)
        for val in res:
            if val.customer_status == 'pending':
                users_activity = self.env.ref("ppm_sale_route.ppt_pharmacy_group_administrator")
                # Create approval schedule action for user in group PPM Administrator
                for user in users_activity.users:
                    val.activity_schedule('ppm_sale_route.mail_activity_data_customer_to_approve', user_id=user.id)
        return res

    def _track_subtype(self, init_values):
        # init_values contains the modified fields' values before the changes
        #
        # the applied values can be accessed on the record as they are already
        # in cache
        self.ensure_one()
        if 'customer_status' in init_values and self.customer_status == 'pending':
            return self.env.ref('ppm_sale_route.ppm_sale_route_line_activity_state_change')
        return super(ResPartner, self)._track_subtype(init_values)

    def write(self, vals):
        vals['gps_range'] = max(0, vals.get('gps_range', 0))
        if 'customer_code' in vals and not vals['customer_code']:
            vals['customer_status'] = 'pending'
        res = super().write(vals)

        if 'ppm_sale_man' not in vals or not vals['ppm_sale_man'][0][2] or self.env.context.get('no_create', False):
            return res

        if 'ppm_sale_man' in vals and not self.env.context.get('no_create', False):
            if vals['ppm_sale_man'][0][2]:
                user_list = list(set(vals['ppm_sale_man'][0][2] + self.ppm_sale_man.ids))
                # Remove all route line that linked to this partner that salesman didn't within user_list
                existing_routes = self.env['ppm.sale.route.line'].sudo().search([
                    ('user_id', 'not in', user_list),
                    ('partner_id', '=', self.id)
                ])
                existing_routes.sudo().unlink()
                for user in user_list:
                    route_by_user = self.env['ppm.sale.route'].sudo().search([
                        ('user_id', '=', user)
                    ], limit=1)
                    if not route_by_user:
                        ppm_member = self.env['ppm.sale.member'].sudo().search([('user_id', '=', user)], limit=1)
                        self.env['ppm.sale.route'].sudo().create({
                            'user_id': ppm_member.user_id.id,
                            'team_id': ppm_member.team_id.id,
                            'company_id': ppm_member.team_id.company_id.id,
                            'manager_id': ppm_member.team_id.manager_id.id,
                            'line_ids': [Command.create({
                                'partner_id': self.id
                            })]
                        })
                    else:
                        if not any(line.partner_id.id == self.id for line in route_by_user.line_ids):
                            route_by_user.write({
                                'line_ids': [Command.create({
                                    'partner_id': self.id,
                                })]
                            })
            else:
                # Remove all sale route line that linked to this customer, because salesman is blank
                existing_routes = self.env['ppm.sale.route.line'].sudo().search([
                    ('partner_id', '=', self.id)
                ])
                existing_routes.sudo().unlink()

        if 'customer_status' in vals and vals['customer_status'] == 'pending':
            users_activity = self.env.ref("ppm_sale_route.ppt_pharmacy_group_administrator")
            for user in users_activity.sudo().users:
                self.activity_schedule('ppm_sale_route.mail_activity_data_customer_to_approve', user_id=user.id)
        return res

    def action_approve(self):
        self.ensure_one()
        if not self.customer_code:
            raise UserError("Please input customer code")
        self.update({'customer_status': 'approve'})
        self._get_user_approval_activities(user=self.env.user).action_feedback()
        self._act_clear_activities()

    def action_reject(self):
        self.ensure_one()
        self.update({'customer_status': 'reject'})
        self._get_user_approval_activities(user=self.env.user).action_feedback()
