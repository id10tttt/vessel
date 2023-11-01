# -*- coding: utf-8 -*-
from odoo import models, fields


class Vessel(models.Model):
    _name = 'freight.vessel'
    _description = 'Vessel'

    name = fields.Char('名称', required=True)
    code = fields.Char('编码')
    country = fields.Many2one('res.country', string='国家')
    active = fields.Boolean('Active', default=True)
