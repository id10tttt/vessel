# -*- coding: utf-8 -*-
from odoo.addons.web.controllers.export import ExcelExport, ExportXlsxWriter, GroupExportXlsxWriter
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


class GroupExportXlsxWriterInherit(GroupExportXlsxWriter, ExportXlsxWriterInherit):
    def get_correct_format(self, digits):
        if digits == 0:
            return '#,##0'
        format_attr = '#,##0.{}'.format(digits * "0")
        return format_attr

    def get_field_correct_digits_format(self, model, field_name):
        try:
            decimal_precision_name = request.env[model]._fields[field_name]._digits
            decimal_precision = request.env['decimal.precision'].search([('name', '=', decimal_precision_name)])
            digits = decimal_precision.digits
            return self.get_correct_format(digits)
        except Exception as e:
            _logger.error('出现错误: {}'.format(e))
            return '#,##,0.00'

    def _write_group_header(self, row, column, label, group, group_depth=0, model=None):
        aggregates = group.aggregated_values

        label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)
        self.write(row, column, label, self.header_bold_style)
        for field in self.fields[1:]:  # No aggregates allowed in the first column because of the group title
            field_header_format = self.workbook.add_format({'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'})
            column += 1
            aggregated_value = aggregates.get(field['name'])
            if field.get('type') == 'monetary':
                self.header_bold_style.set_num_format(self.monetary_format)
            elif field.get('type') == 'float':
                if model:
                    cell_style = self.get_field_correct_digits_format(model, field['name'])
                else:
                    cell_style = self.float_format
                field_header_format.set_num_format(cell_style)
            else:
                aggregated_value = str(aggregated_value if aggregated_value is not None else '')
            self.write(row, column, aggregated_value, field_header_format)
        return row + 1, 0

    def write_group(self, row, column, group_name, group, group_depth=0, model=None, cus_float_format=None):
        group_name = group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else group_name
        if group._groupby_type[group_depth] != 'boolean':
            group_name = group_name or _("Undefined")
        row, column = self._write_group_header(row, column, group_name, group, group_depth, model=model)

        # Recursively write sub-groups
        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(row, column, child_group_name, child_group, group_depth + 1, model=model)

        for record in group.data:
            row, column = self._write_row(row, column, record, cus_float_format=cus_float_format)
        return row, column

    def _write_row(self, row, column, data, cus_float_format=None):
        for data_index, value in enumerate(data):
            if data_index in cus_float_format.keys():
                cus_format = cus_float_format.get(data_index)
                self.write_cell(row, column, value, cus_float_format=cus_format)
            else:
                self.write_cell(row, column, value)
            column += 1
        return row + 1, 0


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

            if self.field_names and self.model_name:
                for field_index, field_id in enumerate(self.field_names):
                    if field_id.get('type') == 'float':
                        self.get_field_correct_digits_format(field_index, field_id.get('name'))

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

    def from_group_data(self, fields, groups):
        with GroupExportXlsxWriterInherit(fields, groups.count) as xlsx_writer:
            x, y = 1, 0
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group, model=self.model_name,
                                               cus_float_format=self.cus_format)

        return xlsx_writer.value

    def from_data(self, fields, rows):
        with ExportXlsxWriterInherit(fields, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if cell_index in self.cus_format.keys():
                        cus_format = self.cus_format.get(cell_index)
                        xlsx_writer.write_cell(row_index + 1, cell_index, cell_value, cus_float_format=cus_format)
                    else:
                        xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value
