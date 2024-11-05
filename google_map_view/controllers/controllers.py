# -*- coding: utf-8 -*-
# from odoo import http


# class GoogleMapView(http.Controller):
#     @http.route('/google_map_view/google_map_view', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/google_map_view/google_map_view/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('google_map_view.listing', {
#             'root': '/google_map_view/google_map_view',
#             'objects': http.request.env['google_map_view.google_map_view'].search([]),
#         })

#     @http.route('/google_map_view/google_map_view/objects/<model("google_map_view.google_map_view"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('google_map_view.object', {
#             'object': obj
#         })
