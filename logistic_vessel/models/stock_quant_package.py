# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    length = fields.Float('Length(mm)')
    width = fields.Float('Width(mm)')
    height = fields.Float('Height(mm)')

    dimensions = fields.Char('Dimensions(LxMxH cm)', compute='_compute_dimensions_value', store=True)

    @api.depends('length', 'width', 'height')
    def _compute_dimensions_value(self):
        for package_id in self:
            package_id.dimensions = '{} x {} x {} cm'.format(
                package_id.length / 100,
                package_id.width / 100,
                package_id.height / 100)
