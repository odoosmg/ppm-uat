# -*- coding: utf-8 -*-

import base64
import functools
import json
import logging

from odoo import http, fields, Command, _, tools
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, html2plaintext

_logger = logging.getLogger(__name__)
config = tools.config


def validate_token(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        if not request:
            raise UserError("this method can only be accessed over Http")

        authorization_header = request.httprequest.headers.get('Authorization')
        if not authorization_header:
            data = {
                'status': 401,
                'error': {
                    'code': 401,
                    'message': "No Authorization header"
                }
            }
            return request.make_json_response(data, status=401)
        try:
            _, access_token = authorization_header.split(' ')
            # return access_token
        except ValueError as e:
            data = {
                'status': 401,
                'error': {
                    'code': 401,
                    'message': str(e)
                }
            }
            return request.make_json_response(data, status=401)

        if not access_token:
            data = {
                'status': 401,
                'error': {
                    'code': 401,
                    'message': "Missing access token in request header"
                }
            }
            return request.make_json_response(data, status=401)

        user_by_token = request.env["res.users"].sudo().search([("ppm_sale_access_token", "=", access_token)],
                                                               order="id DESC", limit=1)

        if user_by_token.find_or_create_token(user=user_by_token) != access_token:
            data = {
                'status': 401,
                'error': {
                    'code': 401,
                    'message': "Token seems to have expired or invalid"
                }
            }
            return request.make_json_response(data, status=401)

        request.update_env(user=user_by_token)

        return func(self, *args, **kwargs)

    return wrap


class PPMSaleRouteController(http.Controller):
    _distributor_per_page = 40
    _customer_per_page = 20
    _order_per_page = 10
    _product_per_page = 20

    def _get_user_by_token(self, access_token):
        _, access_token = access_token.split(' ')
        user_by_token = request.env["res.users"].sudo().search([
            ("ppm_sale_access_token", "=", access_token)
        ], order="id DESC", limit=1)
        return user_by_token

    def _get_today_activities(self, user_id:int):
        """Retrieves sales activities for the given user that were created today."""
        today = fields.Date.today()
        domain = [('user_id', '=', user_id)]
        activities = request.env['ppm.sale.route.line.activity'].sudo().search(domain, order="id desc")
        return activities.filtered(lambda x: fields.Date.from_string(x.create_date) == today)

    def _format_activity_data(self, activity):
        """Formats an activity's data into a dictionary for the API response."""
        return {
            'id': activity.id,
            'customer_name': activity.partner_id.name,
            'partner_id': activity.partner_id.id if activity.partner_id else 0,
            'user_id': activity.user_id.id if activity.user_id else 0,
            'todo_date': activity.create_date.strftime('%d-%b-%Y'),
            'check_in_date': activity.check_in_date.strftime('%d-%b-%Y') if activity.check_in_date else '',
            'check_out_date': activity.check_out_date.strftime('%d-%b-%Y') if activity.check_out_date else '',
            'status': activity.activity_type,
            'address': activity.partner_id.customer_address or '',
            'customer_code': activity.partner_id.customer_code or '',
            'lat': activity.partner_id.partner_latitude,
            'long': activity.partner_id.partner_longitude,
            'photo': activity.photo if activity.photo else '',
            'photo_lat': activity.photo_lat if activity.photo_lat else '',
            'photo_long': activity.photo_long if activity.photo_long else '',
            'has_order': True if activity.has_order else False,
            'remark': activity.remark if activity.remark else '',
            'gps_range': activity.partner_id.gps_range or 0.0
        }

    def _format_check_out_data(self, activity):
        return {
            'customer_name': activity.partner_id.name,
            'check_out_date': activity.check_out_date.strftime('%d-%b-%Y') if activity.check_out_date else '',
            'todo_date': activity.todo_date.strftime('%d-%b-%Y') if activity.todo_date else '',
            'check_in_date': activity.check_in_date.strftime('%d-%b-%Y') if activity.check_in_date else '',
            'remark': activity.remark if activity.remark else '',
            'photo_lat': activity.photo_lat if activity.photo_lat else 0,
            'photo_long': activity.photo_long if activity.photo_long else 0,
            'has_order': True if activity.has_order else False,
            'photo': activity.photo if activity.photo else ''
        }

    def _get_activity_photo_url(self, activity):
        return f"{activity.route_id.company_id.get_base_url()}/web/image?model=ppm.sale.route.line.activity&id={activity.id}&field={activity.photo}",

    def _get_user_profile_photo_url(self, user):
        base_url = user.company_id.get_base_url()
        return f"{base_url}/web/image?model=res.users&id={user.id}&field={user.avatar_1024}"

    def _build_route_data(self, route_data):
        data = {'data': [
            {
                'id': route.id,
                'name': route.name,
                'mon_day': route.mon_day,
                'tue_day': route.tue_day,
                'wed_day': route.wed_day,
                'thu_day': route.thu_day,
                'fri_day': route.fri_day,
                'sat_day': route.sat_day,
                'sale_man_id': {
                    'id': route.user_id.id,
                    'name': route.user_id.name,
                    'phone': route.user_id.partner_id.phone,
                    'leader': {
                        'id': route.team_id.manager_id.id,
                        'name': route.team_id.manager_id.name,
                    }
                },
                'customer': {
                    'id': route.partner_id.id,
                    'name': route.partner_id.name,
                    'address': route.partner_id.customer_address or '',
                    'late': route.partner_id.partner_latitude or 0,
                    'long': route.partner_id.partner_latitude or 0
                },
            } for route in route_data
        ], 'status': 200}
        return data

    def _handle_exception(self, e):
        data = {
            'status': 400,
            'data': {
                'message': _(str(e))
            }
        }
        return request.make_json_response(data, status=400)

    def _validate_missing_key(self, key_list: tuple, value: dict[str:any]):
        for key in key_list:
            if key not in value:
                self._handle_exception(f"{key} is missing")

    def _validate_required_key_value(self, key_list: tuple, value: dict):
        for key in key_list:
            if not value.get(key, False):
                return self._handle_exception(f"{key} is required")

    @validate_token
    @http.route('/ppm_sale/api/distributor_list', methods=["GET"], type='http', auth="none", csrf=False)
    def ppm_distributor_list(self, page=1, **kw):
        try:
            page = int(page)
            distributors = request.env['ppm.distributor'].search([], limit=self._distributor_per_page,
                                                                 offset=(page - 1) * self._distributor_per_page)

            total_distributor = request.env['ppm.distributor'].search_count([])
            total_pages = (total_distributor - 1) // self._distributor_per_page + 1
            data = {
                'status': 200,
                'page': page,
                'total_pages': total_pages,
                'list': [{
                    'id': d.id,
                    'name': d.name or '',
                    'phone': d.phone or '',
                    'email': d.email or '',
                    'address': d.address or ''
                } for d in distributors]
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route("/ppm_sale/api/activity_report", methods=["POST"], type="http", auth="none", csrf=False)
    def ppm_sale_activity_report(self, **kw):
        for key in ('date_to', 'date_from'):
            if key not in kw:
                return self._handle_exception(f"{key} is missing")

        try:
            domain = [('todo_date', '<=', kw['date_to']),
                      ('todo_date', '>=', kw.get('date_from')),
                      ('user_id', '=', request.env.user.id)]
            activities = (request.env['ppm.sale.route.line.activity']
                          .sudo().search(domain, order="activity_type desc"))
            data = {
                'status': 200,
                'list': [self._format_activity_data(activity) for activity in activities]
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route('/ppm_sale/api/sale_order_detail', methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_sale_order_detail(self, **kw):
        if 'order_id' not in kw:
            return self._handle_exception("order_id key is missing")
        if not kw.get('order_id', False):
            return self._handle_exception("Order id is required")
        try:
            sale_order_sudo = request.env['sale.order'].sudo()
            sale_order = sale_order_sudo.search([
                ('id', '=', kw.get('order_id'))
            ], limit=1)
            if not sale_order:
                return self._handle_exception(f"There is not found sale order with id: {kw.get('order_id')}")
            data = {
                "status": 200,
                'data': {
                    'id': sale_order.id,
                    'name': sale_order.name,
                    'partner_id': sale_order.partner_id.id or '',
                    'distributor_id': sale_order.distributor_id.id if sale_order.distributor_id else None,
                    'date_order': sale_order.date_order.strftime(
                        DEFAULT_SERVER_DATE_FORMAT) if sale_order.date_order else '',
                    'delivery_date': sale_order.commitment_date.strftime(
                        DEFAULT_SERVER_DATE_FORMAT) if sale_order.commitment_date else '',
                    'global_discount': sale_order.global_discount,
                    'partner_name': sale_order.partner_id.name or '',
                    'amount': sale_order.tax_totals['amount_total'],
                    'delivery_address_id': sale_order.partner_shipping_id.id or '',
                    'delivery_address': sale_order.partner_id.customer_address or '',
                    'note': html2plaintext(sale_order.note or ""),
                    'order_lines': [{
                        'product_name': line.product_id.name or '',
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'price_unit': line.price_unit,
                        'foc': line.foc or 0.00,
                        'discount': line.discount
                    } for line in sale_order.order_line]
                }
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route("/ppm_sale/api/sale_order_list", methods=['GET'], type="http", auth="none", csrf=False)
    def ppm_sale_order_list(self, page=1, **kw):
        try:
            def get_sale_order_state_value(key: str, field_value: list[tuple]) -> str:
                for item in field_value:
                    if item[0] == key:
                        return item[1]

            try:
                page = int(page)
                if page <= 0:
                    page = 1
            except ValueError:
                page = 1

            sale_order_sudo = request.env['sale.order'].sudo()
            sale_orders = sale_order_sudo.with_context(sale_order_key=True).search(
                [('user_id', '=', request.env.user.id)],
                limit=self._order_per_page,
                offset=(page - 1) * self._order_per_page, order="sale_order_state, date_order DESC")

            state_field = request.env['ir.model.fields'].get_field_selection('sale.order', 'state')
            total_products = sale_order_sudo.search_count([('user_id', '=', request.env.user.id)])
            total_pages = (total_products - 1) // self._order_per_page + 1

            data = {
                "status": 200,
                'page': page,
                'total_pages': total_pages,
                'list': [{
                    'id': sale.id,
                    'name': sale.name,
                    'partner_id': sale.partner_id.id or '',
                    'date_order': sale.date_order.strftime(DEFAULT_SERVER_DATE_FORMAT) if sale.date_order else '',
                    'delivery_date': sale.commitment_date.strftime(
                        DEFAULT_SERVER_DATE_FORMAT) if sale.commitment_date else '',
                    'partner_name': sale.partner_id.name or '',
                    'amount': sale.tax_totals['amount_total'],
                    'status': sale.state,
                    'status_value': get_sale_order_state_value(sale.state, state_field),
                    'delivery_address_id': sale.partner_shipping_id.id or '',
                    'delivery_address': sale.partner_shipping_id.name or ''
                } for sale in sale_orders]
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route("/ppm_sale/api/sale_order/update", methods=['POST'], http="http", auth="none", csrf=False)
    def ppm_update_sale_order(self, **kw):
        order_fields = ('partner_id', 'date_order', 'commitment_date', 'global_discount', 'distributor_id', 'order_id', 'note')
        for key in order_fields:
            if key not in kw:
                return self._handle_exception(f"{key} is missing")

        order_lines_list = json.loads(kw["order_lines"].replace("'", "\""))
        # order_line_fields = ('product_id', 'product_uom_qty', 'product_uom', 'price_unit', 'foc')

        partner = request.env['res.partner'].sudo().search([
            ('id', '=', kw.get('partner_id'))
        ], limit=1)
        if not partner:
            return self._handle_exception(f"Invalid customer id")

        sale_order = request.env['sale.order'].sudo().search([
            ('id', '=', kw.get('order_id'))
        ], limit=1)
        if not sale_order:
            return self._handle_exception("Invalid sale order")

        value = {key: kw.get(key) for key in order_fields}
        del value['order_id']
        value['partner_id'] = int(kw.get('partner_id', 0))
        value['distributor_id'] = int(kw.get('distributor_id', False))
        authorization_header = request.httprequest.headers.get('Authorization')
        user_by_token = self._get_user_by_token(authorization_header)
        request.update_env(user=user_by_token)
        value['company_id'] = user_by_token.company_id.id
        value['note'] = kw.get('note')

        value['pricelist_id'] = partner.property_product_pricelist.id or False
        value['partner_invoice_id'] = partner.address_get(['invoice'])['invoice'] if partner else False
        value['partner_shipping_id'] = partner.address_get(['delivery'])['delivery'] if partner else False

        sale_order.with_user(user_by_token)

        value['payment_term_id'] = user_by_token.partner_id.property_payment_term_id.id or False
        sale_order.sudo().order_line.unlink()
        value['order_line'] = [Command.create(line) for line in order_lines_list]
        with request.env.cr.savepoint():
            sale_order.write(value)
            data = {
                "status": 200,
                'data': {
                    'message': 'Sale Order updated.'
                }
            }
            return request.make_json_response(data)

    @validate_token
    @http.route("/ppm_sale/api/sale_order/new", methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_new_sale_order(self, **kw):
        order_fields = ('partner_id', 'date_order', 'commitment_date', 'global_discount', 'distributor_id')
        for key in order_fields:
            if key not in kw:
                return self._handle_exception(f"{key} is missing")

        customer = request.env['res.partner'].sudo().search([('id', '=', kw.get('partner_id'))], limit=1)
        if not customer:
            return self._handle_exception("Invalid partner_id")

        order_line_fields = ('product_id', 'product_uom', 'price_unit')

        if 'order_lines' not in kw:
            return self._handle_exception("Order line is required.")

        # Convert order_lines string to actual list of dictionaries
        order_lines_list = json.loads(kw["order_lines"].replace("'", "\""))

        if not all(all(item.get(key) for key in order_line_fields) for item in order_lines_list):
            return self._handle_exception("Order line field is missed. Please verify input.")

        value = {key: kw.get(key) for key in order_fields}

        ppm_sale_member = request.env['ppm.sale.member'].search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if ppm_sale_member:
            value['ppm_sale_team_id'] = ppm_sale_member.team_id.id

        value['note'] = kw.get('note', '')
        value['company_id'] = request.env.user.company_id.id
        value['user_id'] = request.env.user.id

        partner = request.env['res.partner'].sudo().search([
            ('id', '=', kw.get('partner_id'))
        ], limit=1)
        if not partner:
            return self._handle_exception(f"There is customer found with this id:{kw.get('partner_id')}")

        value['pricelist_id'] = partner.property_product_pricelist.id or False
        value['distributor_id'] = int(kw.get('distributor_id', False)) if kw.get('distributor_id', False) else False
        value['partner_invoice_id'] = partner.address_get(['invoice'])['invoice'] if partner else False
        value['partner_shipping_id'] = partner.address_get(['delivery'])['delivery'] if partner else False

        sale_order_sudo = request.env['sale.order']

        value['payment_term_id'] = request.env.user.partner_id.property_payment_term_id.id or False
        value['order_line'] = [Command.create(line) for line in order_lines_list]
        with request.env.cr.savepoint():
            sale_order = sale_order_sudo.create(value)
            data = {
                "status": 200,
                'data': {
                    'order_id': sale_order.id,
                    'message': 'Sale Order created.'
                }
            }
            return request.make_json_response(data)

    @validate_token
    @http.route('/ppm_sale/api/user/info', methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_user_info(self):
        authorization_header = request.httprequest.headers.get('Authorization')
        if not authorization_header:
            return self._handle_exception("Authorization header is missing")

        user_by_token = self._get_user_by_token(authorization_header)
        if not user_by_token:
            return self._handle_exception("Invalid token")

        data = {
            "status": 200,
            "data": {
                "image_ur": self._get_user_profile_photo_url(user_by_token),
                "image": user_by_token.avatar_1024 or '',
                "name": user_by_token.name,
            }
        }
        return request.make_json_response(data)

    @validate_token
    @http.route("/ppm_sale/api/user/new-password", methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_user_change_password(self, **kw):
        if 'new_password' not in kw:
            return self._handle_exception("Missing new password")

        if not kw['new_password'].strip():
            return self._handle_exception("New password is required")

        authorization_header = request.httprequest.headers.get('Authorization')
        if not authorization_header:
            return self._handle_exception("Authorization header is missing")

        user_by_token = self._get_user_by_token(authorization_header)
        user_by_token._change_password(kw['new_password'])
        access_token = user_by_token.action_generate_token(user_by_token)
        data = {
            'status': 200,
            'data': {
                'message': 'Password changed',
                'token': f'{access_token}'
            }
        }
        return request.make_json_response(data)

    @validate_token
    @http.route("/ppm_sale/api/customer_type", methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_customer_type(self, **kw):
        customer_types = request.env['res.partner.type'].sudo().search([])
        data = {
            'status': 200,
            'list': [{
                'id': t.id,
                'name': t.name,
                'color_code': t.color_code[1:],
            } for t in customer_types]
        }
        return request.make_json_response(data)

    @validate_token
    @http.route("/ppm_sale/api/customer/new", methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_new_customer(self, **kw):
        customer_fields = ('name', 'customer_type', 'phone', 'email', 'customer_address', 'partner_latitude', 'partner_longitude')
        for key in customer_fields:
            if key not in kw:
                return self._handle_exception(f"{key} is missing")

        value = {key: kw.get(key) for key in (
            'name', 'customer_type', 'phone', 'email', 'customer_address', 'partner_latitude',
            'partner_longitude')}
        value.update({
            'customer_status': 'pending',
            'ppm_sale_man': [Command.link(request.env.user.id)],
            'customer_rank': 1
        })
        try:
            customer = request.env['res.partner'].sudo().create(value)
            data = {
                'status': 200,
                'data': {
                    'id': customer.id,
                    'message': _("Customer created")
                }
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)


    @validate_token
    @http.route("/ppm_sale/api/customer/search", type="http", auth="none", csrf=False)
    def ppm_customer_search(self, page=1, **kw):
        try:
            domain = [('name', 'ilike', kw.get('q'))] if kw.get('q') else []

            domain += [
                ('customer_rank', '>', 0),
                ('type', '=', 'contact'),
                ('ppm_sale_man', 'in', [request.env.user.id])
            ]
            customers = request.env['res.partner'].sudo().search(domain, limit=self._customer_per_page,
                                                                 offset=(page - 1) * self._customer_per_page)

            total_customer = request.env['res.partner'].search_count(domain)
            total_pages = (total_customer - 1) // self._customer_per_page + 1

            data = {
                'status': 200,
                'page': page,
                'total_pages': total_pages,
                'list': [{
                    'id': customer.id,
                    'name': customer.name if customer.name else '',
                    'address': customer.customer_address if customer.customer_address else '',
                    'lat': customer.partner_latitude if customer.partner_latitude else 0,
                    'long': customer.partner_longitude if customer.partner_longitude else 0,
                    'email': customer.email or '',
                    'mobile': customer.mobile or '',
                    'phone': customer.phone or '',
                    'customer_type': customer.customer_type.name or '',
                    'customer_status': customer.customer_status or '',
                    'gps_range': customer.gps_range or 0.0,
                    'salesman_id': customer.user_id.id or '',
                    'salesman_name': customer.user_id.name or ''
                } for customer in customers]
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route('/ppm_sale/api/fetch_customer', methods=['GET'], type="http", auth="none", csrf=False)
    def ppm_fetch_customer(self, page=1, **kw):
        try:
            try:
                page = int(page)
                if page <= 0:
                    page = 1
            except ValueError:
                page = 1

            domain = [
                ('customer_rank', '>', 0),
                ('type', '=', 'contact'),
                ('ppm_sale_man', 'in', [request.env.user.id])
            ]
            customers = request.env['res.partner'].sudo().search(domain, limit=self._customer_per_page,
                                                                 offset=(page - 1) * self._customer_per_page,
                                                                 order="customer_type")

            total_customer = request.env['res.partner'].search_count(domain)
            total_pages = (total_customer - 1) // self._customer_per_page + 1

            data = {
                'status': 200,
                'page': page,
                'total_pages': total_pages,
                'list': [{
                    'id': customer.id,
                    'name': customer.name if customer.name else '',
                    'address': customer.customer_address if customer.customer_address else '',
                    'lat': customer.partner_latitude if customer.partner_latitude else 0,
                    'long': customer.partner_longitude if customer.partner_longitude else 0,
                    'mobile': customer.mobile or '',
                    'email': customer.email or '',
                    'phone': customer.phone or '',
                    'color_code': customer.customer_type and customer.customer_type.color_code[1:] or 'e9ecef',
                    'customer_type': customer.customer_type.name or '',
                    'customer_status': customer.customer_status or '',
                    'gps_range': customer.gps_range or 0.0,
                    'salesman_id': customer.user_id.id or '',
                    'salesman_name': customer.user_id.name or '',
                } for customer in customers]
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route("/ppm_sale/api/product_list", methods=['GET'], type="http", auth="none", csrf=False)
    def ppm_product_list(self, page=1, **kw):
        try:
            try:
                page = int(page)
                if page <= 0:
                    page = 1
            except ValueError:
                page = 1

            domain = [('name', 'ilike', kw.get('q'))] if kw.get('q') else []
            customers = request.env['product.product'].sudo().search(domain, limit=self._product_per_page,
                                                                     offset=(page - 1) * self._product_per_page)

            total_products = request.env['product.product'].search_count(domain)
            total_pages = (total_products - 1) // self._product_per_page + 1

            data = {
                'status': 200,
                'page': page,
                'total_pages': total_pages,
                'list': [{
                    'id': p.id,
                    'name': p.name,
                    'category': p.categ_id.name or '',
                    'code': p.default_code or '',
                    'sale_price': p.list_price or 0.00,
                    'product_uom': p.uom_id.name or '',
                    'product_uom_id': p.uom_id.id or 1,
                } for p in customers]
            }
            return request.make_json_response(data)
        except Exception as e:
            return self._handle_exception(e)

    @validate_token
    @http.route("/ppm_sale/api/detail/activity", methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_detail_activity(self, **kw):
        if 'id' not in kw:
            return self._handle_exception("id is missing ")

        activity = request.env['ppm.sale.route.line.activity'].sudo().search([
            ('id', '=', kw.get('id'))
        ], limit=1)
        if not activity:
            return self._handle_exception("Invalid activity")

        data = {
            'status': 200,
            'data': self._format_check_out_data(activity)
        }
        return request.make_json_response(data)

    @validate_token
    @http.route('/ppm_sale/api/new/activity', methods=['POST'], type="http", auth="none", csrf=False)
    def ppm_new_activity(self, **kw):
        for key in ('partner_id', 'user_id'):
            if key not in kw:
                return self._handle_exception(f"{key} is missing")

        user = request.env['res.users'].sudo().search([
            ('id', '=', kw.get('user_id'))
        ], limit=1)
        if not user:
            return self._handle_exception("Invalid user_id")

        partner = request.env['res.partner'].sudo().search([
            ('id', '=', kw.get('partner_id'))
        ], limit=1)
        if not partner:
            return self._handle_exception("Invalid customer id")

        activity = request.env['ppm.sale.route.line.activity'].sudo().create({
            'user_id': user.id,
            'partner_id': partner.id,
            'todo_date': fields.Date.today(),
            'check_in_date': fields.Datetime.now(),
        })
        data = {
            'status': 200,
            'data': {
                'check_in_id': activity.id,
                'message': _("Activity created")
            }
        }
        return request.make_json_response(data)

    @validate_token
    @http.route('/ppm_sale/api/check_out/activity', methods=['POST'], type="http", auth="none", csrf=False)
    def sale_man_activity_check_out(self, **kw):
        for key in ('photo_lat', 'photo_long', 'remark', 'check_in_id', 'has_order', 'photo'):
            if key not in kw:
                return self._handle_exception(f"{key.capitalize()} is missing")
            if not kw.get(key, False):
                return self._handle_exception(f"{key.capitalize()} is required")

        activity = request.env['ppm.sale.route.line.activity'].sudo().search([
            ('id', '=', kw.get('check_in_id'))
        ], limit=1)
        if not activity:
            return self._handle_exception(
                f"There is not found activity that match to check_in_id:{kw.get('check_in_id')}")

        values = {key: kw.get(key) for key in ('photo_lat', 'photo_long', 'remark')}
        photo_data = kw['photo'].read()
        values['user_id'] = request.env.user.id
        values['check_out_date'] = fields.Datetime.now()
        values['photo'] = base64.b64encode(photo_data).decode()
        values['has_order'] = True if int(kw.get('has_order', 0)) == 1 else False
        activity.sudo().update(values)
        data = {
            'status': 200,
            'data': self._format_check_out_data(activity)
        }
        return request.make_json_response(data)

    @validate_token
    @http.route('/ppm_sale/api/check_in/activity', type="http", auth="none", csrf=False)
    def sale_man_activity_check_in(self, **kw):
        for key in ('check_in_id', 'route_id', 'user_id', 'has_order'):
            if key not in kw:
                return self._handle_exception(f"{key.capitalize()} is missing")
            if not kw.get(key, False):
                return self._handle_exception(f"{key.capitalize()} is required")

        if int(kw['check_in_id']) == 0:
            route_obj = request.env["ppm.sale.route.line"].sudo().search([
                ('id', '=', kw.get('route_id'))
            ])
            if not route_obj:
                return self._handle_exception(f"There is no route line for with id: {kw.get('route_id')}")

            values = {key: kw.get(key) for key in ('partner_id', 'user_id')}
            values['todo_date'] = fields.Date.today(),
            values['check_in_date'] = fields.Datetime.now()
            values['partner_id'] = route_obj.partner_id.id
            values['has_order'] = True if kw.get('has_order', 0) == 1 else False
            check_in_obj = request.env['ppm.sale.route.line.activity'].sudo().create(values)
            data = {
                'status': 200,
                'data': {
                    'message': 'Success Check-In',
                    'check_in_id': check_in_obj.id
                }
            }
            return request.make_json_response(data)

        check_in_obj = request.env['ppm.sale.route.line.activity'].sudo().search([
            ('id', '=', kw.get('check_in_id'))
        ])
        if not check_in_obj:
            return self._handle_exception(f"There is no activity match to this id: {kw.get('check_in_id')}")

        check_in_obj.sudo().update({
            'check_in_date': fields.Datetime.now()
        })
        return request.make_json_response(data={
            'status': 200,
            'data': {
                'message': 'Success Check-In',
                'check_in_id': check_in_obj.id
            }
        })

    @validate_token
    @http.route('/ppm_sale/api/sale_route_list', methods=['POST'], type="http", auth="user", csrf=False)
    def route_by_sale_man(self, **kw):

        if 'user_id' not in kw:
            return self._handle_exception("User id is missing")
        if not kw.get('user_id'):
            return self._handle_exception("User is id required")

        user = request.env['res.users'].sudo().search([('id', '=', kw.get('user_id', 0))], limit=1)
        if not user:
            return self._handle_exception(f"There is no user with id: {kw.get('user_id')}")
        route_data = request.env['ppm.sale.route.line'].sudo().search(
            [('user_id', '=', user.id)])
        data = self._build_route_data(route_data)
        return request.make_json_response(data)

    @validate_token
    @http.route('/ppm_sale/api/sale_activity_today', methods=['POST'], type="http", auth="user", csrf=False)
    def today_sale_activity(self, **kw):
        if 'user_id' not in kw:
            return self._handle_exception("User id is missing")
        if not kw.get('user_id'):
            return self._handle_exception("User is id required")

        user = request.env['res.users'].sudo().search([
            ('id', '=', kw.get('user_id', 0))
        ], limit=1)
        if not user:
            return self._handle_exception(f"There is no user with id: {kw.get('user_id')}")
        today_activities = self._get_today_activities(user.id)
        data = {
            'status': 200,
            'data': [self._format_activity_data(activity) for activity in today_activities]
        }
        return request.make_json_response(data)

    @validate_token
    @http.route('/ppm_sale/api/sale_activity', methods=['POST'], type='http', auth="user", csrf=False)
    def route_by_date(self, **kw):
        for key in ('route_id', 'user_id', 'route_date'):
            if key not in kw:
                return self._handle_exception(f"Param {key} is missing")
            if not kw.get(key, False):
                return self._handle_exception(f"{key.capitalize()} is required")

        route = request.env['ppm.sale.route'].search([
            ('id', '=', int(kw.get('route_id')))
         ], limit=1)
        if not route:
            return self._handle_exception(f"There is no route that match to this route: {kw.get('route_id')}")

        user = request.env['res.users'].search([
            ('id', '=', kw.get('user_id'))
        ], limit=1)
        if not user:
            return self._handle_exception(f"There is no user that match to this id: {kw.get('user_id')}")

        domain = [
            ('route_id', '=', route.id),
            ('user_id', '=', user.id)
        ]
        activities = request.env['ppm.sale.route.line.activity'].sudo().search(domain, order="id desc")
        if not activities:
            return self._handle_exception(f"There is no activity for that match to route_id: {route.id} and user_id: {user.id}")

        route_date = fields.Date.from_string(kw.get('route_date')).strftime(DEFAULT_SERVER_DATE_FORMAT)
        activity = activities.filtered(
            lambda x: x.check_in_date and x.check_in_date.strftime(DEFAULT_SERVER_DATE_FORMAT) == route_date
        )
        if activity:
            data = {
                'status': 200,
                'data': {
                    'status': _(activity.activity_type)
                }
            }
            return request.make_json_response(data)

        data = {
            'data': {}
        }
        return request.make_json_response(data)

    @http.route('/ppm_sale/api/login', methods=['POST'], type='http', auth="none", csrf=False)
    def login(self, **kw):

        for key in ('username', 'password'):
            if key not in kw:
                return self._handle_exception(f"{key} is missing")
        for key in ('username', 'password'):
            if not kw.get(key, False):
                return self._handle_exception(f"{key} is required")

        user = request.env['res.users'].sudo().search([
            ('login', '=', kw.get('username'))
        ], limit=1)

        if not user:
            return self._handle_exception("Invalid Username")
        try:
            # db = 'demo_01'
            # db = 'ppm_uat'
            db = config.get('db_name', '')
            uid = request.session.authenticate(db, request.params['username'], request.params['password'])
            if uid != request.session.uid:
                return self._handle_exception("Invalid login user")
            request.update_env(user=uid)
            user = request.env['res.users'].sudo().browse(uid)
            access_token = user.find_or_create_token(user=user)
            return request.make_json_response({
                "token": access_token,
                "user_id": uid
            })
        except Exception as e:
            _logger.error(e)
            return self._handle_exception("Invalid Password")
