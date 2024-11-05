# -*- coding: utf-8 -*-
import logging
from calendar import timegm
from datetime import datetime, timedelta

import jwt
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = "res.users"

    ppm_sale_access_token = fields.Char(readonly=True, copy=False)
    ppm_token_expire_date = fields.Datetime(readonly=True)


    def has_expired(self, access_token):
        """
        Checks if the given access token has expired.

        Args:
            access_token (str): The access token to check.

        Returns:
            bool: True if the token is expired, False otherwise.
        """

        try:
            payload = jwt.decode(access_token, self.env['ir.config_parameter'].sudo().get_param('database.secret'), algorithms=['HS256'])
            return datetime.now() > datetime.fromtimestamp(payload['exp'])
        except jwt.ExpiredSignatureError:
            return True
        except Exception as e:
            _logger.info(str(e))
            return False

    def action_generate_token(self, user=None):
        if not user:
            user = self.env.user

        token_expiry_date = datetime.now() + timedelta(days=365)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        payload = {
            "sub": user.id,
            "exp": token_expiry_date.timestamp(),
            "iat": datetime.utcnow().timestamp()
        }

        try:
            access_token = jwt.encode(payload, secret, algorithm='HS256')
            user.sudo().write({'ppm_sale_access_token': access_token})
            return access_token
        except Exception as e:
            _logger.info(str(e))
            return None

    def find_or_create_token(self, user=None):
        """
        Finds or creates a PPM sale access token for the given user.

        Args:
            user (odoo.models.BaseModel): The user for whom to generate the token.
                If not provided, defaults to the current user.

        Returns:
            str: The PPM sale access token, or None if an error occurs.
        """

        if not user:
            user = self.env.user

        # Check if a valid token already exists for the user
        existing_token = user.ppm_sale_access_token
        if existing_token and not user.has_expired(existing_token):
            return existing_token

        # Generate a new token if necessary

        self.action_generate_token(user)

    def _ppm_sale_decode_token(self, payload):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        encoded_jwt = jwt.decode(payload, secret, algorithm="HS256")
        return encoded_jwt
