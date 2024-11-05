# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class WizardSaleMemberChangePassword(models.TransientModel):
    _name = "wizard.member.change.password"
    _description = "Wizard member change password"

    new_password = fields.Char(required=True)

    def action_change_password(self):
        self.ensure_one()
        if not self.new_password.strip():
            raise UserError(_("New password can't blank or empty"))
        user_sudo = self.env['res.users'].sudo()
        user = user_sudo.browse(self._context.get('active_user_id'))
        user.sudo()._change_password(self.new_password)
        return user.sudo().action_generate_token(user)
