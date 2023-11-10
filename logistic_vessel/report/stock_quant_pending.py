# -*- coding: utf-8 -*-
from odoo import models, fields, tools
from psycopg2 import sql


class StockQuantPending(models.Model):
    _name = 'stock.quant.pending.report'
    _auto = False
    _order = 'warehouse_enter_no'

    supplier_id = fields.Many2one('res.partner', string='Supplier')
    mv = fields.Many2one('freight.vessel', string='M/V')
    owner_ref = fields.Char('Ref#')
    location = fields.Char('Location')
    warehouse_enter_no = fields.Char('Warehouse Enter No')
    quantity = fields.Float('Quantity')
    weight = fields.Float('Weight')
    volume = fields.Float('Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)')
    ready_date = fields.Date('Ready Date')
    arrival_date = fields.Date('Arrival Date')
    invoice = fields.Char('Invoice')
    so = fields.Char('S/O')
    dest = fields.Char('Dest')
    awb = fields.Char('Awb')
    departure_date = fields.Date('Departure Date')
    ref = fields.Char('Ref')

    def init(self):
        query = """
        select
            sq.id as id,
            rp.id as supplier_id,
            so.mv as mv,
            so.gross_weight_pc as weight,
            so.volume as volume,
            so.dimensions as dimensions,
            so.owner_ref as owner_ref,
            rcs.name as location,
            so.warehouse_enter_no as warehouse_enter_no,
            so.ready_date as ready_date,
            sq.quantity as quantity,
            sp.arrival_date as arrival_date,
            so.invoice_no as invoice,
            so.client_order_ref as so,
            sp.dest as dest,
            sp.awb as awb,
            sp.departure_date as departure_date,
            sp.ref as ref
        from
            stock_quant as sq
        left join stock_location sl2 on
            sl2.id = sq.location_id
        left join stock_lot sl on
            sl.id = sq.lot_id
        left join sale_order so on
            so.owner_ref = sl.name
        left join res_partner rp on
            so.partner_id = rp.id
        left join stock_picking sp on
            sp.sale_id = so.id
        left join res_country_state rcs on
            rcs.id = so.location_id
        where
            (so.state = 'sale' or so.state is null)
            and sl2.usage = 'internal'
        """
        tools.drop_view_if_exists(self._cr, self._table)

        self.env.cr.execute(
            sql.SQL("""CREATE or REPLACE VIEW {} as ({})""").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            ))
