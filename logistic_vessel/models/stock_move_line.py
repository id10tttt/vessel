# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    gross_weight_pc = fields.Float('Gross Weight(KG/pc)')
    length = fields.Float('Length(cm)', digits='Vessel Package Volume')
    width = fields.Float('Width(cm)', digits='Vessel Package Volume')
    height = fields.Float('Height(cm)', digits='Vessel Package Volume')

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
