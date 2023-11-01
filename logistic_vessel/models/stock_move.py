# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        warehouse_enter_no = self.group_id.sale_id.warehouse_enter_no
        vals['warehouse_enter_no'] = warehouse_enter_no
        return vals
