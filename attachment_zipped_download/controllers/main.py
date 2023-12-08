# Copyright 2019 César Fernández Domínguez <cesfernandez@outlook.com>
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import _, http
from odoo.http import request

DEFAULT_FILE_NAME = 'attachments'


class AttachmentZippedDownloadController(http.Controller):

    def get_model_field_value(self, attach_ids, field_name='owner_ref'):
        if not attach_ids:
            return DEFAULT_FILE_NAME
        res_model = list(set(attach_ids.mapped('res_model')))
        res_id = list(set(attach_ids.mapped('res_id')))
        if len(res_model) == 1 and len(res_id) == 1:
            model_id = request.env[res_model[0]].browse(res_id[0])
            if not model_id:
                return DEFAULT_FILE_NAME
            if hasattr(model_id, field_name):
                return getattr(model_id, field_name)
            return DEFAULT_FILE_NAME
        return DEFAULT_FILE_NAME

    @http.route("/web/attachment/download_zip", type="http", auth="user")
    def download_zip(self, ids=None, debug=0):
        ids = [] if not ids else ids
        if len(ids) == 0:
            return
        list_ids = map(int, ids.split(","))

        attach_ids = request.env["ir.attachment"].browse(list_ids)
        out_file = attach_ids._create_temp_zip()

        field_name = self.get_model_field_value(attach_ids)
        download_name = '{}.zip'.format(field_name)
        out_file_bytes = out_file.getvalue()
        return http.Stream(
            type='data', data=out_file_bytes).get_response(mimetype="application/zip",
                                                           download_name=download_name)
        # zip_http_headers = [
        #     (
        #         "Content-Type",
        #         "application/zip"
        #     ),
        #     ("Content-Length", len(out_file_bytes)),
        # ]
        # return request.make_response(out_file_bytes, headers=zip_http_headers)
