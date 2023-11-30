import base64
import hashlib
import logging
import os
import oss2
from odoo import api, fields, models, tools
from odoo.tools.safe_eval import safe_eval
import datetime
import requests
from odoo.exceptions import AccessError
from urllib.parse import urlparse

BUCKET_HEADER = 'VESSEL/'
_logger = logging.getLogger(__name__)


def is_oss_bucket(bucket):
    if hasattr(bucket, 'get_bucket_info'):
        bucket_info = getattr(bucket, 'get_bucket_info')()
        headers = bucket_info.headers
        server_name = headers.get('Server')
        return server_name and 'OSS' in server_name
    app_name = getattr(bucket, "app_name", None)
    return app_name and app_name == "oss"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    oss_file_name = fields.Char('OSS file name')

    def unlink(self):
        oss_enable_state = self._get_oss_settings('oss.enable_oss', 'OSS_ENABLE')
        if oss_enable_state:
            for obj_id in self:
                obj_id._file_delete(obj_id.oss_file_name)
        return super().unlink()

    def _file_delete(self, fname):
        _logger.info('start unlink file: {}'.format(fname))
        oss_bucket = self._get_oss_resource()
        oss_bucket.delete_object(fname)
        _logger.info({
            'oss delete': fname
        })

    def _get_oss_settings(self, param_name, os_var_name):
        config_obj = self.env["ir.config_parameter"]
        res = config_obj.sudo().get_param(param_name)
        if not res:
            res = os.environ.get(os_var_name)
        return res

    def parse_alicloud_oss_image_url(self, url):
        if 'aliyuncs.com' not in url:
            return url
        parsed_url = urlparse(url)
        file_url = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
        return file_url

    @api.model
    def _get_oss_object_url(self, oss_bucket, file_name, timeout):
        object_url = oss_bucket.sign_url('GET', file_name, timeout)
        object_url = self.parse_alicloud_oss_image_url(object_url)
        return object_url

    def get_oss_resource(self):
        return self._get_oss_resource()

    @api.model
    def _get_oss_resource(self):
        access_key_id = self._get_oss_settings("oss.access_key_id", "OSS_ACCESS_KEY_ID")
        secret_key = self._get_oss_settings("oss.secret_key", "OSS_SECRET_KEY")
        bucket_name = self._get_oss_settings("oss.bucket", "OSS_BUCKET")
        endpoint_url = self._get_oss_settings("oss.endpoint_url", "OSS_ENDPOINT_URL")

        if not access_key_id or not secret_key or not bucket_name or not endpoint_url:
            raise AccessError('Please config oss key and secret')

        oss_auth = oss2.Auth(access_key_id, secret_key)

        bucket = oss2.Bucket(oss_auth, endpoint_url, bucket_name)

        return bucket

    def upload_file_to_oss(self, oss_client, file_name, bin_data):
        oss_client.put_object(file_name, bin_data)
        _logger.info({
            'oss upload': file_name
        })

    def get_file_mimetype(self, attach):
        mimetype = attach.mimetype
        return mimetype.split('/').pop()

    def get_today_file_name(self, filename):
        date_today = datetime.date.today()
        oss_file_name = str(date_today.strftime('%Y/%m/%d')) + '/' + filename
        oss_folder_root = self._get_oss_settings("oss.oss_folder_root", "OSS_FOLDER_ROOT")
        oss_folder_name = oss_folder_root if oss_folder_root else BUCKET_HEADER
        return oss_folder_name + oss_file_name

    def get_file_name(self, filename, checksum, mimetype=None):

        file_name = checksum + '/{}'.format(filename)
        today_file_name = self.get_today_file_name(file_name)
        return today_file_name

    def get_oss_config_state(self):
        oss_state = self.env["ir.config_parameter"].sudo().get_param("ir_attachment_url.storage")
        return oss_state

    def _set_where_to_store(self, vals_list):
        bucket = None
        try:
            bucket = self._get_oss_resource()
        except Exception as e:
            _logger.exception("Could not get oss bucket")

        if not bucket:
            return super(IrAttachment, self)._set_where_to_store(vals_list)

        # TODO: тут игнорируется s3 condition и соотвествующий bucket пишется везде
        for values in vals_list:
            values["_bucket"] = bucket

        return super(IrAttachment, self)._set_where_to_store(vals_list)

    def force_storage_oss(self):
        try:
            bucket = self._get_oss_resource()
        except Exception as e:
            _logger.error('发生错误')
            raise ValueError('发生错误! {}'.format(e))

        oss_condition = self._get_oss_settings("oss.oss_condition", "OSS_CONDITION")
        oss_condition = safe_eval(oss_condition, mode="eval")

        return self._force_storage_with_bucket(
            bucket,
            [
                ("type", "!=", "url"),
                ("id", "!=", 0),
                ("store_fname", "!=", False),
                ("res_model", "not in", ["ir.ui.view", "ir.ui.menu"]),
            ]
            + oss_condition,
        )

    def _inverse_datas(self):
        oss_state = self.get_oss_config_state()
        oss_enable_state = self._get_oss_settings('oss.enable_oss', 'OSS_ENABLE')
        if oss_state != "oss" or not oss_enable_state:
            return super(IrAttachment, self)._inverse_datas()

        oss_condition = self._get_oss_settings("oss.oss_condition", "OSS_CONDITION")

        if oss_condition and not self.env.context.get("force_oss"):
            oss_condition = safe_eval(oss_condition, mode="eval")
            oss_records = self.sudo().search([("id", "in", self.ids)] + oss_condition)
        else:
            # if there is no condition or force_oss in context
            # then store all attachments on oss
            oss_records = self

        if oss_records:

            oss_bucket = self._get_oss_resource()
            if not oss_bucket:
                _logger.info("something wrong on alicloud side, keep attachments as usual")
                oss_records = self.env[self._name]
            else:
                oss_records = oss_records._filter_protected_attachments()
                oss_records = oss_records.filtered(lambda r: r.type != 'url' and r.res_model is not False)
                oss_records._write_records_with_bucket(oss_bucket)

        return super(IrAttachment, self - oss_records)._inverse_datas()

    def _file_read(self, fname):
        try:
            oss_bucket = self._get_oss_resource()
            oss_bucket.get_object(self.fname)
        except Exception as e:
            return super()._file_read(fname)

    def _file_write_with_bucket(self, bucket, bin_data, filename, mimetype, checksum):
        # make sure, that given bucket is s3 bucket
        if not is_oss_bucket(bucket):
            return super(IrAttachment, self)._file_write_with_bucket(
                bucket, bin_data, filename, mimetype, checksum
            )
        fname = hashlib.sha1(bin_data).hexdigest()
        file_name = self.get_file_name(filename, fname, mimetype=mimetype)

        self.upload_file_to_oss(bucket, file_name, bin_data)

        obj_url = self._get_oss_object_url(bucket, file_name, timeout=60 * 60 * 24 * 30)
        return file_name, obj_url

    def _get_datas_related_values_with_bucket(self, bucket, data, filename, mimetype, checksum=None):
        bin_data = base64.b64decode(data) if data else b""
        if not checksum:
            checksum = self._compute_checksum(bin_data)
        fname, url = self._file_write_with_bucket(
            bucket, bin_data, filename, mimetype, checksum
        )
        return {
            "file_size": len(bin_data),
            "checksum": checksum,
            "index_content": self._index(bin_data, mimetype),
            "store_fname": fname,
            "db_datas": False,
            "type": "url",
            "url": url,
            "public": True,
            "oss_file_name": fname
        }

    def force_storage_oss2(self):
        try:
            oss_bucket = self._get_oss_resource()
        except Exception as e:
            return super().force_storage_oss2()

        oss_condition = self._get_oss_settings("oss.oss_condition", "OSS_CONDITION")

        return self._force_storage_with_bucket(
            oss_bucket,
            [
                ("type", "!=", "url"),
                ("id", "!=", 0),
                ("store_fname", "!=", False),
                ("res_model", "not in", ["ir.ui.view", "ir.ui.menu"]),
            ]
            + oss_condition,
        )
