# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import MissingError, UserError
import requests
import re
from odoo.http import Stream, request


def is_http_url(s):
    regex = re.compile(
        r'^(?:http|ftp|)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if regex.match(s):
        return True
    else:
        return False


class StreamExtended(Stream):

    @classmethod
    def from_binary_field_by_url(cls, record, field_name):
        """ Create a :class:`~Stream`: from a binary field. """
        data_b64 = record[field_name]
        response = requests.get(data_b64)
        data = response.content
        return cls(
            type='data',
            data=data,
            etag=request.env['ir.attachment']._compute_checksum(data),
            last_modified=record['__last_update'] if record._log_access else None,
            size=len(data),
        )


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        """
        Low level method responsible for the actual conversion from a
        model record to a stream. This method is an extensible hook for
        other modules. It is not meant to be directly called from
        outside or the ir.binary model.

        :param record: the record where to load the data from.
        :param str field_name: the binary field where to load the data
            from.
        :rtype: odoo.http.Stream
        """
        if record._name == 'ir.attachment' and field_name in ('raw', 'datas', 'db_datas'):
            return Stream.from_attachment(record)

        record.check_field_access_rights('read', [field_name])
        field_def = record._fields[field_name]
        # fields.Binary(attachment=False) or compute/related
        if not field_def.attachment or field_def.compute or field_def.related:
            data_b64 = record[field_name]
            if data_b64 and is_http_url(data_b64.decode()):
                return StreamExtended.from_binary_field_by_url(record, field_name)
            else:
                return Stream.from_binary_field(record, field_name)

        # fields.Binary(attachment=True)
        field_attachment = self.env['ir.attachment'].sudo().search(
            domain=[('res_model', '=', record._name),
                    ('res_id', '=', record.id),
                    ('res_field', '=', field_name)],
            limit=1)
        if not field_attachment:
            raise MissingError("The related attachment does not exist.")
        return Stream.from_attachment(field_attachment)
