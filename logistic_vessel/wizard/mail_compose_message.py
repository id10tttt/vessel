# -*- coding: utf-8 -*-
from odoo import models, api


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        if 'attachment_ids' in self._context:
            res['attachment_ids'] = self._context.get('attachment_ids')
        return res
