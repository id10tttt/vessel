# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
from io import BytesIO
import hashlib
import base64
from odoo.tools import float_compare
from tempfile import NamedTemporaryFile
from odoo.modules.module import get_module_resource

READONLY_FIELD_STATES = {
    state: [('readonly', True)]
    for state in {'sale', 'done', 'cancel'}
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection([
        ('stock_in', u'入库订单'),
        ('stock_out', u'出库订单'),
    ], string='订单类型', default='stock_out')

    mv = fields.Many2one('freight.vessel', string='M/V', tracking=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Supplier",
        required=True, readonly=False, change_default=True, index=True,
        tracking=1,
        states=READONLY_FIELD_STATES,
        domain="[('type', '!=', 'private'), ('company_id', 'in', (False, company_id))]")
    owner_id = fields.Many2one('res.partner', string='Owner', tracking=True)
    email = fields.Char('E-mail', tracking=True)
    invoice_no = fields.Char('Invoice No', tracking=True)
    owner_ref = fields.Char('Owner Ref', tracking=True)
    ready_date = fields.Date('Ready Date', tracking=True)
    delivery_date = fields.Date('Delivery Date', tracking=True)
    invoice_date = fields.Date('Invoice Date', tracking=True)
    location_id = fields.Many2one('res.country.state', string='State', tracking=True)
    package_list = fields.One2many('vessel.package.list', 'order_id', string='Package List')
    warehouse_enter_no = fields.Char('Warehouse Enter No', compute='_compute_warehouse_no', store=True)

    gross_weight_pc = fields.Float('Gross Weight(KG/pc)', tracking=True)
    gross_weight_kgs = fields.Float('Gross Weight(KGS)', tracking=True)

    net_weight_pc = fields.Float('Net Weight(KG/pc)', tracking=True)
    net_weight_kgs = fields.Float('Net Weight(KGS)', tracking=True)

    length = fields.Float('Length(mm)', tracking=True)
    width = fields.Float('Width(mm)', tracking=True)
    height = fields.Float('Height(mm)', tracking=True)
    cbm_pc = fields.Char('CBM/pc', tracking=True)
    volume = fields.Float('Volume(cm³)', compute='_compute_volume_and_dimensions', store=True, tracking=True)
    dimensions = fields.Char('Dimensions(LxMxH cm)', compute='_compute_volume_and_dimensions', store=True,
                             tracking=True)

    @api.depends('length', 'width', 'height')
    def _compute_volume_and_dimensions(self):
        for order_id in self:
            order_id.dimensions = '{} x {} x {} cm'.format(
                order_id.length / 100,
                order_id.width / 100,
                order_id.height / 100)
            order_id.volume = (order_id.length / 100) * (order_id.width / 100) * (order_id.height / 100)

    @api.depends('owner_ref')
    def _compute_warehouse_no(self):
        prefix = 'FOXJ'
        for order_id in self:
            order_id.warehouse_enter_no = '{}-{}'.format(prefix, order_id.owner_ref or '')

    def generate_template_attachment(self):
        with NamedTemporaryFile() as tmp:
            fox_logo_path = get_module_resource('logistic_vessel', 'static/src/img', 'fox_logo.png')
            qr_code_path = get_module_resource('logistic_vessel', 'static/src/img', 'qr_code.png')
            map_path = get_module_resource('logistic_vessel', 'static/src/img', 'map.png')
            workbook = xlsxwriter.Workbook(tmp.name, {'in_memory': True})
            worksheet = workbook.add_worksheet(name=self.client_order_ref)

            file = open(fox_logo_path, 'rb')
            data = BytesIO(file.read())
            file.close()

            worksheet.insert_image('A1:B3', fox_logo_path, {'image_data': data, 'x_scale': 0.8, 'y_scale': 0.8})

            cell_format_c1h1 = workbook.add_format(
                {'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter'})
            cell_format_i1i2 = workbook.add_format(
                {'bold': True, 'font_size': 15, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
            cell_format_c2h2 = workbook.add_format(
                {'bold': True, 'font_size': 15, 'align': 'center', 'valign': 'vcenter'})

            cell_format_c3h3 = workbook.add_format(
                {'bold': True, 'font_size': 12, 'font_color': 'red',
                 'bg_color': 'yellow',
                 'align': 'center', 'valign': 'vcenter'})
            cell_format_a4i4 = workbook.add_format(
                {'bold': True, 'font_size': 10, 'text_wrap': True,
                 'align': 'center', 'valign': 'vcenter'})
            cell_format_a5b6 = workbook.add_format(
                {'bold': True, 'font_size': 12, 'text_wrap': True,
                 'bg_color': '#99ccff',
                 'align': 'center', 'valign': 'vcenter'})
            cell_format_c5c6 = workbook.add_format(
                {'bold': True, 'font_size': 16,
                 'align': 'center', 'valign': 'vcenter'})
            cell_format_d5i6 = workbook.add_format(
                {'bold': True, 'font_size': 16,
                 'align': 'left', 'valign': 'vcenter'})
            cell_format_a7i7 = workbook.add_format(
                {'bold': True, 'font_size': 10, 'text_wrap': True,
                 'bg_color': 'yellow',
                 'align': 'center', 'valign': 'vcenter'})
            cell_format_a8i8 = workbook.add_format(
                {'font_size': 10, 'text_wrap': True,
                 'align': 'left', 'valign': 'vcenter'})
            cell_format_a13i13 = workbook.add_format(
                {'bold': True, 'font_size': 12, 'text_wrap': True, 'font_color': 'red',
                 'align': 'left', 'valign': 'vcenter'})
            bold = workbook.add_format({"bold": True, 'font_size': 12})
            bold_size_10 = workbook.add_format({"bold": True, 'font_size': 10})
            color_underline = workbook.add_format(({
                'underline': 1, 'font_color': 'red', 'font_size': 14
            }))
            worksheet.merge_range('C1:H1', '上海福誉国际货物运输代理有限公司', cell_format_c1h1)
            worksheet.merge_range('I1:I2', '空运\n普货', cell_format_i1i2)
            worksheet.merge_range('C2:H2', 'SHANGHAI FOX GLOBAL LOGISTICS', cell_format_c2h2)

            worksheet.merge_range('C3:H3', '***送货此地图请打印纸质版，无纸质地图不收货**', cell_format_c3h3)
            worksheet.merge_range('A4:I4', '', cell_format_a4i4)
            worksheet.write_rich_string(
                'A4:I4',
                '***福誉新仓库地图', color_underline, ' （2021年08月28日启用） ',
                '(仓库凭进仓编号收货)***\n*** FOX new warehouse map (opened on August 28th, 2021)',
                cell_format_a4i4)
            worksheet.merge_range('A5:B6', '进仓编号 S/O\nNo：', cell_format_a5b6)
            worksheet.merge_range('C5:C6', 'FOXJ-', cell_format_c5c6)
            worksheet.merge_range('D5:I6', self.client_order_ref, cell_format_d5i6)
            worksheet.merge_range('A7:I7',
                                  '**本地图可以打印贴在货上，或者随身携带。无纸质地图不收货，进仓编号(手写无效)。***\n***寄送快递也是一样***',
                                  cell_format_a7i7)
            worksheet.merge_range('A8:I8', "", cell_format_a8i8)
            worksheet.write_rich_string(
                'A8',
                bold,
                '货物送：\n上海市浦东新区祝桥镇亭中村588-1号， 张付友 58103521/13162325926 \n',
                'Add: No. 588-1, TingZhong village, Zhuqiao Town, Pudong New Area, Shanghai Mr. Fuyou Zhang 58103521/13162325926 \n(You must be enter the warehouse with the S/O No, otherwise we have the right to ',
                bold_size_10, 'REJECT',
                'your cargoes. If you don\'t have S/O No, please contact Alice or Joy. (cus02@foxglobalsha.com or 0086-021-52387510) )',
                cell_format_a8i8)

            file = open(qr_code_path, 'rb')
            data = BytesIO(file.read())
            file.close()
            worksheet.insert_image('H9:I12', qr_code_path, {'image_data': data, 'x_scale': 0.5, 'y_scale': 0.5})

            align_map_txt = workbook.add_format({'font_size': 10, 'align': 'right', 'valign': 'bottom'})
            worksheet.merge_range('A9:G12', '（地图导航请扫描右侧二维码）', align_map_txt)
            worksheet.merge_range('A13:I13',
                                  '单证寄：\n上海市浦东新区祝桥镇亭中村588-1号， 伊家祥 15610661811 \n***单证上必须写好对应的进仓编号***',
                                  cell_format_a13i13)

            file = open(map_path, 'rb')
            data = BytesIO(file.read())
            file.close()

            cell_format_a15i38 = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            worksheet.merge_range('A14:I38', "", cell_format_a15i38)
            worksheet.insert_image('A14', map_path,
                                   {'image_data': data, 'x_scale': 1, 'y_scale': 1, 'object_position': 2})

            worksheet.set_row(3, 38)
            worksheet.set_row(6, 25)
            worksheet.set_row(7, 125)
            worksheet.set_row(12, 63)
            workbook.close()

            tmp.seek(0)
            stream = tmp.read()

            stram_encode = base64.b64encode(stream)
            file_md5 = hashlib.md5(stream)
            file_name = "{}.xlsx".format(self.client_order_ref)
            attachment_data = {
                'name': file_name,
                'datas': stram_encode,
                'description': file_md5.hexdigest(),
                'type': 'binary',
            }
            attach_id = self.env['ir.attachment'].create(attachment_data)
            return attach_id

    def action_quotation_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        attach_id = self.generate_template_attachment()
        self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        mail_template = self._find_mail_template()
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.id,
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
            'attachment_ids': [(6, 0, [attach_id.id])]
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def _find_mail_template(self):
        """ Get the appropriate mail template for the current sales order based on its state.

        If the SO is confirmed, we return the mail template for the sale confirmation.
        Otherwise, we return the quotation email template.

        :return: The correct mail template based on the current status
        :rtype: record of `mail.template` or `None` if not found
        """
        self.ensure_one()
        if self.env.context.get('proforma') or self.state not in ('sale', 'done'):
            return self.env.ref('logistic_vessel.mail_template_sale_order_notify_chinese', raise_if_not_found=False)
        else:
            return self._get_confirmation_template()

    def _get_confirmation_template(self):
        """ Get the mail template sent on SO confirmation (or for confirmed SO's).

        :return: `mail.template` record or None if default template wasn't found
        """
        return self.env.ref('logistic_vessel.mail_template_sale_order_notify_chinese', raise_if_not_found=False)

    def parse_stock_production_lot_data(self, order_line_id, lot_name):
        lot_data = {
            'product_id': order_line_id.product_id.id,
            'company_id': self.env.company.id,
            'name': lot_name
        }
        return lot_data

    def _show_cancel_wizard(self):
        # 去除邮件提示
        return False

    def get_production_lot_id(self, lot_data):
        lot_obj = self.env['stock.lot'].sudo()
        product_id = lot_data.get('product_id')
        lot_name = lot_data.get('name')

        lot_id = lot_obj.search([
            ('product_id', '=', product_id),
            ('name', '=', lot_name)
        ])

        if len(lot_id) > 1:
            raise ValidationError(u'批次解析错误: {}'.format(lot_id.mapped('name')))

        if lot_id:
            return lot_id.id
        else:
            lot_id = self.env['stock.lot'].create(lot_data)
            return lot_id.id

    def get_set_product_production_lot(self):
        for line_id in self:
            owner_ref_lot = line_id.owner_ref
            for order_line_id in line_id.order_line:
                if order_line_id.product_type == 'service' or order_line_id.product_id.tracking != 'lot':
                    continue

                if order_line_id.product_lot_id:
                    lot_name = owner_ref_lot
                    if order_line_id.product_lot_id.name == lot_name:
                        continue

                lot_data = self.parse_stock_production_lot_data(order_line_id, owner_ref_lot)
                lot_id = self.get_production_lot_id(lot_data)
                order_line_id.product_lot_id = lot_id

    # 确认订单时，创建服务费用
    def action_confirm(self):
        self.get_set_product_production_lot()
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_lot_id = fields.Many2one('stock.lot', string=u'批次')

    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        res.update({
            'sale_line_id': self.id,
            'move_lot_id': self.product_lot_id.id,
            'lot_name': self.order_id.owner_ref
        })
        return res

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields generated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        if self._context.get("skip_procurement"):
            return True
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            if line.order_id.order_type == 'stock_in':
                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id, product_qty, procurement_uom,
                    line.order_id.warehouse_id.lot_stock_id,
                    line.name, line.order_id.name, line.order_id.company_id, values))
            else:
                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id, product_qty, procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.product_id.display_name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True


class PackageList(models.Model):
    _name = 'vessel.package.list'
    _description = 'vessel Package'

    order_id = fields.Many2one('sale.order', string='Order')
    name = fields.Char('Description', required=True)
    qty = fields.Float('Qty(pcs)', required=True)
    gross_weight_pc = fields.Float('Gross Weight(KG/pc)')
    gross_weight_kgs = fields.Float('Gross Weight(KGS)')

    net_weight_pc = fields.Float('Net Weight(KG/pc)')
    net_weight_kgs = fields.Float('Net Weight(KGS)')

    length = fields.Float('Length(mm)')
    width = fields.Float('Width(mm)')
    height = fields.Float('Height(mm)')
    cbm_pc = fields.Char('CBM/pc')
