# Copyright 2019 César Fernández Domínguez <cesfernandez@outlook.com>
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import zipfile
from io import BytesIO

from odoo import _, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def action_attachments_download(self):
        items = self.filtered(lambda x: x.type == "binary")
        if not items:
            raise UserError(
                _("None attachment selected. Only binary attachments allowed.")
            )
        ids = ",".join(map(str, items.ids))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/attachment/download_zip?ids=%s" % (ids),
            "target": "new",
        }

    def _create_temp_zip(self):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for att_index, attachment in enumerate(self):
                attachment.check("read")
                zip_file.writestr(
                    '{}-{}'.format(att_index, attachment._compute_zip_file_name()),
                    attachment.raw,
                )
            zip_buffer.seek(0)
            zip_file.close()
        return zip_buffer

    def correct_file_name(self):
        if not all([self.res_model, self.res_id, not self.res_field]):
            return self.name
        record_id = self.env[self.res_model].browse(self.res_id)
        if self.res_field and hasattr(record_id, '{}name'.format(self.res_field)):
            return getattr(record_id, '{}name'.format(self.res_field)) or self.name
        return self.name

    def _compute_zip_file_name(self):
        """Give a chance of easily changing the name of the file inside the ZIP."""
        self.ensure_one()
        return self.correct_file_name()
