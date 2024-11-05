# -*- coding: utf-8 -*-
import json

from odoo import fields, models, api, _
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    global_discount = fields.Float(string="Global Discount(%)")
    discount_amount = fields.Monetary(compute="_compute_discount_amount", store=True)
    amount_after_discount = fields.Monetary(compute="_compute_amount_after_discount", store=True)
    ppm_sale_team_id = fields.Many2one('ppm.sale.team', string="Sale Team")
    sale_order_state = fields.Char(store=True, compute="_compute_sale_order_state")
    distributor_id = fields.Many2one('ppm.distributor')

    @api.depends('state')
    def _compute_sale_order_state(self):
        order_state = {
            'draft': 'a',
            'sale': 'b',
            'cancel': 'c'
        }
        for rec in self:
            rec.sale_order_state = order_state.get(rec.state)

    @api.depends('global_discount', 'order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax

            if order.global_discount and order.global_discount > 0:
                tmp_amount_total = order.amount_untaxed + order.amount_tax
                discount_amount = (order.global_discount / 100) * tmp_amount_total
            else:
                discount_amount = 0
            order.amount_total = (order.amount_untaxed + order.amount_tax) - discount_amount
        super()._compute_amounts()

    @api.depends_context('lang')
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id', 'global_discount')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            if order.global_discount:
                discount_amount = (order.global_discount / 100) * tax_totals['amount_total']
                tax_totals['amount_total'] = tax_totals['amount_total'] - discount_amount
                tax_totals['amount_untaxed'] = tax_totals['amount_untaxed'] - discount_amount
            order.tax_totals = tax_totals

    @api.onchange('user_id')
    def _onchange_user_id(self):
        sale_team = self.env['ppm.sale.member'].search([
            ('user_id', '=', self.user_id.id)
        ], limit=1)
        self.ppm_sale_team_id = sale_team.team_id.id if sale_team else False

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if 'user_id' in val and val.get('ppm_sale_team_id') is False:
                sale_team = self.env['ppm.sale.member'].search([
                    ('user_id', '=', val['user_id'])
                ], limit=1)
                if sale_team:
                    val['ppm_sale_team_id'] = sale_team.team_id.id
            if 'user_id' not in val:
                val['user_id'] = self.env.user.id
        return super().create(vals_list)

    @api.depends('global_discount', 'tax_totals')
    def _compute_discount_amount(self):
        for rec in self:
            rec.discount_amount = (rec.global_discount / 100) * rec.tax_totals['amount_total']

    @api.depends('global_discount', 'tax_totals')
    def _compute_amount_after_discount(self):
        for rec in self:
            if rec.global_discount:
                discount_amount = rec.tax_totals['amount_total'] - (rec.global_discount / 100) * rec.tax_totals[
                    'amount_total']
            else:
                discount_amount = rec.tax_totals['amount_total']
            rec.amount_after_discount = discount_amount
