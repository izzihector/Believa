# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Amazon FBA Connector',
    'version': '12.0',
    'category': 'Sales',
    'summary' : 'Amazon Odoo Connector helps you integrate & manage your Amazon Seller Account operations from Odoo. Save time, efforts and avoid errors due to manual data entry to boost your Amazon sales with this connector.',
    'license': 'OPL-1',
    
    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com/',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    
    # Dependencies
    'depends': ['amazon_ept'],
    
    # Views
    'init_xml': [],
    'data': [
             'security/security.xml',
             'view/return_reason.xml',
             'view/inbound_shipment_plan.xml',
             'view/inbound_shipment.xml',
             'view/stock.xml',
             'view/outbound_order_wizard_view.xml',  
             'view/sale_order_view.xml',             
             'view/amazon_list_shipping_report_wizard.xml',
             'view/instance.xml',                                                  
             'view/prepare_product_wizard_view.xml',
             'view/stock_quant_package_view.xml',
             'view/ir_cron.xml',
             'view/res_config_view.xml',
             'view/inventory_wizard_view.xml',
             'view/process_import_export.xml',
             'view/stock_warehouse.xml',
             'view/inbound_shipment_labels_wizard.xml',
             'view/shipping_report.xml',
             'view/order_return_report.xml',
             'view/seller.xml',
             'view/product_ul.xml',
             'view/procurement_group.xml',
             'view/transaction.xml',
             'data/product_data.xml',
             'data/amazon_transaction_type.xml',
             'data/res_partner_data.xml',
             'data/fr_code.xml',
             'data/de_code.xml',
             'data/it_code.xml',
             'data/es_code.xml',
             'data/pl_code.xml',
             'data/uk_code.xml',
             'data/us_code.xml',
             'data/ca_code.xml',
             'security/ir.model.access.csv',
             'report/sale_report_view.xml',
             'view/import_product_inbound_shipment_wizard.xml',
             'view/account_invoice.xml',
             'view/settlement_report.xml',
             'view/amazon_file_job_inherite_view.xml',
             'view/amazon_live_stock_report_view.xml',
             'view/view_stock_inventory.xml',
             'view/stock_warehouse.xml',
             'data/prep.instruction.csv',
             'view/product_view.xml',
             'view/import_inbound_shipment_report_wizard_view.xml',
             'data/amazon_return_reason_data.xml',
             'view/order_return_config_view.xml',
             'view/amazon_fulfillment_res_country.xml'
        ],
   
    
    'demo_xml': [
    ],
    
    # Odoo Store Specific
    'images': ['static/description/main_screen.jpeg'],
    
    #Technical
    'active': True,
    'installable': True,
    'auto_install': False,
    'application' : True,
    'live_test_url':'https://www.emiprotechnologies.com/free-trial?app=amazon-fba-connector&version=12&edition=enterprise',
    'price': 450.00,
    'currency': 'EUR',
}
