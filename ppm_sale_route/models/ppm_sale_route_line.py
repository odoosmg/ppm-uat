# -*- coding: utf-8 -*-
import datetime
import logging
from odoo import fields, models, Command, api, _

_logger = logging.getLogger(__name__)

ACTIVITY_STATUS = {
    'todo': "Todo",
    'check-in': "Check In",
    'check-out': "Check Out",
    "check-out-order": 'Check out with order'
}


class PPMSaleRouteLine(models.Model):
    _name = "ppm.sale.route.line"
    _description = "PPM Sale route line"

    name = fields.Char(compute="_compute_name", store=True)

    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="route_id.company_id")
    partner_id = fields.Many2one('res.partner', required=True)
    # partner_id = fields.Many2one('res.partner', string="Customer", required=True,
    #                              domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('id', 'not in', existing_partner_ids)]")
    # existing_partner_ids = fields.Many2many('res.partner', compute="_compute_existing_partner_ids")
    customer_code = fields.Char(related="partner_id.customer_code")
    customer_address = fields.Char(related="partner_id.customer_address")
    week1 = fields.Boolean(string="W1")
    week2 = fields.Boolean(string="W2")
    week3 = fields.Boolean(string="W3")
    week4 = fields.Boolean(string="W4")
    mon_day = fields.Boolean(string="Mon")
    tue_day = fields.Boolean(string="Tue")
    wed_day = fields.Boolean(string="Wed")
    thu_day = fields.Boolean(string="Thu")
    fri_day = fields.Boolean(string="Fri")
    sat_day = fields.Boolean(string="Sat")
    route_id = fields.Many2one('ppm.sale.route', ondelete='cascade', index=True, copy=False)
    team_id = fields.Many2one(related="route_id.team_id")
    user_id = fields.Many2one('res.users', compute="_compute_user_id", store=True)
    activity_ids = fields.One2many('ppm.sale.route.line.activity', 'route_id')

    def unlink(self):
        for record in self:
            salesman = self.env['res.partner'].search([('id', '=', record.partner_id.id)])
            for rec in salesman:
                new_salesman = []
                for item in rec.ppm_sale_man.filtered(lambda user: user.id != record.route_id.user_id.id):
                    new_salesman.append(item.id)
                rec.with_context(no_create=True).write({
                    'ppm_sale_man': [Command.set(new_salesman)]
                })
        return super(PPMSaleRouteLine, self).unlink()

    @api.model
    def create_schedule_activity_list(self, current_date: datetime) -> list:
        activity = self.env['ppm.sale.route.line.activity'].search([
            ('route_id', '=', self.id),
            ('partner_id', '=', self.partner_id.id)
        ], order="id desc", limit=1)
        if activity:
            created_date = fields.Date.from_string(activity.create_date)
            c_date = fields.Date.from_string(current_date)
            if created_date < c_date:
                return [{
                    'partner_id': self.partner_id.id,
                    'user_id': self.user_id.id,
                    'activity_type': 'todo',
                    'todo_date': fields.Date.today(),
                    'route_id': self.id
                }]
        else:
            return [{
                'partner_id': self.partner_id.id,
                'user_id': self.user_id.id,
                'activity_type': 'todo',
                'todo_date': fields.Date.today(),
                'route_id': self.id
            }]
        return []

    @api.model
    def should_create_schedule_activity(self, current_date: datetime) -> bool:
        week_number = (current_date.day - 1) // 7 + 1
        weekday_name = current_date.strftime('%a').lower()
        weekday_mapped = {
            'mon': self.mon_day,
            'tue': self.tue_day,
            'wed': self.wed_day,
            'thu': self.thu_day,
            'fri': self.fri_day,
            'sat': self.sat_day,
            'sun': False
        }
        week_map = {
            1: self.week1,
            2: self.week2,
            3: self.week3,
            4: self.week4,
        }

        if (current_date.month == 2 and current_date.day == 29) or week_number == 5:
            week_number = 4
        return week_map.get(week_number, False) and weekday_mapped.get(weekday_name, False)

    def _cron_job_create_sale_activity(self):
        current_date = fields.Datetime.now()
        _logger.info(f"PPM Cron job create sale activity: {current_date}")
        for rec in self.search([]):
            if rec.should_create_schedule_activity(current_date):
                _logger.info(f"PPM cron job: create schedule activity {rec.id}, {current_date}")
                activity_to_create = rec.create_schedule_activity_list(current_date)
                if activity_to_create:
                    for activity in activity_to_create:
                        self.env['ppm.sale.route.line.activity'].sudo().create(activity)

    def ppm_sale_route_line_activity_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('ppm_sale_route.ppm_sale_route_line_activity_action')
        action['domain'] = [('route_id', '=', self.route_id.id)]
        action['context']['form_view_initial_mode'] = 'edit'
        return action

    def ppm_sale_route_line_activity_view_map(self):
        self.ensure_one()
        pass

    @api.depends('route_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = rec.route_id.user_id

    @api.depends('partner_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f'{rec.partner_id.name}'


class SaleRouteLineActivity(models.Model):
    _name = "ppm.sale.route.line.activity"
    _description = "PPM Sale route line activity"

    display_name = fields.Char(compute="_compute_display_name")
    name = fields.Char(compute="_compute_name")
    activity_type = fields.Selection([
        ('todo', 'Todo'),
        ('check-in', 'Check In'),
        ('check-out', 'Check Out'),
        ('check-out-order', 'Check out with order')], string="Status",
        compute="_compute_activity_type", store=True)
    latitude = fields.Char(compute="_compute_lat_long", store=True)
    longitude = fields.Char(compute="_compute_lat_long", store=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    todo_date = fields.Date()
    check_in_date = fields.Datetime()
    check_out_date = fields.Datetime()
    route_id = fields.Many2one('ppm.sale.route.line')
    remark = fields.Char()
    has_order = fields.Boolean()
    photo = fields.Binary()
    user_id = fields.Many2one('res.users', string="Salesperson")
    photo_lat = fields.Char(string="Photo Latitude")
    photo_long = fields.Char(string="Photo Longitude")
    state_color = fields.Char(compute="_compute_state_color", store=True)

    @api.depends('activity_type')
    def _compute_state_color(self):
        for rec in self:
            color_state = {
                'todo': '#212529',
                'check-in': '#008000',
                'check-out': '#0000ff',
                'check-out-order': '#212529',
            }
            rec.state_color = color_state[rec.activity_type]

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.partner_id.name

    @api.depends('partner_id')
    def _compute_lat_long(self):
        for rec in self:
            rec.update({
                'latitude': rec.partner_id.partner_latitude,
                'longitude': rec.partner_id.partner_longitude,
            })

    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.partner_id.name} ({rec.create_date.strftime('%d-%b-%Y')}, {ACTIVITY_STATUS[rec.activity_type]}) "

    @api.depends('check_in_date', 'check_out_date', 'has_order', 'todo_date')
    def _compute_activity_type(self):
        for rec in self:
            if rec.check_out_date and rec.has_order:
                status = 'check-out-order'
            elif rec.check_out_date and not rec.has_order:
                status = 'check-out'
            elif rec.check_in_date:
                status = 'check-in'
            else:
                status = 'todo'
            rec.activity_type = status
