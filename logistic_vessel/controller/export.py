# -*- coding: utf-8 -*-
from odoo.addons.web.controllers.export import ExcelExport, ExportXlsxWriter
from odoo.tools import lazy_property, osutil, pycompat
from odoo.http import request
import operator
import json
import logging
from odoo import http
from odoo.tools.translate import _
from odoo.exceptions import UserError
import datetime


_logger = logging.getLogger(__name__)


class ExportXlsxWriterInherit(ExportXlsxWriter):

    def write_cell(self, row, column, cell_value, cus_float_format=None):
        cell_style = self.workbook.add_format({'text_wrap': True})

        if isinstance(cell_value, bytes):
            try:
                # because xlsx uses raw export, we can get a bytes object
                # here. xlsxwriter does not support bytes values in Python 3 ->
                # assume this is base64 and decode to a string, if this
                # fails note that you can't export
                cell_value = pycompat.to_text(cell_value)
            except UnicodeDecodeError:
                raise UserError(
                    _("Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.",
                      self.field_names)[column])
        elif isinstance(cell_value, (list, tuple, dict)):
            cell_value = pycompat.to_text(cell_value)

        if isinstance(cell_value, str):
            if len(cell_value) > self.worksheet.xls_strmax:
                cell_value = _(
                    "The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.",
                    self.worksheet.xls_strmax)
            else:
                cell_value = cell_value.replace("\r", " ")
        elif isinstance(cell_value, datetime.datetime):
            cell_style = self.datetime_style
        elif isinstance(cell_value, datetime.date):
            cell_style = self.date_style
        elif isinstance(cell_value, float):
            if cus_float_format:
                cell_style.set_num_format(cus_float_format)
            else:
                cell_style.set_num_format(self.float_format)
        self.write(row, column, cell_value, cell_style)


class ExcelExportInherit(ExcelExport):
    def __init__(self):
        super().__init__()
        self.model_name = None
        self.field_names = None
        self.import_compat = False
        self.cus_format = {}

    @http.route('/web/export/xlsx', type='http', auth="user")
    def web_export_xlsx(self, data):
        try:
            params = json.loads(data)
            model, fields, ids, domain, import_compat = \
                operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

            Model = request.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
            if not Model._is_an_ordinary_table():
                fields = [field for field in fields if field['name'] != 'id']

            self.model_name = model
            self.field_names = fields
            self.import_compat = import_compat
            return super().web_export_xlsx(data)
        except Exception as e:
            return super().web_export_xlsx(data)

    def get_correct_format(self, digits):
        if digits == 0:
            return '#,##0'
        format_attr = '#,##0.{}'.format(digits * "0")
        return format_attr

    def get_field_correct_digits_format(self, field_index, field_name):
        try:
            decimal_precision_name = request.env[self.model_name]._fields[field_name]._digits
            decimal_precision = request.env['decimal.precision'].search([('name', '=', decimal_precision_name)])
            digits = decimal_precision.digits
            self.cus_format[field_index] = self.get_correct_format(digits)
        except Exception as e:
            _logger.error('出现错误: {}'.format(e))

    def from_data(self, fields, rows):
        if self.field_names and self.model_name:
            for field_index, field_id in enumerate(self.field_names):
                if field_id.get('type') == 'float':
                    self.get_field_correct_digits_format(field_index, field_id.get('name'))
        with ExportXlsxWriterInherit(fields, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if cell_index in self.cus_format.keys():
                        cus_format = self.cus_format.get(cell_index)
                        xlsx_writer.write_cell(row_index + 1, cell_index, cell_value, cus_float_format=cus_format)
                    else:
                        xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value

