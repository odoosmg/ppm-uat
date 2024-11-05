# odoo_auto_rebuild/controllers/main.py

from odoo import http

class AutoRebuildController(http.Controller):

    @http.route('/auto_rebuild/rebuild', auth='user', type='json')
    def rebuild(self):
        http.request.env['auto.rebuild'].create({}).button_rebuild()
        return {'status': 'success', 'message': 'Rebuild process initiated'}
