# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.pdf_tools import ProcessPDF
from odoo.tools.misc import file_path
import hashlib
from io import BytesIO
import requests
import base64

import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_note_file = fields.Binary('Delivery Note File', attachment=True)
    delivery_note_file_filename = fields.Char('Delivery Note File Name')
    file_download_link = fields.Char('File Name', compute='_compute_file_download_link')
    warehouse_enter_no = fields.Char('Warehouse Enter No')
    arrival_date = fields.Date('Arrival Date')
    dest = fields.Char('Dest')
    awb = fields.Char('Awb')
    departure_date = fields.Date('Departure Date')
    ref = fields.Char('Ref')

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
        file_resp = requests.get(self.file_download_link)
        pdf_stream = file_resp.content
        water_mark_txt = str(fields.Date.today())
        pdf = ProcessPDF(pdf_content=pdf_stream, seal=seal, water_mark_txt=water_mark_txt, font_path=font_path, clarity=1.5)
        pdf_stream = pdf.out()

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
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
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
