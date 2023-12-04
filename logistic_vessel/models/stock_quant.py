# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    lot_name = fields.Char(related='lot_id.name', store=True, string='Lot name')

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = [('product_id', '=', product_id.id)]
        if not strict:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            if package_id:
                domain = expression.AND([['|', ('package_id', '=', package_id.id), ('package_id', '=', False)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND(
                [['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)] if lot_id else [('lot_id', '=', False)],
                 domain])
            domain = expression.AND(
                [['|', ('package_id', '=', package_id and package_id.id or False), ('package_id', '=', False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])
        if self.env.context.get('with_expiration'):
            domain = expression.AND(
                [['|', ('expiration_date', '>=', self.env.context['with_expiration']), ('expiration_date', '=', False)],
                 domain])
        return domain
