# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
from psycopg2 import sql
from odoo.exceptions import UserError


class StockQuantPending(models.Model):
    _name = 'stock.quant.pending.report'
    _auto = False
    _order = 'id desc, warehouse_enter_no'

    stock_in_order = fields.Many2one('sale.order', string='Stock IN')
    stock_out_order = fields.Many2one('sale.order', string='Stock OUT', compute='_compute_stock_out_order_info')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    mv = fields.Many2one('freight.vessel', string='M/V')
    lot_id = fields.Many2one('stock.lot', string='Lot')
    package_id = fields.Many2one('stock.quant.package', string='Package')
    owner_ref = fields.Char('Ref#')
    location = fields.Char('Location')
    warehouse_enter_no = fields.Char('Warehouse Enter No')
    quantity = fields.Float('Quantity')
    reserved_quantity = fields.Float('Reserved Quantity')
    weight = fields.Float('Weight')
    volume = fields.Float('Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)')
    ready_date = fields.Date('Ready Date')
    arrival_date = fields.Date('Arrival Date')
    invoice = fields.Char('Invoice')
    so = fields.Char('S/O')
    dest = fields.Char('Dest', compute='_compute_stock_out_order_info')
    awb = fields.Char('Awb', compute='_compute_stock_out_order_info')
    departure_date = fields.Date('Departure Date', compute='_compute_stock_out_order_info')
    ref = fields.Char('Ref', compute='_compute_stock_out_order_info')

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
        with pure_stock_in as (with stock_in as (select sq.id                 as id,
                                                        so.id                 as stock_in_order,
                                                        sq.lot_id             as lot_id,
                                                        sq.package_id         as package_id,
                                                        rp.id                 as supplier_id,
                                                        so.mv                 as mv,
                                                        sqp.gross_weight_pc   as weight,
                                                        sqp.volume            as volume,
                                                        sqp.dimensions        as dimensions,
                                                        so.owner_ref          as owner_ref,
                                                        rcs.name              as location,
                                                        so.warehouse_enter_no as warehouse_enter_no,
                                                        so.date_order         as ready_date,
                                                        sq.quantity           as quantity,
                                                        sq.reserved_quantity  as reserved_quantity,
                                                        so.invoice_no         as invoice,
                                                        so.client_order_ref   as so,
                                                        ''                    as dest,
                                                        ''                    as awb,
                                                        ''                    as departure_date,
                                                        ''                    as ref,
                                                        so.arrival_date       as arrival_date
                                                 from stock_quant as sq
                                                          left join stock_location sl2 on
                                                     sq.location_id = sl2.id
                                                          left join stock_quant_package sqp on
                                                     sq.package_id = sqp.id
                                                          left join stock_lot sl on
                                                     sq.lot_id = sl.id
                                                          left join sale_order so on
                                                     sl.name = so.owner_ref
                                                          left join res_partner rp on
                                                     rp.id = so.partner_id
                                                          left join res_country_state rcs on
                                                     rcs.id = so.location_id
                                                 where (so.state = 'sale'
                                                     or so.state is null)
                                                   and sq.package_id is not null
                                                   and so.order_type = 'stock_in'
                                                   and sl2.usage = 'internal'
                                                 union
                                                 select sq.id                 as id,
                                                        so.id                 as stock_in_order,
                                                        sq.lot_id             as lot_id,
                                                        sq.package_id         as package_id,
                                                        rp.id                 as supplier_id,
                                                        so.mv                 as mv,
                                                        sqp.gross_weight_pc   as weight,
                                                        sqp.volume            as volume,
                                                        sqp.dimensions        as dimensions,
                                                        so.owner_ref          as owner_ref,
                                                        rcs.name              as location,
                                                        so.warehouse_enter_no as warehouse_enter_no,
                                                        so.date_order         as ready_date,
                                                        sq.quantity           as quantity,
                                                        sq.reserved_quantity  as reserved_quantity,
                                                        so.invoice_no         as invoice,
                                                        so.client_order_ref   as so,
                                                        ''                    as dest,
                                                        ''                    as awb,
                                                        ''                    as departure_date,
                                                        ''                    as ref,
                                                        so.arrival_date       as arrival_date
                                                 from stock_quant as sq
                                                          left join stock_location sl2 on
                                                     sq.location_id = sl2.id
                                                          left join stock_quant_package sqp on
                                                     sq.package_id = sqp.id
                                                          left join stock_lot sl on
                                                     sq.lot_id = sl.id
                                                          left join sale_order so on
                                                     sl.name = so.owner_ref
                                                          left join res_partner rp on
                                                     rp.id = so.partner_id
                                                          left join res_country_state rcs on
                                                     rcs.id = so.location_id
                                                 where (so.state = 'sale'
                                                     or so.state is null)
                                                   and sq.package_id is null
                                                   and so.order_type = 'stock_in'
                                                   and sl2.usage = 'internal')
                               select si.id                 as id,
                                      si.stock_in_order     as stock_in_order,
                                      cast(null as bigint)  as stock_out_order,
                                      si.lot_id             as lot_id,
                                      si.package_id         as package_id,
                                      si.supplier_id        as supplier_id,
                                      si.mv                 as mv,
                                      si.weight             as weight,
                                      si.volume             as volume,
                                      si.dimensions         as dimensions,
                                      si.owner_ref          as owner_ref,
                                      si.location           as location,
                                      si.warehouse_enter_no as warehouse_enter_no,
                                      si.ready_date         as ready_date,
                                      si.quantity           as quantity,
                                      si.reserved_quantity  as reserved_quantity,
                                      si.invoice            as invoice,
                                      si.so                 as so,
                                      ''                    as dest,
                                      ''                    as awb,
                                      ''                    as departure_date,
                                      ''                    as ref,
                                      si.arrival_date       as arrival_date
                               from stock_in si)
        select pure_stock_in.id                 as id,
               pure_stock_in.stock_in_order     as stock_in_order,
               pure_stock_in.lot_id             as lot_id,
               pure_stock_in.package_id         as package_id,
               pure_stock_in.supplier_id        as supplier_id,
               pure_stock_in.mv                 as mv,
               pure_stock_in.weight             as weight,
               pure_stock_in.volume             as volume,
               pure_stock_in.dimensions         as dimensions,
               pure_stock_in.owner_ref          as owner_ref,
               pure_stock_in.location           as location,
               pure_stock_in.warehouse_enter_no as warehouse_enter_no,
               pure_stock_in.ready_date         as ready_date,
               pure_stock_in.quantity           as quantity,
               pure_stock_in.reserved_quantity  as reserved_quantity,
               pure_stock_in.invoice            as invoice,
               pure_stock_in.so                 as so,
               pure_stock_in.arrival_date       as arrival_date
        from pure_stock_in
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
        # if len(set(self.mapped('owner_ref'))) != 1:
        #     raise UserError('不允许选择多个Owner Ref#')
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
