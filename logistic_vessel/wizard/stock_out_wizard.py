# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError


class SaleQuantOut(models.TransientModel):
    _name = 'stock.quant.stock.out.wizard'
    _description = '出库'

    mv = fields.Many2one('freight.vessel', string='M/V', required=True)
    owner_ref = fields.Char('Owner Ref')
    dest = fields.Char('Dest')
    awb = fields.Char('Awb')
    departure_date = fields.Date('Departure Date')
    ref = fields.Char('Ref')
    line_ids = fields.One2many('stock.quant.stock.out.line', 'wizard_id', string='Line')

    def get_sale_order_data(self):
        data = {
            'mv': self.mv.id,
            'owner_ref': self.owner_ref,
            'order_type': 'stock_out',
            'departure_date': self.departure_date,
            'dest': self.dest,
            'ref': self.ref,
            'awb': self.awb,
            'partner_id': self.env.user.id,
        }
        return data

    def get_sale_order_line_data(self):
        default_product_id = self.env['product.product'].sudo().search([
            ('default_code', '=', '000000')
        ])
        if not default_product_id or len(default_product_id) != 1:
            raise UserError('数据异常! 没有找到对应的产品')
        data = []
        for line_id in self.line_ids:
            data.append((0, 0, {
                'product_id': default_product_id.id,
                'product_uom_qty': line_id.qty,
                'gross_weight_pc': line_id.package_id.gross_weight_pc,
                'length': line_id.package_id.length,
                'width': line_id.package_id.width,
                'height': line_id.package_id.height,
                'product_lot_id': line_id.lot_id.id,
                'package_id': line_id.package_id.id,
                'assign_package': True,
                'assign_lot': True,
            }))
        return data

    def create_stock_out_order(self):
        order_data = self.get_sale_order_data()
        order_line_data = self.get_sale_order_line_data()
        if order_line_data:
            order_data.update({
                'order_line': order_line_data
            })
            order_id = self.env['sale.order'].create(order_data)
            action = {
                'name': order_id.name,
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'context': {
                    'default_order_type': 'stock_out'
                },
                'views': [(False, 'form')],
                'view_mode': 'form',
                'target': 'current',
                'res_id': order_id.id,
            }
            return action


class SaleQuantOutLine(models.TransientModel):
    _name = 'stock.quant.stock.out.line'
    _description = '出库明细'

    wizard_id = fields.Many2one('stock.quant.stock.out.wizard', string='Out Wizard')
    package_id = fields.Many2one('stock.quant.package', string='Package')
    lot_id = fields.Many2one('stock.lot', string='Lots')
    qty = fields.Float('Qty')
    weight = fields.Float('Weight')
    volume = fields.Float('Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)')
