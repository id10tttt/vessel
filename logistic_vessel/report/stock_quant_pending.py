# -*- coding: utf-8 -*-
from odoo import models, fields, tools
from psycopg2 import sql
from odoo.exceptions import UserError


class StockQuantPending(models.Model):
    _name = 'stock.quant.pending.report'
    _auto = False
    _order = 'warehouse_enter_no'

    stock_in_order = fields.Many2one('sale.order', string='Stock IN')
    stock_out_order = fields.Many2one('sale.order', string='Stock OUT')
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
    dest = fields.Char('Dest')
    awb = fields.Char('Awb')
    departure_date = fields.Date('Departure Date')
    ref = fields.Char('Ref')

    def get_query(self):
        query = """
        with pure_stock_in as (
            with stock_in as (
            select
                sq.id as id,
                so.id as stock_in_order,
                sq.lot_id as lot_id,
                sq.package_id as package_id,
                rp.id as supplier_id,
                so.mv as mv,
                sqp.gross_weight_pc as weight,
                sqp.volume as volume,
                sqp.dimensions as dimensions,
                so.owner_ref as owner_ref,
                rcs.name as location,
                so.warehouse_enter_no as warehouse_enter_no,
                so.date_order as ready_date,
                sq.quantity as quantity,
                sq.reserved_quantity as reserved_quantity,
                so.invoice_no as invoice,
                so.client_order_ref as so,
                '' as dest,
                '' as awb,
                '' as departure_date,
                '' as ref,
                so.arrival_date as arrival_date
            from
                stock_quant as sq
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
            where
                (so.state = 'sale'
                    or so.state is null)
                and sq.package_id is not null
                and so.order_type = 'stock_in'
                and sl2.usage = 'internal'
            union
            select
                sq.id as id,
                so.id as stock_in_order,
                sq.lot_id as lot_id,
                sq.package_id as package_id,
                rp.id as supplier_id,
                so.mv as mv,
                sqp.gross_weight_pc as weight,
                sqp.volume as volume,
                sqp.dimensions as dimensions,
                so.owner_ref as owner_ref,
                rcs.name as location,
                so.warehouse_enter_no as warehouse_enter_no,
                so.date_order as ready_date,
                sq.quantity as quantity,
                sq.reserved_quantity as reserved_quantity,
                so.invoice_no as invoice,
                so.client_order_ref as so,
                '' as dest,
                '' as awb,
                '' as departure_date,
                '' as ref,
                so.arrival_date as arrival_date
            from
                stock_quant as sq
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
            where
                (so.state = 'sale'
                    or so.state is null)
                and sq.package_id is null
                and so.order_type = 'stock_in'
                and sl2.usage = 'internal'
            )
            select
                si.id as id,
                si.stock_in_order as stock_in_order,
                cast(null as bigint) as stock_out_order,
                si.lot_id as lot_id,
                si.package_id as package_id,
                si.supplier_id as supplier_id,
                si.mv as mv,
                si.weight as weight,
                si.volume as volume,
                si.dimensions as dimensions,
                si.owner_ref as owner_ref,
                si.location as location,
                si.warehouse_enter_no as warehouse_enter_no,
                si.ready_date as ready_date,
                si.quantity as quantity,
                si.reserved_quantity as reserved_quantity,
                si.invoice as invoice,
                si.so as so,
                '' as dest,
                '' as awb,
                '' as departure_date,
                '' as ref,
                si.arrival_date as arrival_date
            from
                stock_in as si
            where
                si.owner_ref not in (
            with res as (
                select
                    so.id as stock_in_order,
                    sq.lot_name
                from
                    stock_quant sq
                left join sale_order so on
                    sq.lot_name = so.owner_ref
                left join stock_location sl on
                    sq.location_id = sl.id
                where
                    so.order_type = 'stock_in'
                    and sl.usage = 'internal'
                    and (so.state is null
                        or so.state = 'sale')
            )
                select
                    res.lot_name
                from
                    res
                join sale_order so on
                    res.lot_name = so.owner_ref
                where
                    (so.state is null
                        or so.state = 'sale')
                    and so.order_type = 'stock_out'
            )
            ),
            stock_in_out as (
            with stock_out as (
            select
                sq.id as id,
                so.id as stock_in_order,
                sq.lot_id as lot_id,
                sq.package_id as package_id,
                rp.id as supplier_id,
                so.mv as mv,
                sqp.gross_weight_pc as weight,
                sqp.volume as volume,
                sqp.dimensions as dimensions,
                so.owner_ref as owner_ref,
                rcs.name as location,
                so.warehouse_enter_no as warehouse_enter_no,
                so.date_order as ready_date,
                sq.quantity as quantity,
                sq.reserved_quantity as reserved_quantity,
                so.invoice_no as invoice,
                so.client_order_ref as so,
                '' as dest,
                '' as awb,
                '' as departure_date,
                '' as ref,
                so.arrival_date as arrival_date
            from
                stock_quant as sq
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
            where
                (so.state = 'sale'
                    or so.state is null)
                and sq.package_id is not null
                and so.order_type = 'stock_in'
                and sl2.usage = 'internal'
            union
            select
                sq.id as id,
                so.id as stock_in_order,
                sq.lot_id as lot_id,
                sq.package_id as package_id,
                rp.id as supplier_id,
                so.mv as mv,
                sqp.gross_weight_pc as weight,
                sqp.volume as volume,
                sqp.dimensions as dimensions,
                so.owner_ref as owner_ref,
                rcs.name as location,
                so.warehouse_enter_no as warehouse_enter_no,
                so.date_order as ready_date,
                sq.quantity as quantity,
                sq.reserved_quantity as reserved_quantity,
                so.invoice_no as invoice,
                so.client_order_ref as so,
                '' as dest,
                '' as awb,
                '' as departure_date,
                '' as ref,
                so.arrival_date as arrival_date
            from
                stock_quant as sq
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
            where
                (so.state = 'sale'
                    or so.state is null)
                and sq.package_id is null
                and so.order_type = 'stock_in'
                and sl2.usage = 'internal'
                )
            select
                stock_out.id as id,
                stock_out.stock_in_order as stock_in_order,
                so.id as stock_out_order,
                stock_out.lot_id as lot_id,
                stock_out.package_id as package_id,
                stock_out.supplier_id as supplier_id,
                stock_out.mv as mv,
                stock_out.weight as weight,
                stock_out.volume as volume,
                stock_out.dimensions as dimensions,
                stock_out.owner_ref as owner_ref,
                stock_out.location as location,
                stock_out.warehouse_enter_no as warehouse_enter_no,
                stock_out.ready_date as ready_date,
                stock_out.quantity as quantity,
                stock_out.reserved_quantity as reserved_quantity,
                stock_out.invoice as invoice,
                stock_out.so as so,
                so.dest as dest,
                so.awb as awb,
                so.departure_date as departure_date,
                so.ref as ref,
                stock_out.arrival_date as arrival_date
            from
                stock_out
            left join sale_order so
            on
                stock_out.owner_ref = so.owner_ref
            where
                so.order_type = 'stock_out'
                and (so.state is null
                    or so.state = 'sale')
                and 
                stock_out.owner_ref in (
            with res as (
                select
                    so.id as stock_in_order,
                    sq.lot_name
                from
                    stock_quant sq
                left join sale_order so on
                    sq.lot_name = so.owner_ref
                left join stock_location sl on
                    sq.location_id = sl.id
                where
                    so.order_type = 'stock_in'
                    and sl.usage = 'internal'
                    and (so.state is null
                        or so.state = 'sale')
            )
                select
                    res.lot_name
                from
                    res
                join sale_order so on
                    res.lot_name = so.owner_ref
                where
                    (so.state is null
                        or so.state = 'sale')
                    and so.order_type = 'stock_out'
            )
            )
            select
                pure_stock_in.id as id,
                pure_stock_in.stock_in_order as stock_in_order,
                pure_stock_in.stock_out_order as stock_out_order,
                pure_stock_in.lot_id as lot_id,
                pure_stock_in.package_id as package_id,
                pure_stock_in.supplier_id as supplier_id,
                pure_stock_in.mv as mv,
                pure_stock_in.weight as weight,
                pure_stock_in.volume as volume,
                pure_stock_in.dimensions as dimensions,
                pure_stock_in.owner_ref as owner_ref,
                pure_stock_in.location as location,
                pure_stock_in.warehouse_enter_no as warehouse_enter_no,
                pure_stock_in.ready_date as ready_date,
                pure_stock_in.quantity as quantity,
                pure_stock_in.reserved_quantity as reserved_quantity,
                pure_stock_in.invoice as invoice,
                pure_stock_in.so as so,
                pure_stock_in.dest as dest,
                pure_stock_in.awb as awb,
                pure_stock_in.departure_date as departure_date,
                pure_stock_in.ref as ref,
                pure_stock_in.arrival_date as arrival_date
            from
                pure_stock_in
            union all
            select
                stock_in_out.id as id,
                stock_in_out.stock_in_order as stock_in_order,
                stock_in_out.stock_out_order as stock_out_order,
                stock_in_out.lot_id as lot_id,
                stock_in_out.package_id as package_id,
                stock_in_out.supplier_id as supplier_id,
                stock_in_out.mv as mv,
                stock_in_out.weight as weight,
                stock_in_out.volume as volume,
                stock_in_out.dimensions as dimensions,
                stock_in_out.owner_ref as owner_ref,
                stock_in_out.location as location,
                stock_in_out.warehouse_enter_no as warehouse_enter_no,
                stock_in_out.ready_date as ready_date,
                stock_in_out.quantity as quantity,
                stock_in_out.reserved_quantity as reserved_quantity,
                stock_in_out.invoice as invoice,
                stock_in_out.so as so,
                stock_in_out.dest as dest,
                stock_in_out.awb as awb,
                stock_in_out.departure_date::varchar as departure_date,
                stock_in_out.ref as ref,
                stock_in_out.arrival_date as arrival_date
            from
                stock_in_out
        """
        return query

    def init(self):
        query = """
        select
            sq.id as id,
            sq.lot_id as lot_id,
            sq.package_id as package_id,
            rp.id as supplier_id,
            so.mv as mv,
            sqp.gross_weight_pc as weight,
            sqp.volume as volume,
            sqp.dimensions as dimensions,
            so.owner_ref as owner_ref,
            rcs.name as location,
            so.warehouse_enter_no as warehouse_enter_no,
            so.ready_date as ready_date,
            sq.quantity as quantity,
            sq.reserved_quantity as reserved_quantity,
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
            sq.location_id = sl2.id
        left join stock_quant_package sqp on
            sq.package_id = sqp.id
        left join stock_lot sl on
            sq.lot_id = sl.id
        left join sale_order so on
             sl.name = so.owner_ref
        left join res_partner rp on
            rp.id = so.partner_id
        left join stock_picking sp on
            so.id = sp.sale_id
        left join res_country_state rcs on
            rcs.id = so.location_id
        where
            (so.state = 'sale'
                or so.state is null)
            and sq.package_id is not null
            and sl2.usage = 'internal'
        union
        select
            sq.id as id,
            sq.lot_id as lot_id,
            sq.package_id as package_id,
            rp.id as supplier_id,
            so.mv as mv,
            sqp.gross_weight_pc as weight,
            sqp.volume as volume,
            sqp.dimensions as dimensions,
            so.owner_ref as owner_ref,
            rcs.name as location,
            so.warehouse_enter_no as warehouse_enter_no,
            so.ready_date as ready_date,
            sq.quantity as quantity,
            sq.reserved_quantity as reserved_quantity,
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
            sq.location_id = sl2.id
        left join stock_quant_package sqp on
            sq.package_id = sqp.id
        left join stock_lot sl on
            sq.lot_id = sl.id
        left join sale_order so on
             sl.name = so.owner_ref
        left join res_partner rp on
            rp.id = so.partner_id
        left join stock_picking sp on
            so.id = sp.sale_id
        left join res_country_state rcs on
            rcs.id = so.location_id
        where
            (so.state = 'sale'
                or so.state is null)
            and sq.package_id is null
            and sl2.usage = 'internal'
        """
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
