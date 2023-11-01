# Copyright 2019 Rafis Bikbov <https://it-projects.info/team/RafiZz>
# Copyright 2019 Alexandr Kolushov <https://it-projects.info/team/KolushovAlexandr>
# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
import base64
import hashlib
from odoo.tools.safe_eval import safe_eval
from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class OSSSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oss_folder_root = fields.Char(string='OSS folder root')
    oss_bucket = fields.Char(string="OSS bucket name", help="i.e. 'attachmentbucket'")
    oss_access_key_id = fields.Char(string="OSS access key id")
    oss_secret_key = fields.Char(string="OSS secret key")
    oss_endpoint_url = fields.Char(string="OSS endpoint url")
    oss_condition = fields.Char(string="OSS condition")
    enable_oss = fields.Boolean('Enable oss')

    @api.model
    def get_values(self):
        res = super(OSSSettings, self).get_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        oss_bucket = ICPSudo.get_param("oss.bucket", default="")
        oss_access_key_id = ICPSudo.get_param("oss.access_key_id", default="")
        oss_secret_key = ICPSudo.get_param("oss.secret_key", default="")
        oss_endpoint_url = ICPSudo.get_param("oss.endpoint_url", default="")
        oss_condition = ICPSudo.get_param("oss.oss_condition", default="")
        enable_oss = ICPSudo.get_param("oss.enable_oss", default="")
        oss_folder_root = ICPSudo.get_param("oss.oss_folder_root", default="")

        res.update(
            oss_bucket=oss_bucket,
            oss_access_key_id=oss_access_key_id,
            oss_secret_key=oss_secret_key,
            oss_endpoint_url=oss_endpoint_url,
            oss_condition=oss_condition,
            enable_oss=enable_oss,
            oss_folder_root=oss_folder_root,
        )
        return res

    def set_values(self):
        super(OSSSettings, self).set_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        ICPSudo.set_param("oss.bucket", self.oss_bucket or "")
        ICPSudo.set_param("oss.access_key_id", self.oss_access_key_id or "")
        ICPSudo.set_param("oss.secret_key", self.oss_secret_key or "")
        ICPSudo.set_param("oss.endpoint_url", self.oss_endpoint_url or "")
        ICPSudo.set_param("oss.oss_condition", self.oss_condition or "")
        ICPSudo.set_param("oss.enable_oss", self.enable_oss or "")
        ICPSudo.set_param("oss.oss_folder_root", self.oss_folder_root or "")

    def upload_file_to_oss(self, oss_client, file_name, bin_data):
        oss_client.put_object(file_name, bin_data)
        _logger.info({
            'oss upload': file_name
        })

    def upload_existing(self):
        oss_enable_state = self.env["ir.config_parameter"].sudo().get_param('oss.enable_oss')
        if not oss_enable_state:
            raise AccessError(_('Please enable oss first!'))

        oss_condition = self.oss_condition and safe_eval(self.oss_condition, mode="eval") or []
        domain = [("type", "!=", "url"), ("id", "!=", 0), ('res_model', '!=', False)] + oss_condition
        attachments = self.env["ir.attachment"].search(domain)
        attachments = attachments._filter_protected_attachments()

        attachment_obj = self.env["ir.attachment"]
        if attachments:

            oss = attachment_obj.get_oss_resource()

            if not oss:
                raise exceptions.MissingError('Error')

            for attach in attachments:
                value = attach.datas
                bin_data = base64.b64decode(value) if value else b""
                fname = hashlib.sha1(bin_data).hexdigest()

                file_name = attachment_obj.get_file_name(attach, fname)

                # oss.put_object(file_name, bin_data)
                self.upload_file_to_oss(oss, file_name, bin_data)

                vals = {
                    "file_size": len(bin_data),
                    "checksum": attach._compute_checksum(bin_data),
                    "index_content": attach._index(bin_data, attach.datas_fname, attach.mimetype),
                    "store_fname": fname,
                    "db_datas": False,
                    "type": "url",
                    "url": attach._get_oss_object_url(oss, file_name, 60 * 60 * 24),
                }
                attach.write(vals)
