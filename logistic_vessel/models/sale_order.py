# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import xlsxwriter
from typing import Dict, List
from io import BytesIO
import hashlib
import base64
from odoo.tools import float_compare
from tempfile import NamedTemporaryFile
from odoo.tools.misc import file_path
import logging

_logger = logging.getLogger(__name__)

SALE_ORDER_STATE = [
    ('draft', "出仓单"),
    ('sent', "已发送出仓单"),
    ('sale', "销售订单"),
    ('cancel', "已取消"),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _sql_constraints = [
        ('unique_type_owner_ref_state', 'unique(order_type,owner_ref,state)',
         'Order type and Owner Ref and Order state must unique!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_type') == 'stock_in':
                if 'company_id' in vals:
                    self = self.with_company(vals['company_id'])
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.order.stock.in', sequence_date=seq_date) or _("New")

        return super().create(vals_list)

    client_order_ref = fields.Char(string="Your Ref", copy=False)
    method_id = fields.Many2one('delivery.method', string='运输方式')
    delivery_title = fields.Char('邮件标题')
    order_type = fields.Selection([
        ('stock_in', u'入库订单'),
        ('stock_out', u'出库订单'),
    ], string='订单类型', default='stock_out')

    mv = fields.Many2one('freight.vessel', string='M/V', tracking=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Supplier",
        required=True, change_default=True, index=True,
        tracking=1,
        domain="[('company_id', 'in', (False, company_id))]")
    owner_id = fields.Many2one('res.partner', string='Owner', tracking=True)
    email = fields.Char('E-mail', tracking=True)
    invoice_no = fields.Char('Invoice No', tracking=True)
    owner_ref = fields.Char('Owner Ref', tracking=True, copy=False)
    invoice_date = fields.Date('Invoice Date', tracking=True, copy=False)
    location_id = fields.Many2one('res.country.state', string='State', tracking=True)
    warehouse_enter_no = fields.Char('Warehouse Enter No', compute='_compute_warehouse_no', store=True)

    invoice_file_url = fields.Char('Invoice Url', compute='_compute_invoice_packing_url')
    packing_file_url = fields.Char('Packing Url', compute='_compute_invoice_packing_url')

    invoice_file = fields.Binary('Invoice File', attachment=True)
    invoice_filename = fields.Char('Invoice File Name')

    packing_file = fields.Binary('Packing File', attachment=True)
    packing_filename = fields.Char('Packing File Name')

    dest = fields.Char('Dest')
    awb = fields.Char('Awb')
    departure_date = fields.Date('Departure Date')
    ref = fields.Char('Ref')
    arrival_date = fields.Date('Arrival Date')
    date_order = fields.Datetime(
        string="Ready Date",
        required=True, copy=False,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
        default=fields.Datetime.now)

    stock_out_state = fields.Selection(
        selection=SALE_ORDER_STATE,
        string="状态",
        copy=False, store=False,
        compute='_compute_stock_out_state')

    def get_order_attachment(self):
        # attach_ids = self.env['ir.attachment'].search([
        #     ('res_model', '=', self._name),
        #     ('res_id', 'in', self.ids),
        #     ('res_field', 'in', ['invoice_file', 'packing_file'])
        # ])
        attach_ids = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('res_field', '=', False)
        ])
        return attach_ids

    def action_download_order_attach(self, ids):
        return {
            "type": "ir.actions.act_url",
            "url": "/web/attachment/download_zip?ids=%s" % (ids),
            "target": "new",
        }

    def action_attachments_download(self):
        self.ensure_one()
        items = self.get_order_attachment()
        if not items:
            raise UserError('您并没有上传附件(Invoice/Packing)，无法下载导出！')
        ids = ",".join(map(str, items.ids))
        return self.action_download_order_attach(ids)

    def create_attachment_ids(self, file_name, file_stream, field_name, res_id):
        stream_encode = base64.b64decode(file_stream)
        file_md5 = hashlib.md5(stream_encode)
        attachment_data = {
            'name': file_name,
            'datas': file_stream,
            'description': file_md5.hexdigest(),
            'type': 'binary',
            'res_field': field_name,
            'res_model': self._name,
            'res_id': res_id,
            'file_size': len(stream_encode)
        }
        exist_att_ids = self.env['ir.attachment'].search([
            ('res_field', '=', field_name),
            ('res_model', '=', self._name),
            ('res_id', '=', res_id)
        ])
        # Unlink before create
        if exist_att_ids:
            exist_att_ids.unlink()
        attach_id = self.env['ir.attachment'].create(attachment_data)
        _logger.info('创建附件: {}, {}'.format(file_name, attach_id))

    def web_save(self, vals, specification: Dict[str, Dict], next_id=None) -> List[Dict]:
        # Write
        if self:
            invoice_file = vals.get('invoice_file')
            invoice_filename = vals.get('invoice_filename')

            if invoice_file and invoice_filename:
                self.create_attachment_ids(
                    invoice_filename, invoice_file, 'invoice_file', res_id=self.id)
                vals.pop('invoice_file')

            packing_file = vals.get('packing_file')
            packing_filename = vals.get('packing_filename')

            if packing_filename and packing_file:
                self.create_attachment_ids(
                    packing_filename, packing_file, 'packing_file', res_id=self.id)
                vals.pop('packing_file')

            return super().web_save(vals, specification, next_id)
        # Create
        else:
            invoice_file = vals.get('invoice_file')
            invoice_filename = vals.get('invoice_filename')
            packing_file = vals.get('packing_file')
            packing_filename = vals.get('packing_filename')
            vals.pop('invoice_file')
            vals.pop('packing_file')
            res = super().web_save(vals, specification, next_id)
            if invoice_file and invoice_filename:
                self.create_attachment_ids(
                    invoice_filename, invoice_file, 'invoice_file', res_id=res[0].get('id'))
            if packing_filename and packing_file:
                self.create_attachment_ids(
                    packing_filename, packing_file, 'packing_file', res_id=res[0].get('id'))
            res[0].update({
                'invoice_file': invoice_file,
                'packing_file': packing_file,
            })
            return res

    @api.depends('state')
    def _compute_stock_out_state(self):
        for order_id in self:
            order_id.stock_out_state = order_id.state

    def action_cancel(self):
        if any([[p.state == 'done' for p in self.picking_ids]]):
            raise ValidationError('不允许取消')
        return super().action_cancel()

    def generate_attachment_hyperlink(self, attach_id, record, file_name):
        if not attach_id:
            return ''
        attach_id = attach_id[0]
        return '=HYPERLINK("{}", "{}")'.format(attach_id.url, getattr(record, file_name))

    @api.depends('invoice_file', 'packing_file', 'invoice_filename', 'packing_filename')
    def _compute_invoice_packing_url(self):
        for record in self:
            attachment_ids = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', record._name),
                ('res_id', '=', record.id),
                ('res_field', 'in', ['invoice_file', 'packing_file'])
            ], order='id desc')
            record.invoice_file_url = self.generate_attachment_hyperlink(
                attachment_ids.filtered(lambda f: f.res_field == 'invoice_file'), record, 'invoice_filename')
            record.packing_file_url = self.generate_attachment_hyperlink(
                attachment_ids.filtered(lambda f: f.res_field == 'packing_file'), record, 'packing_filename')

    @api.depends('owner_ref')
    def _compute_warehouse_no(self):
        prefix = 'FOXJ'
        for order_id in self:
            order_id.warehouse_enter_no = '{}-{}'.format(prefix, order_id.owner_ref or '')

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        return [
            [
                'user',
                lambda pdata: pdata['type'] == 'user',
                {
                    'active': True,
                    'has_button_access': False
                }
            ], [
                'portal',
                lambda pdata: pdata['type'] == 'portal',
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'follower',
                lambda pdata: pdata['is_follower'],
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'customer',
                lambda pdata: True,
                {
                    'active': True,
                    'has_button_access': False,
                }
            ]
        ]

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        res = super()._notify_by_email_prepare_rendering_context(message, msg_vals, model_description=model_description,
                                                                 force_email_company=force_email_company,
                                                                 force_email_lang=force_email_lang)
        res.update({
            'model_description': False,
            'record': False,
            'record_name': False,
            'subtitles': False
        })
        return res

    def generate_template_attachment(self):
        with NamedTemporaryFile() as tmp:
            fox_logo_path = file_path('logistic_vessel/static/src/img/fox_logo.png')
            qr_code_path = file_path('logistic_vessel/static/src/img/qr_code.png')
            map_path = file_path('logistic_vessel/static/src/img/map.png')
            workbook = xlsxwriter.Workbook(tmp.name, {'in_memory': True})
            worksheet = workbook.add_worksheet(name=self.owner_ref or self.warehouse_enter_no or 'FOXJ')

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
            worksheet.merge_range('D5:I6', self.owner_ref, cell_format_d5i6)
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
            file_name = "{}.xlsx".format(self.owner_ref)
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
            'default_res_ids': self.ids,
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'logistic_vessel.mail_notification_layout_inherit',
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

                # 由 Pending 创建
                if order_line_id.assign_lot and order_line_id.product_lot_id and line_id.order_type == 'stock_out':
                    continue

                if order_line_id.product_lot_id:
                    lot_name = owner_ref_lot
                    if order_line_id.product_lot_id.name == lot_name:
                        continue

                lot_data = self.parse_stock_production_lot_data(order_line_id, owner_ref_lot)
                lot_id = self.get_production_lot_id(lot_data)
                order_line_id.product_lot_id = lot_id

    def get_stock_quant_package_id(self, package_data):
        package_obj = self.env['stock.quant.package'].sudo()
        package_name = package_data.get('name')

        package_id = package_obj.search([
            ('name', '=', package_name)
        ])

        if len(package_id) > 1:
            raise ValidationError(u'Package解析错误: {}'.format(package_id.mapped('name')))

        if package_id:
            return package_id.id
        else:
            package_id = package_obj.create(package_data)
            return package_id.id

    def parse_stock_quant_package_data(self, order_line_id, package_name):
        package_data = {
            'name': package_name,
            'length': order_line_id.length,
            'width': order_line_id.width,
            'height': order_line_id.height,
            'gross_weight_pc': order_line_id.gross_weight_pc,
        }
        return package_data

    def get_set_product_package(self):
        for line_id in self:
            owner_ref_lot = line_id.owner_ref
            for order_line_id in line_id.order_line:
                if order_line_id.product_type == 'service' or order_line_id.product_id.tracking != 'lot':
                    continue

                if order_line_id.assign_package:
                    continue

                package_name = '{}#{}{}{}'.format(owner_ref_lot, order_line_id.length, order_line_id.width,
                                                  order_line_id.height)

                if order_line_id.package_id:

                    if order_line_id.package_id.name == package_name:
                        continue

                package_data = self.parse_stock_quant_package_data(order_line_id, owner_ref_lot)
                package_id = self.get_stock_quant_package_id(package_data)
                order_line_id.package_id = package_id

    def button_validate_picking_one_step_by_sale_order(self, order_ids):
        order_ids = order_ids.filtered(lambda so: so.order_type == 'stock_out')
        if order_ids:
            picking_ids = order_ids.picking_ids
            picking_ids.button_validate()

    def action_confirm(self):
        # 如果没有明细，生成一个缺省值
        self.action_set_default_order_line()
        # 设置批次
        self.get_set_product_production_lot()
        # 设置Package
        self.get_set_product_package()
        self.write({
            'arrival_date': fields.Date.today()
        })
        return super().action_confirm()

    def action_confirm_picking(self):
        res = self.action_confirm()
        self.button_validate_picking_one_step_by_sale_order(self)
        return res

    def get_default_product_id(self):
        default_product_id = self.env['product.product'].sudo().search([
            ('default_code', '=', '000000')
        ])
        if not default_product_id:
            return False
        return default_product_id.id

    def action_set_default_order_line(self):
        default_product_id = self.get_default_product_id()
        for order_id in self:
            if order_id.order_line:
                continue

            if not default_product_id:
                raise ValidationError('没有找到对应的产品, 产品编码: 000000')
            data = {
                'product_id': default_product_id,
                'product_uom_qty': 1
            }
            order_id.write({
                'order_line': [(0, 0, data)]
            })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def set_default_product_id(self):
        default_product_id = self.env['product.product'].sudo().search([
            ('default_code', '=', '000000')
        ])
        if not default_product_id:
            return False
        return default_product_id.id

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        default=lambda self: self.set_default_product_id(),
        change_default=True, ondelete='restrict', check_company=True, index='btree_not_null',
        domain="[('sale_ok', '=', True)]")
    product_lot_id = fields.Many2one('stock.lot', string=u'批次')
    gross_weight_pc = fields.Float('Gross Weight(KG/pc)', required=True, default='0.0')

    length = fields.Float('Length(cm)', required=True, default=0.0, digits='Vessel Package Volume')
    width = fields.Float('Width(cm)', required=True, default=0.0, digits='Vessel Package Volume')
    height = fields.Float('Height(cm)', required=True, default=0.0, digits='Vessel Package Volume')

    volume = fields.Float('Volume(m³)', compute='_compute_volume_and_dimensions', store=True,
                          digits='Vessel Package Volume')
    dimensions = fields.Char('Dimensions(LxMxH cm)', compute='_compute_volume_and_dimensions', store=True)

    package_id = fields.Many2one('stock.quant.package', string='Package')

    hs_code = fields.Char('HS Code')
    declaration = fields.Char('Customs declaration')

    assign_package = fields.Boolean('Assign Package', default=False, copy=False)
    assign_lot = fields.Boolean('Assign Lot', default=False, copy=False)

    supplier_id = fields.Many2one('res.partner', string='Supplier')

    @api.depends('length', 'width', 'height')
    def _compute_volume_and_dimensions(self):
        for order_id in self:
            order_id.dimensions = '{} x {} x {} cm'.format(
                order_id.length,
                order_id.width,
                order_id.height)
            order_id.volume = (order_id.length * order_id.width * order_id.height) / (100 * 100 * 100)

    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        res.update({
            'sale_line_id': self.id,
            'move_lot_id': self.product_lot_id.id,
            'move_package_id': self.package_id.id,
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
