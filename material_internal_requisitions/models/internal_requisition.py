# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError


class InternalRequisition(models.Model):
    _name = 'internal.requisition'
    _description = 'Internal Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel', 'reject'):
                raise UserError(
                    _('You cannot delete Internal Requisition which is not in draft, cancelled, or rejected state.'))
        return super(InternalRequisition, self).unlink()

    name = fields.Char(
        string='Number',
        index=True,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'New'),
        ('confirm', 'Waiting Department Approval'),
        ('manager', 'Waiting IR Approval'),
        ('user', 'Approved'),
        ('stock', 'Requested Stock'),
        ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')],
        default='draft',
        tracking=True,
    )
    request_date = fields.Date(
        string='Requisition Date',
        default=fields.Date.today(),
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        copy=True,
    )
    request_emp = fields.Many2one(
        'hr.employee',
        string='Employee',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        required=True,
        copy=True,
    )
    approve_manager = fields.Many2one(
        'hr.employee',
        string='Department Manager',
        readonly=True,
        copy=False,
    )
    reject_manager = fields.Many2one(
        'hr.employee',
        string='Department Manager Reject',
        readonly=True,
    )
    approve_user = fields.Many2one(
        'hr.employee',
        string='Approved by',
        readonly=True,
        copy=False,
    )
    reject_user = fields.Many2one(
        'hr.employee',
        string='Rejected by',
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        required=True,
        copy=True,
    )
    location = fields.Many2one(
        'stock.location',
        string='Source Location',
        copy=True,
    )
    requisition_line_ids = fields.One2many(
        'custom.internal.requisition.line',
        'requisition_id',
        string='Requisitions Line',
        copy=True,
    )
    date_end = fields.Date(
        string='Requisition Deadline',
        readonly=True,
        help='Last date for the product to be needed',
        copy=True,
    )
    date_done = fields.Date(
        string='Date Done',
        readonly=True,
        help='Date of Completion of Internal Requisition',
    )
    managerapp_date = fields.Date(
        string='Department Approval Date',
        readonly=True,
        copy=False,
    )
    manareject_date = fields.Date(
        string='Department Manager Reject Date',
        readonly=True,
    )
    userreject_date = fields.Date(
        string='Rejected Date',
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string='Approved Date',
        readonly=True,
        copy=False,
    )
    receive_date = fields.Date(
        string='Received Date',
        readonly=True,
        copy=False,
    )
    reason = fields.Text(
        string='Reason for Requisitions',
        copy=True,
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        copy=True,
    )
    desti_loca_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        copy=True,
    )
    delivery_picking_id = fields.Many2one(
        'stock.picking',
        string='Internal Picking',
        readonly=True,
        copy=False,
    )
    requisiton_responsible_id = fields.Many2one(
        'hr.employee',
        string='Requisition Responsible',
        copy=True,
    )
    confirm_id = fields.Many2one(
        'hr.employee',
        string='Confirmed by',
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        string='Confirmed Date',
        readonly=True,
        copy=False,
    )
    custom_picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        copy=False,
    )
    # analytic_tag_ids = fields.Many2many(
    #     'account.analytic.tag', string='Analytic Tag'
    # )

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('internal.requisition.seq')
        vals.update({
            'name': name
        })
        return super(InternalRequisition, self).create(vals)

    def requisition_confirm(self):
        for rec in self:
            manager_mail_template = self.env.ref('material_internal_requisitions.email_confirm_irrequisition')
            rec.confirm_id = rec.request_emp.id
            rec.confirm_date = fields.Date.today()
            rec.state = 'confirm'
            if manager_mail_template:
                manager_mail_template.send_mail(self.id)

    def requisition_reject(self):
        for rec in self:
            rec.state = 'reject'
            rec.reject_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            rec.userreject_date = fields.Date.today()

    def manager_approve(self):
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.approve_manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            employee_mail_template = self.env.ref(
                'material_internal_requisitions.email_internal_requisition_iruser_custom')
            email_iruser_template = self.env.ref('material_internal_requisitions.email_ir_requisition')
            if employee_mail_template:
                employee_mail_template.sudo().send_mail(self.id)
            if email_iruser_template:
                email_iruser_template.sudo().send_mail(self.id)
            rec.state = 'manager'

    def user_approve(self):
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            rec.state = 'user'

    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def request_stock(self):
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for rec in self:
            if not rec.location:
                raise Warning(_('Select Source Location under the picking details.'))

            if not rec.custom_picking_type_id:
                raise Warning(_('Select Picking Type under the picking details.'))

            if not rec.desti_loca_id:
                raise Warning(_('Select Destination Location under the picking details.'))

            vals = {
                'partner_id': rec.request_emp.sudo().address_home_id.id,
                'location_id': rec.location.id,
                'location_dest_id': rec.desti_loca_id.id if rec.desti_loca_id else (
                            rec.request_emp.sudo().desti_loca_id.id or rec.request_emp.sudo().department_id.desti_loca_id.id),
                'picking_type_id': rec.custom_picking_type_id.id,
                'name': f"{rec.name}/{rec.custom_picking_type_id.name}",
                'note': rec.reason,
                'inter_requi_id': rec.id,
                'origin': rec.name,
                'company_id': rec.company_id.id,
            }
            stock_id = stock_obj.create(vals)
            for line in rec.requisition_line_ids:
                vals1 = {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    'product_uom': line.uom.id,
                    'location_id': rec.location.id,
                    'location_dest_id': rec.request_emp.desti_loca_id.id,
                    'name': line.description,
                    'picking_id': stock_id.id,
                    'company_id': line.requisition_id.company_id.id,
                }
                move_obj.create(vals1)
            rec.write({'delivery_picking_id': stock_id.id})
            rec.state = 'stock'

    def action_received(self):
        for rec in self:
            rec.receive_date = fields.Date.today()
            rec.state = 'receive'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    @api.onchange('request_emp')
    def set_department(self):
        for rec in self:
            rec.department_id = rec.request_emp.sudo().department_id.id
            rec.desti_loca_id = rec.request_emp.desti_loca_id.id if rec.request_emp.desti_loca_id else rec.request_emp.department_id.desti_loca_id.id

    def show_picking(self):
        self.ensure_one()
        res = self.env.ref('stock.action_picking_tree_all')
        res = res.read()[0]
        res['domain'] = [('inter_requi_id', '=', self.id)]
        return res
