# -*- coding: utf-8 -*-
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        return ['move_lot_id', 'lot_name', 'sale_line_id']
