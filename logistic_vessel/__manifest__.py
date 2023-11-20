{
    "name": "Logistic Vessel",
    "summary": """
        Logistic Vessel""",
    "author": "1di0t",
    "category": "web",
    "license": "AGPL-3",
    "depends": ["web", "sale", "stock", "sale_stock", "stock_account", "account"],
    "installable": True,
    'data': [
        'data/volume_digits.xml',
        'data/notify_template.xml',
        'data/delivery_note_template.xml',
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/freight_vessel_view.xml',
        'views/freight_port_view.xml',
        'views/stock_quant_package.xml',
        'views/stock_move.xml',
        'views/hide_menu.xml',
        'report/stock_quant_pending_report_view.xml',
        'wizard/stock_quant_stock_out_wizard.xml',
    ],
    "assets": {
        "web.assets_backend": [
        ],
        "web.assets_qweb": [
        ],
    },
}
