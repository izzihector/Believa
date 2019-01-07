{
    # App information
    'name': 'eBay Odoo Connector',
    'version': '12.0',
    'category': 'Sales',
    'license': 'OPL-1',
    'summary' : 'Automate your vital business processes & eliminate the need for manual data entry at Odoo by bi-directional data exchange & integration between eBay & Odoo.',
    
    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',   
    'website': 'http://www.emiprotechnologies.com/',
    
    # Dependencies
    'depends': ['auto_invoice_workflow_ept','document','common_connector_library'], 

    # Views
    'data': [
        'view/account_view.xml',
        'view/product_template_view.xml',
        'view/product_product_view.xml',
        'view/readonly_bypass.xml',
        'security/res_groups.xml',
        'view/ebay_instance_ept_view.xml',
        'view/sale_workflow_config.xml',
        'report/sale_report_view.xml',
        'view/sale_order.xml',
        'view/stock_view.xml',
        'view/payment_option_view.xml',
        'view/res_config_view.xml',
        'view/ship_settings_view.xml',
        
        'view/ebay_product_ept.xml',
        'view/category.xml',
        'view/ebay_product_listing.xml',
        'view/ebay_template.xml',
        
        #'view/product_promotion.xml',
        'view/duration_data.xml',
        'view/buyer_requirement.xml',
        'view/ebay_refund_details.xml',
        'view/operations.xml',
        'security/ir.model.access.csv',
        'view/ebay_credential_wizard.xml',
        'view/ebay_product_wizard_view.xml',
        'view/ebay_process_job_log.xml',
        'view/stock_quant_package.xml',
        'view/ebay_cancel_order_wizard_view.xml',
        'view/ir_cron.xml',
        'view/delivery.xml',
        'view/duration.xml',
        'view/condition.xml',
        'view/account_invoice_view.xml',
        'data/sequence.xml',
        'view/ebay_product_image_view.xml',
        'view/web_templates.xml',
        'view/dashboard_operation_view.xml',
        #'data/ebay.operations.ept.csv',
        #'view/ebay_installer.xml',
        'view/ebay_description_template_view.xml',
        'view/ebay_feedback_wizard.xml',
        'view/ebay_feedback_ept.xml',
    ],
    
    # Odoo Store Specific
    'images': ['static/description/main_screen.jpg'],
    'live_test_url':'https://www.emiprotechnologies.com/free-trial?app=ebay-ept&version=12&edition=enterprise',
    
    'demo_xml': [],
    'installable': True,
    'auto_install': False,
    'application' : True,
    'active': False,
    'price': 479.00,
    'currency': 'EUR',
}

