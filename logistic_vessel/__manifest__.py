{
    "name": "Logistic Vessel",
    "summary": """
        Logistic Vessel""",
    "author": "1di0t",
    "category": "web",
    "license": "AGPL-3",
    "depends": ["web", "sale", "stock", "sale_stock"],
    "installable": True,
    'data': [
        'data/notify_template.xml',
        'data/delivery_note_template.xml',
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/freight_vessel_view.xml',
        'views/freight_port_view.xml',
        'views/stock_quant_package.xml',
    ],
    "assets": {
        "web.assets_backend": [
        ],
        "web.assets_qweb": [
        ],
    },
}
