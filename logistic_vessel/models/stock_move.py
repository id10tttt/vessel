# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    lot_name = fields.Char('批次号')
    move_lot_id = fields.Many2one('stock.lot', string=u'需求批次')

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        default_vals = dict(
            lot_id=self.sale_line_id.product_lot_id.id,
            lot_name=self.sale_line_id.order_id.owner_ref
        )
        vals = super(StockMove, self)._prepare_move_line_vals(quantity, reserved_quant)
        default_vals.update(vals)
        return default_vals

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        warehouse_enter_no = self.group_id.sale_id.warehouse_enter_no
        vals['warehouse_enter_no'] = warehouse_enter_no
        return vals

    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None,
                                strict=False, allow_negative=False):
        if not lot_id:
            lot_id = self.move_lot_id or self.sale_line_id.product_lot_id
        return super()._get_available_quantity(product_id=product_id, location_id=location_id, lot_id=lot_id,
                                               package_id=package_id, owner_id=owner_id, strict=strict,
                                               allow_negative=allow_negative)

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
                                  owner_id=None, strict=True):
        self.ensure_one()
        if not lot_id:
            lot_id = self.move_lot_id or self.sale_line_id.product_lot_id
        return super(StockMove, self)._update_reserved_quantity(
            need, available_quantity, location_id, lot_id=lot_id,
            package_id=package_id, owner_id=owner_id, strict=strict)
