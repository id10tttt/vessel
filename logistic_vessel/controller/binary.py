# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.tools._vendor.send_file import send_file as _send_file

from odoo import SUPERUSER_ID, _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request, Response
from odoo.tools import file_open, file_path, replace_exceptions
from io import BytesIO
import requests
_logger = logging.getLogger(__name__)

BAD_X_SENDFILE_ERROR = """\
Odoo is running with --x-sendfile but is receiving /web/filestore requests.

With --x-sendfile enabled, NGINX should be serving the
/web/filestore route, however Odoo is receiving the
request.

This usually indicates that NGINX is badly configured,
please make sure the /web/filestore location block exists
in your configuration file and that it is similar to:

    location /web/filestore {{
        internal;
        alias {data_dir}/filestore;
    }}
"""


def clean(name):
    return name.replace('\x3c', '')


class Binary(http.Controller):
    @http.route(['/web/content',
                 '/web/content/<string:xmlid>',
                 '/web/content/<string:xmlid>/<string:filename>',
                 '/web/content/<int:id>',
                 '/web/content/<int:id>/<string:filename>',
                 '/web/content/<string:model>/<int:id>/<string:field>',
                 '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'],
                cors='*',
                type='http', auth="public")
    # pylint: disable=redefined-builtin,invalid-name
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                       filename=None, filename_field='name', mimetype=None, unique=False,
                       download=False, access_token=None, nocache=False):
        with replace_exceptions(UserError, by=request.not_found()):
            record = request.env['ir.binary']._find_record(xmlid, model, id and int(id), access_token)
            stream = request.env['ir.binary']._get_stream_from(record, field, filename, filename_field, mimetype)
        send_file_kwargs = {'as_attachment': download}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None
        if field in ['delivery_note_file', 'invoice_file', 'packing_file'] and getattr(stream, 'url'):
            download_name = filename or stream.download_name
            send_file_kwargs = {
                'mimetype': stream.mimetype,
                'download_name': download_name,
                'conditional': stream.conditional,
                'etag': stream.etag,
                'last_modified': stream.last_modified,
                'environ': request.httprequest.environ,
                'response_class': Response,
                **send_file_kwargs,
            }
            res = requests.get(stream.url)
            return _send_file(BytesIO(res.content), **send_file_kwargs)

        res = stream.get_response(**send_file_kwargs)
        res.headers['Content-Security-Policy'] = "default-src 'none'"
        return res
