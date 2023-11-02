{
    "name": """Ali cloud OSS""",
    "summary": """Ali cloud OSS""",
    "category": "Tools",
    "application": False,
    "author": "1di0t",
    "website": " ",
    "depends": ["base_setup", "ir_attachment_url"],
    "external_dependencies": {
        "python": ["oss2"],
        "bin": []
    },
    "data": [
        "data/ir_attachment_oss_data.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "auto_install": False,
    "installable": True,
    "license": "AGPL-3",
}
