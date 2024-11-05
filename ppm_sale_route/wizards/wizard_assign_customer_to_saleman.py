# -*- coding: utf-8 -*-

from odoo import fields, models, Command, api, _
from odoo.exceptions import UserError


class WizardAssignCustomerToSaleMan(models.TransientModel):
    _name = "wizard.assign.customer.saleman"
    _description = "Wizard assign customer to saleman"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    sale_man_ids = fields.Many2many('res.users', domain="[('company_id', '=', company_id)]", required=True)

    def action_validate(self):
        self.ensure_one()
        if not self.sale_man_ids:
            raise UserError(_("Salesman can't blank"))

        if self._context.get('active_ids') and self._context.get('active_model') == 'res.partner':
            active_customs = self.env['res.partner'].browse(self._context.get('active_ids'))
            for rec in active_customs:
                user_list = rec.ppm_sale_man.ids + self.sale_man_ids.ids
                rec.ppm_sale_man = [Command.set(ids=user_list)]

