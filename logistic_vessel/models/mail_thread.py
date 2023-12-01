# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.tools import is_html_empty
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context, get_lang, groupby
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """ Inherit the base settings to add a counter of failed email + configure
    the alias domain. """
    _inherit = 'res.config.settings'

    def open_email_layout(self):
        layout = self.env.ref('logistic_vessel.mail_notification_layout_inherit', raise_if_not_found=False)
        if not layout:
            raise UserError(_("This layout seems to no longer exist."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mail Layout'),
            'view_mode': 'form',
            'res_id': layout.id,
            'res_model': 'ir.ui.view',
        }


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_notify(self):
        if not self:
            return
        for activity in self:
            if activity.user_id.lang:
                # Send the notification in the assigned user's language
                activity = activity.with_context(lang=activity.user_id.lang)

            model_description = activity.env['ir.model']._get(activity.res_model).display_name
            body = activity.env['ir.qweb']._render(
                'mail.message_activity_assigned',
                {
                    'activity': activity,
                    'model_description': model_description,
                    'is_html_empty': is_html_empty,
                },
                minimal_qcontext=True
            )
            record = activity.env[activity.res_model].browse(activity.res_id)
            if activity.user_id:
                record.message_notify(
                    partner_ids=activity.user_id.partner_id.ids,
                    body=body,
                    record_name=activity.res_name,
                    model_description=model_description,
                    email_layout_xmlid='logistic_vessel.mail_notification_layout_inherit',
                    subject=_('"%(activity_name)s: %(summary)s" assigned to you',
                              activity_name=activity.res_name,
                              summary=activity.summary or activity.activity_type_id.name),
                    subtitles=[_('Activity: %s', activity.activity_type_id.name),
                               _('Deadline: %s', activity.date_deadline.strftime(get_lang(activity.env).date_format))]
                )


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_by_email_render_layout(self, message, recipients_group,
                                       msg_vals=False,
                                       render_values=None):
        """ Renders the email layout for a given recipients group which
        encapsulate the message body.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param dict recipients_group: a dict containing data for the recipients,
          see @ _notify_get_recipients_groups;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries;
        :param dict render_values: values to render the notification layout;

        At this point expected values are
          render_values: company, is_discussion, lang, message, model_description,
                         record, record_name, signature, subtype, tracking_values,
                         website_url
          recipients_group: actions, button_access, has_button_access, recipients

        :return str: rendered complete layout;
        """
        if render_values is None:
            render_values = {}

        email_layout_xmlid = msg_vals.get('email_layout_xmlid') if msg_vals else message.email_layout_xmlid
        template_xmlid = email_layout_xmlid if email_layout_xmlid else 'logistic_vessel.mail_notification_layout_inherit'
        render_values = {**render_values, **recipients_group}
        mail_body = self.env['ir.qweb']._render(
            template_xmlid,
            render_values,
            minimal_qcontext=True,
            raise_if_not_found=False,
            lang=render_values.get('lang', self.env.lang),
        )
        if not mail_body:
            _logger.warning(
                'QWeb template %s not found or is empty when sending notification emails. Sending without layouting.',
                template_xmlid)
            mail_body = message.body
        return mail_body

    def _message_auto_subscribe_notify(self, partner_ids, template):
        """ Notify new followers, using a template to render the content of the
        notification message. Notifications pushed are done using the standard
        notification mechanism in mail.thread. It is either inbox either email
        depending on the partner state: no user (email, customer), share user
        (email, customer) or classic user (notification_type)

        :param partner_ids: IDs of partner to notify;
        :param template: XML ID of template used for the notification;
        """
        if not self or self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        if not self.env.registry.ready:  # Don't send notification during install
            return

        for record in self:
            model_description = self.env['ir.model']._get(record._name).display_name
            company = record.company_id.sudo() if 'company_id' in record else self.env.company
            values = {
                'access_link': record._notify_get_action_link('view'),
                'company': company,
                'model_description': model_description,
                'object': record,
            }
            assignation_msg = self.env['ir.qweb']._render(template, values, minimal_qcontext=True)
            assignation_msg = self.env['mail.render.mixin']._replace_local_links(assignation_msg)
            record.message_notify(
                subject=_('You have been assigned to %s', record.display_name),
                body=assignation_msg,
                partner_ids=partner_ids,
                record_name=record.display_name,
                email_layout_xmlid='logistic_vessel.mail_notification_layout_inherit',
                model_description=model_description,
            )
