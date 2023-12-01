# -*- coding: utf-8 -*-
import os

from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.pdf_tools import ProcessPDF
from ..utils.excel_to_pdf import convert_excel_to_pdf
from odoo.tools.misc import file_path
import time
import hashlib
from odoo.tools.mimetypes import guess_mimetype
import base64

import logging

BASE_TMP_PATH = '/tmp'
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    name = fields.Char(
        '参考号', default='FOX/', required=True,
        copy=False, index='trigram', readonly=False)

    receipt_order = fields.Char('回单')
    method_id = fields.Many2one('delivery.method', string='运输方式')
    pick_up_charge = fields.Float('Pick Up Charge', digits='Pick Up Charge', default=0.0)
    delivery_note_file = fields.Binary('Delivery Note File', attachment=True)
    delivery_note_file_filename = fields.Char('Delivery Note File Name')
    file_download_link = fields.Char('File Name', compute='_compute_file_download_link')
    warehouse_enter_no = fields.Char('Warehouse Enter No')
    arrival_date = fields.Date('Arrival Date', default=fields.Date.today)
    dest = fields.Char('Dest')
    awb = fields.Char('Awb')
    departure_date = fields.Date('Departure Date')
    ref = fields.Char('Ref')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            defaults = self.default_get(['name', 'picking_type_id'])
            picking_type = self.env['stock.picking.type'].browse(
                vals.get('picking_type_id', defaults.get('picking_type_id')))
            if (vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and
                    vals.get('picking_type_id', defaults.get('picking_type_id'))):
                if picking_type.sequence_id:
                    vals['name'] = picking_type.sequence_id.next_by_id()
            if (vals.get('name', 'FOX/') == 'FOX/' and defaults.get('name', 'FOX/') == 'FOX/' and
                    vals.get('picking_type_id', defaults.get('picking_type_id'))):
                if picking_type.sequence_id:
                    vals['name'] = picking_type.sequence_id.next_by_id()
        return super().create(vals_list)

    @api.onchange('delivery_note_file', 'delivery_note_file_filename')
    def _compute_file_download_link(self):
        for line_id in self:
            if not line_id.delivery_note_file_filename and line_id.delivery_note_file:
                line_id.file_download_link = None
            else:
                field_attachment = self.env['ir.attachment'].sudo().search(
                    domain=[('res_model', '=', line_id._name),
                            ('res_id', '=', line_id.id),
                            ('res_field', '=', 'delivery_note_file')],
                    limit=1)
                if field_attachment:
                    line_id.file_download_link = field_attachment.url
                else:
                    line_id.file_download_link = None

    def _compute_hide_pickign_type(self):
        # self.hide_picking_type = self.env.context.get('default_picking_type_id', False)
        self.hide_picking_type = False

    def generate_template_attachment(self):
        seal = file_path('logistic_vessel/static/src/img/seal.png')
        font_path = file_path('logistic_vessel/utils/Candaral.ttf')

        mimetype = guess_mimetype(self.delivery_note_file)
        if ('officedocument' in mimetype or
                (mimetype == 'application/octet-stream' and 'xls' in self.delivery_note_file_filename) or
                (mimetype == 'text/plain' and 'xls' in self.delivery_note_file_filename)):

            excel_file = str(time.time())
            excel_file_path = '{}/{}.xlsx'.format(BASE_TMP_PATH, excel_file)
            pdf_path = '{}/{}.pdf'.format(BASE_TMP_PATH, excel_file)
            try:
                decode_stream = base64.b64decode(self.delivery_note_file)
                with open(excel_file_path, 'wb') as f:
                    f.write(decode_stream)
                    f.close()
                pdf_path = convert_excel_to_pdf(excel_file_path, excel_file)

                _logger.info('生成PDF 文件: {}'.format(pdf_path))
                water_mark_txt = str(fields.Date.today())
                pdf = ProcessPDF(pdf_content=None, pdf_file_path=pdf_path,
                                 seal=seal, water_mark_txt=water_mark_txt,
                                 font_path=font_path,
                                 clarity=1.5)
                pdf_stream = pdf.out()

                # Delete tmp file
                os.unlink(excel_file_path)
                os.unlink(pdf_path)
            except Exception as e:
                os.unlink(excel_file_path)
                os.unlink(pdf_path)
                raise UserError('Excel 解析文件出现错误! {}'.format(e))
        else:
            try:
                # file_resp = requests.get(self.file_download_link)
                # pdf_stream = file_resp.content
                pdf_stream = base64.b64decode(self.delivery_note_file)
                water_mark_txt = str(fields.Date.today())
                pdf = ProcessPDF(pdf_content=pdf_stream, seal=seal, water_mark_txt=water_mark_txt, font_path=font_path,
                                 clarity=1.5)
                pdf_stream = pdf.out()
            except Exception as e:
                raise UserError('Pdf/Image 解析文件出现错误! {}'.format(e))

        file_name = '{}.pdf'.format(self.delivery_note_file_filename)
        stram_encode = base64.b64encode(pdf_stream)
        file_md5 = hashlib.md5(pdf_stream)
        attachment_data = {
            'name': file_name,
            'datas': stram_encode,
            'description': file_md5.hexdigest(),
            'type': 'binary',
        }
        attach_id = self.env['ir.attachment'].create(attachment_data)
        _logger.info('创建附件: {}, {}'.format(file_name, attach_id))
        return attach_id

    def action_delivery_note_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        if not self.delivery_note_file_filename:
            raise UserError('请先上传文件!')
        attach_id = self.generate_template_attachment()
        lang = self.env.context.get('lang')
        mail_template = self._find_mail_template()
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'stock.picking',
            'default_res_ids': self.ids,
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'logistic_vessel.mail_notification_layout_inherit',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
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
        return self.env.ref('logistic_vessel.mail_template_delivery_notes', raise_if_not_found=False)

    def parse_stock_quant_package_data(self, move_line_id):
        data = {
            'name': '{}#{}'.format(move_line_id.picking_id.sale_id.owner_ref if move_line_id.picking_id.sale_id else '',
                                   move_line_id.id),
            'gross_weight_pc': move_line_id.gross_weight_pc,
            'length': move_line_id.length,
            'width': move_line_id.width,
            'height': move_line_id.height,
        }
        return data

    def set_correct_product_package(self):
        package_obj = self.env['stock.quant.package']
        for picking_id in self:
            if picking_id.sale_id and picking_id.sale_id.order_type != 'stock_in':
                continue
            for move_line_id in picking_id.move_line_ids:
                package_data = self.parse_stock_quant_package_data(move_line_id)
                package_id = package_obj.search([
                    ('name', '=', package_data.get('name'))
                ])
                if not package_id:
                    # 创建新的记录
                    package_id = package_obj.create(package_data)
                    _logger.info('生成package: {}'.format(package_id))
                if package_id:
                    move_line_id.result_package_id = package_id

    def button_validate(self):
        self.set_correct_product_package()
        return super().button_validate()
