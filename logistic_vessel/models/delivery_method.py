# -*- coding: utf-8 -*-
from odoo import models, fields


class DeliveryMethod(models.Model):
    _name = 'delivery.method'
    _description = 'Delivery Method'
    _sql_constraints = [
        ('unique_name_code', 'unique(name, code)', 'name and code must unique!')
    ]

    name = fields.Char('名称', required=True)
    code = fields.Char('编码')
