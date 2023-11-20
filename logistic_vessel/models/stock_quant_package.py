# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Package name must unique!')
    ]

    gross_weight_pc = fields.Float('Gross Weight(KG/pc)')
    length = fields.Float('Length(cm)')
    width = fields.Float('Width(cm)')
    height = fields.Float('Height(cm)')

    volume = fields.Float('Volume(m³)', compute='_compute_volume_and_dimensions', store=True,
                          digits='Vessel Package Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)', compute='_compute_dimensions_value', store=True)

    @api.depends('length', 'width', 'height')
    def _compute_volume_and_dimensions(self):
        for package_id in self:
            package_id.dimensions = '{} x {} x {} cm'.format(
                package_id.length,
                package_id.width,
                package_id.height)
            package_id.volume = package_id.length * package_id.width * package_id.height / 100 * 100 * 100
