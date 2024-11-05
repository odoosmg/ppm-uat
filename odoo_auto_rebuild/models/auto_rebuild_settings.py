# odoo_auto_rebuild/models/auto_rebuild_settings.py

from odoo import models, fields, tools, api

config = tools.config
live_filestore = '%s/filestore/%s'.format(config.get('data_dir'), config.get('db_name'))


class AutoRebuildSettings(models.Model):
    _name = 'auto.rebuild.settings'
    _description = 'Auto Rebuild Settings'

    name = fields.Char()
    active = fields.Boolean(default=True)
    prod_db_name = fields.Char(string='Production Database Name', default=config.get('db_name', ''), required=True)
    prod_db_user = fields.Char(string='Production Database User', default=config.get('db_user', ''), required=True)
    prod_db_password = fields.Char(string='Production Database Password', default=config.get('db_password', ''), required=True)
    prod_host = fields.Char(string='Production Host', required=True, default="db")
    prod_filestore = fields.Char(string='Production Filestore Path', default=live_filestore, required=True)
    uat_db_name = fields.Char(string='UAT Database Name', required=True)
    uat_db_user = fields.Char(string='UAT Database User', default=config.get('db_user', ''), required=True)
    uat_db_password = fields.Char(string='UAT Database Password', default=config.get('db_password', ''), required=True)
    uat_host = fields.Char(string='UAT Host', default="web-uat", required=True)
    uat_filestore = fields.Char(string='UAT Filestore Path', required=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = 'UAT Configure'
        return super().create(vals_list)

    # @api.onchange('uat_db_name')
    # def _onchange_uat_db_name(self):
    #     if self.uat_db_name:
            # uat_filestore = config.get('data_dir', '') + '/filestore/' + self.uat_db_name
            # self.uat_filestore = uat_filestore
