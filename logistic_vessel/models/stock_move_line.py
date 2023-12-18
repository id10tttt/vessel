# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    gross_weight_pc = fields.Float('Gross Weight(KG/pc)')
    length = fields.Float('Length(cm)', digits='Vessel Package Volume Unit')
    width = fields.Float('Width(cm)', digits='Vessel Package Volume Unit')
    height = fields.Float('Height(cm)', digits='Vessel Package Volume Unit')

    volume = fields.Float('Volume(m³)', compute='_compute_volume_and_dimensions', store=True,
                          digits='Vessel Package Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)', compute='_compute_volume_and_dimensions', store=True)

    @api.depends('length', 'width', 'height')
    def _compute_volume_and_dimensions(self):
        for package_id in self:
            package_id.dimensions = '{} x {} x {} cm'.format(
                package_id.length,
                package_id.width,
                package_id.height)
            package_id.volume = (package_id.length * package_id.width * package_id.height) / (100 * 100 * 100)

    @api.onchange('length', 'width', 'height')
    def _onchange_set_default_product_info(self):
        for line_id in self:
            picking_id = self.picking_id
            if not picking_id:
                continue
            move_id = picking_id.move_ids
            if not move_id:
                continue
            line_id.product_id = move_id[0].product_id.id
            line_id.lot_name = move_id[0].lot_name
