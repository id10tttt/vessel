# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
from psycopg2 import sql
from odoo.exceptions import UserError


class StockQuantPending(models.Model):
    _name = 'stock.quant.pending.report'
    _auto = False
    _order = 'id desc'

    stock_in_order = fields.Many2one('sale.order', string='Stock IN', compute='_compute_stock_in_order_info')
    stock_out_order = fields.Many2one('sale.order', string='Stock OUT', compute='_compute_stock_out_order_info')
    supplier_id = fields.Many2one('res.partner', string='Supplier', compute='_compute_stock_in_order_info')
    mv = fields.Many2one('freight.vessel', string='M/V', compute='_compute_stock_in_order_info')
    lot_id = fields.Many2one('stock.lot', string='Lot')
    package_id = fields.Many2one('stock.quant.package', string='Package')
    owner_ref = fields.Char('Owner Ref', related='lot_id.name')
    location = fields.Char('Location', compute='_compute_stock_in_order_info')
    warehouse_enter_no = fields.Char('Warehouse Enter No', compute='_compute_stock_in_order_info')
    quantity = fields.Float('Quantity', digits='Stock Quant Decimal')
    reserved_quantity = fields.Float('Reserved Quantity', digits='Stock Quant Decimal')
    weight = fields.Float('Weight', related='package_id.gross_weight_pc')
    volume = fields.Float('Volume', related='package_id.volume', digits='Vessel Quant Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)', related='package_id.dimensions')
    ready_date = fields.Date('Ready Date', compute='_compute_stock_in_order_info')
    arrival_date = fields.Date('Arrival Date', compute='_compute_stock_in_order_info')
    pick_up_charge = fields.Float('Pick Up Charge', compute='_compute_stock_in_order_info', digits='Pick Up Charge')
    invoice = fields.Char('Invoice', compute='_compute_stock_in_order_info')
    packing = fields.Char('Packing List', compute='_compute_stock_in_order_info')
    your_ref = fields.Char('Your Ref', compute='_compute_stock_in_order_info')
    dest = fields.Char('Dest', compute='_compute_stock_out_order_info')
    awb = fields.Char('Awb', compute='_compute_stock_out_order_info')
    departure_date = fields.Date('Departure Date', compute='_compute_stock_out_order_info')
    ref = fields.Char('Ref', compute='_compute_stock_out_order_info')

    @api.depends('owner_ref', 'lot_id', 'package_id')
    def _compute_stock_in_order_info(self):
        sale_order_ids = self.env['sale.order'].sudo().search([
            ('order_type', '=', 'stock_in'),
            ('owner_ref', 'in', self.lot_id.mapped('name')),
            ('state', '!=', 'cancel')
        ])
        for quant_id in self:
            order_id = sale_order_ids.filtered(lambda so: so.owner_ref == quant_id.lot_id.name)
            if order_id:
                picking_ids = order_id.picking_ids
                valid_picking_id = picking_ids.filtered(lambda p: p.state == 'done')
                quant_id.stock_in_order = order_id[0].id
                quant_id.supplier_id = order_id[0].partner_id.id
                quant_id.mv = order_id[0].mv.id
                quant_id.location = order_id[0].location_id.name
                quant_id.warehouse_enter_no = order_id[0].warehouse_enter_no
                quant_id.ready_date = order_id[0].date_order
                quant_id.arrival_date = valid_picking_id[0].date_done if valid_picking_id else None
                quant_id.invoice = order_id[0].invoice_file_url
                quant_id.packing = order_id[0].packing_file_url
                quant_id.your_ref = order_id[0].client_order_ref
                quant_id.pick_up_charge = valid_picking_id[0].pick_up_charge if valid_picking_id else 0
            else:
                quant_id.stock_in_order = None
                quant_id.supplier_id = None
                quant_id.mv = None
                quant_id.location = None
                quant_id.warehouse_enter_no = None
                quant_id.ready_date = None
                quant_id.arrival_date = None
                quant_id.invoice = None
                quant_id.packing = None
                quant_id.your_ref = None
                quant_id.pick_up_charge = 0

    @api.depends('owner_ref', 'lot_id', 'package_id')
    def _compute_stock_out_order_info(self):
        sale_order_ids = self.env['sale.order.line'].sudo().search([
            ('order_id.order_type', '=', 'stock_out'),
            ('product_lot_id', 'in', self.lot_id.ids),
            ('package_id', 'in', self.package_id.ids),
            ('order_id.state', '!=', 'cancel')
        ])
        if not sale_order_ids:
            sale_order_ids = self.env['sale.order.line'].sudo().search([
                ('order_id.order_type', '=', 'stock_out'),
                ('order_id.owner_ref', 'in', self.mapped('owner_ref')),
                ('order_id.state', '!=', 'cancel')
            ])
        for quant_id in self:
            order_line_id = sale_order_ids.filtered(
                lambda sol: sol.product_lot_id == quant_id.lot_id and sol.package_id == quant_id.package_id)
            order_id = order_line_id[0].order_id if order_line_id else False
            if order_id:
                quant_id.stock_out_order = order_id.id
                quant_id.dest = order_id.dest
                quant_id.awb = order_id.awb
                quant_id.departure_date = order_id.departure_date
                quant_id.ref = order_id.ref
            else:
                quant_id.stock_out_order = False
                quant_id.dest = False
                quant_id.awb = False
                quant_id.departure_date = False
                quant_id.ref = False

    def get_query(self):
        query = """
        select sq.id                as id,
               sq.lot_id            as lot_id,
               sq.package_id        as package_id,
               sq.quantity          as quantity,
               sq.reserved_quantity as reserved_quantity
        from stock_quant as sq
                 join stock_location sl on sq.location_id = sl.id
        where sl.usage = 'internal'
        """
        return query

    def init(self):
        query = self.get_query()
        tools.drop_view_if_exists(self._cr, self._table)

        self.env.cr.execute(
            sql.SQL("""CREATE or REPLACE VIEW {} as ({})""").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            ))

    def stock_quant_stock_out(self):
        mv_ids = self.mv
        if len(set(mv_ids)) != 1:
            raise UserError('不允许选择多个M/V')
        out_data = {
            'mv': mv_ids[0].id,
            'owner_ref': ','.join(x.owner_ref for x in self)
        }
        line_data = []
        for quant_id in self:
            line_data.append((0, 0, {
                'supplier_id': quant_id.supplier_id.id or False,
                'package_id': quant_id.package_id.id or False,
                'lot_id': quant_id.lot_id.id or False,
                'qty': quant_id.quantity,
                'weight': quant_id.weight,
                'volume': quant_id.volume,
                'dimensions': quant_id.dimensions,
            }))
        if line_data:
            out_data.update({
                'line_ids': line_data
            })
        wiz = self.env['stock.quant.stock.out.wizard'].create(out_data)

        action = {
            'name': u'出库',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.stock.out.wizard',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'res_id': wiz.id,
        }
        return action
