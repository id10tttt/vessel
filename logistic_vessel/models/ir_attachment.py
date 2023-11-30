# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # TODO: 不能获取到正确的名称
    def get_model_file_name(self, values):
        if values.get('res_model') == 'stock.picking' and values.get('res_field') == 'delivery_note_file':
            picking_id = self.env[values.get('res_model')].browse(values.get('res_id'))
            if picking_id.delivery_note_file_filename:
                return picking_id.delivery_note_file_filename
            if values.get('name') == 'delivery_note_file':
                return 'file'
            return values.get('name')
        return values.get('name')
