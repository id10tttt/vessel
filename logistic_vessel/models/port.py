# -*- coding: utf-8 -*-
from odoo import models, fields


class Port(models.Model):
    _name = 'freight.port'
    _description = 'Port'

    name = fields.Char('名称', required=True)
    code = fields.Char('编码')
    country = fields.Many2one('res.country', string='国家')
    active = fields.Boolean('Active', default=True)

    air = fields.Boolean('Air')
    ocean = fields.Boolean('Ocean')
    land = fields.Boolean('Land')
