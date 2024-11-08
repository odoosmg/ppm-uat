# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime,date
from odoo.exceptions import Warning

class InternalRequisition(models.Model):
    _name = 'internal.requisition'
    _description = 'Internal Requisition'
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin']      #   odoo11
    _order = 'id desc'
    
    #@api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel', 'reject'):
                raise Warning(_('You can not delete Internal Requisition which is not in draft or cancelled or rejected state.'))
        return super(InternalRequisition, self).unlink()
    
    name = fields.Char(
        string='Number',
        index=True,
        readonly=1,
    )
    state = fields.Selection([
        ('draft', 'New'),
        ('confirm', 'Waiting Department Approval'),
        ('manager', 'Waiting IR Approved'),
        ('user', 'Approved'),
        ('stock', 'Requested Stock'),
        ('receive', 'Received'),
#         ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')],
        default='draft',
        track_visibility='onchange',
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
        #related='request_emp.department_id',
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
        #related='request_emp.company_id',
        default=lambda self: self.env.user.company_id,
        required=True,
        copy=True,
    )
    location = fields.Many2one(
        'stock.location',
        string='Source Location',
        #required=True,
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
        #default=fields.Date.today(),
        readonly=True,
        copy=False,
    )
    manareject_date = fields.Date(
        string='Department Manager Reject Date',
        #default=fields.Date.today(),
        readonly=True,
    )
    userreject_date = fields.Date(
        string='Rejected Date',
        #default=fields.Date.today(),
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string='Approved Date',
        #default=fields.Date.today(),
        readonly=True,
        copy=False,
    )
    receive_date = fields.Date(
        string='Received Date',
        #default=fields.Date.today(),
        readonly=True,
        copy=False,
    )
    reason = fields.Text(
        string='Reason for Requisitions',
        required=False,
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
        required=False,
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
        #default=fields.Date.today(),
        readonly=True,
        copy=False,
    )
    custom_picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        copy=False,
    )
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag', string='Analytic Tag'
    )
    
    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('internal.requisition.seq')
        vals.update({
            'name': name
            })
        res = super(InternalRequisition, self).create(vals)
        return res
        
    #@api.multi
    def requisition_confirm(self):
        for rec in self:
            manager_mail_template = self.env.ref('material_internal_requisitions.email_confirm_irrequisition')
            rec.confirm_id = rec.request_emp.id
            rec.confirm_date = fields.Date.today()
            rec.state = 'confirm'
            if manager_mail_template:
                manager_mail_template.send_mail(self.id)
            
    #@api.multi
    def requisition_reject(self):
        for rec in self:
            rec.state = 'reject'
            rec.reject_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            rec.userreject_date = fields.Date.today()

    #@api.multi
    def manager_approve(self):
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.approve_manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            employee_mail_template = self.env.ref('material_internal_requisitions.email_internal_requisition_iruser_custom')
            email_iruser_template = self.env.ref('material_internal_requisitions.email_ir_requisition')
            employee_mail_template.sudo().send_mail(self.id)
            email_iruser_template.sudo().send_mail(self.id)
            rec.state = 'manager'

    #@api.multi
    def user_approve(self):
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            rec.state = 'user'

    #@api.multi
    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    #@api.multi
    def request_stock(self):
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        #internal_obj = self.env['stock.picking.type'].search([('code','=', 'internal')])
#         internal_obj = self.env['stock.picking.type'].search([('usage','=', 'internal')], limit=1)
#         if not internal_obj:
#             raise UserError(_('Please configure Internal Picking Type under Inventory.'))
        for rec in self:
            if not rec.location:
                raise Warning(_('Select Source Location under the picking details.'))
            
            if not rec.custom_picking_type_id:
                raise Warning(_('Select Picking Type under the picking details.'))

            if not rec.desti_loca_id:
                raise Warning(_('Select Destination Location under the picking details.'))
            #if not rec.request_emp.desti_loca_id or not rec.request_emp.department_id.desti_loca_id:
             #   raise Warning(_('Select Destination Location under the picking details.'))
            vals = {
                'partner_id' : rec.request_emp.sudo().address_home_id.id,
                # 'min_date' : fields.Date.today(), #odoo13
                'location_id' : rec.location.id,
                #'location_dest_id' : rec.desti_loca_id.id,
                'location_dest_id' : rec.desti_loca_id and rec.desti_loca_id.id or rec.request_emp.sudo().desti_loca_id.id or rec.request_emp.sudo().department_id.desti_loca_id.id,
                'picking_type_id' : rec.custom_picking_type_id.id,#internal_obj.id,
                'name' : rec.name + '/' + rec.custom_picking_type_id.name,#internal_obj.name,
                'note' : rec.reason,
                'inter_requi_id' : rec.id,
                'origin' : rec.name,
                'company_id' : rec.company_id.id,
            }
            stock_id = stock_obj.create(vals)
            for line in rec.requisition_line_ids:
            
                vals1 = {
                    'product_id' : line.product_id.id,
                    'product_uom_qty' : line.qty,
                    'product_uom' : line.uom.id,
                    'location_id' : rec.location.id,
                    'location_dest_id' : rec.request_emp.desti_loca_id.id,
                    'name' : line.description,
                    'picking_id' : stock_id.id,
                    'company_id' : line.requisition_id.company_id.id,
                }
                move_id = move_obj.create(vals1)
            vals3 = {
                'delivery_picking_id' : stock_id.id,
            }
            rec.write(vals3)
            rec.state = 'stock'
    
    #@api.multi
    def action_received(self):
        for rec in self:
            rec.receive_date = fields.Date.today()
            rec.state = 'receive'
    
    #@api.multi
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
    
#     @api.multi
#     def action_done(self):
#         for rec in self:
#             rec.state = 'done'
            
    @api.onchange('request_emp')
    def set_department(self):
        for rec in self:
            rec.department_id = rec.request_emp.sudo().department_id.id
            rec.desti_loca_id = rec.request_emp.desti_loca_id.id or rec.request_emp.department_id.desti_loca_id.id 
            
    #@api.multi
    def show_picking(self):
#        for rec in self:
        self.ensure_one()
        res = self.env.ref('stock.action_picking_tree_all')
        res = res.read()[0]
        res['domain'] = str([('inter_requi_id','=',self.id)])
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
