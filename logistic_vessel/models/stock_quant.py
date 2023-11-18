# -*- coding: utf-8 -*-
from odoo import models, fields


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    lot_name = fields.Char(related='lot_id.name', store=True, string='Lot name')
