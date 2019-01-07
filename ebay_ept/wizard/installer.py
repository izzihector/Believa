# -*- coding: utf-8 -*-
#!/usr/bin/python3
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from dateutil.relativedelta import relativedelta
import logging

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

from odoo.exceptions import Warning
from datetime import datetime

try:
    import simplejson as json
except ImportError:
    import json     # noqa

from odoo.release import serie
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

from odoo import models,fields,api,_

class ebay_instance_conf_installer(models.TransientModel):
    _name = 'ebay.instance.conf.installer'
    _inherit = 'res.config.installer'

    name = fields.Char("Instance Name")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    dev_id = fields.Char('Dev ID',size=256,help="Dev ID")
    app_id = fields.Char('App ID',size=256,help="App ID")
    cert_id = fields.Char('Cert ID',size=256,help="Cert ID")
    server_url = fields.Char('Server URL',size=256,help="eBay Server URL")
    environment = fields.Selection([('is_sandbox', 'Sandbox'),('is_production', 'Production')],'Environment')
    auth_token = fields.Text('Token',help="eBay Token")
    country_id = fields.Many2one('res.country',string = "Country")
    
    @api.onchange('environment')
    def onchange_environment(self):
        if self.environment == 'is_sandbox':
            self.server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            self.server_url = 'https://api.ebay.com/ws/api.dll'
    
    @api.multi
    def execute(self):
        self.env['ebay.instance.ept'].create({'name':self.name,
                                         'dev_id':self.dev_id,                                                 
                                         'app_id':self.app_id,
                                         'cert_id':self.cert_id,
                                         'server_url':self.server_url,
                                         'environment':self.environment,
                                         'auth_token':self.auth_token,
                                         'country_id':self.country_id.id,
                                         'warehouse_id':self.warehouse_id.id,
                                         })
        return super(ebay_instance_conf_installer, self).execute()

class ebay_instance_general_conf_installer(models.TransientModel):
    _name = 'ebay.instance.general.conf.installer'
    _inherit = 'res.config.installer'

    @api.model
    def _default_instance(self):
        instances = self.env['ebay.instance.ept'].search([])
        return instances and instances[0].id or False
        
    instance_id = fields.Many2one('ebay.instance.ept', 'Instance', default=_default_instance)
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse")
    partner_id = fields.Many2one('res.partner', string='Default Customer')
    country_id = fields.Many2one('res.country',string = "Country")
    lang_id = fields.Many2one('res.lang', string='Language')
    order_prefix = fields.Char(size=10, string='Order Prefix')    
    price_tax_included = fields.Boolean(string='Is Price Tax Included?')
    tax_id = fields.Many2one('account.tax', string='Default Sales Tax')
    
    order_auto_import = fields.Boolean(string='Auto Order Import?')    
    order_import_interval_number = fields.Integer('Import Order Interval Number',help="Repeat every x.")
    order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Order Interval Unit')
    order_import_next_execution = fields.Datetime('Next Execution', help='Next execution time')    
    
    order_auto_update=fields.Boolean(string="Auto Order Update ?")
    order_update_interval_number = fields.Integer('Update Order Interval Number',help="Repeat every x.")
    order_update_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit')               
    order_update_next_execution = fields.Datetime('Next Execution', help='Next execution time')    
    
    stock_auto_export=fields.Boolean(string="Stock Auto Export?")
    update_stock_interval_number = fields.Integer('Update Order Interval Number',help="Repeat every x.")
    update_stock_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit')
    update_stock_next_execution = fields.Datetime('Next Execution', help='Next execution time')    
    
    auto_update_payment=fields.Boolean(string="Auto Update Payment On invoice paid ?")
    ebay_default_product_category_id = fields.Many2one('product.category','Default Product Category')
    stock_field = fields.Many2one('ir.model.fields', string='Stock Field')
    pay_mthd = fields.Selection([('PayPal', 'PayPal'),('PaisaPay', 'PaisaPay')],'Payment Methods',help="Method of Payment")
    email_add = fields.Char('Email Address', size=126,help="Seller Email Address")
    site_id = fields.Many2one('ebay.site.details','Site')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')    
    shipment_charge_product_id=fields.Many2one("product.product","Shipment Fee",domain=[('type','=','service')])
    create_new_product=fields.Boolean("Auto Create New Product",default=False)
    create_quotation_without_product=fields.Boolean("Create Quotation Without Product",default=False)
    manage_multi_tracking_number_in_delivery_order=fields.Boolean("One order can have multiple Tracking Number ?",default=False)    
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    team_id=fields.Many2one('crm.team', 'Sales Team',oldname='section_id')
    post_code = fields.Char('Postal Code',size=64,help="Enter the Postal Code for Item Location")
    company_id=fields.Many2one('res.company',string="Company")
    discount_charge_product_id=fields.Many2one("product.product","Order Discount",domain=[('type','=','service')])
    ebay_plus=fields.Boolean("Is eBay Plus Account",default=False)
    order_import_user_id = fields.Many2one('res.users',string="User",help='User')
    order_status_update_user_id = fields.Many2one('res.users',string="User",help='User')
    stock_update_user_id = fields.Many2one('res.users',string="User",help='User')
    
    use_dynamic_desc = fields.Boolean("Use Dynamic Description Template", help='If ticked then you can able to use dynamic product description for an individual product only.')
    fetch_token_boolean = fields.Boolean(string='Fetch Token Boolean',related='instance_id.fetch_token_boolean', store=False)
    
    @api.onchange('instance_id')
    def onchange_instance_id(self):
        values = {} 
        context = dict(self._context or {})
        instance = self.instance_id or False
        self.price_tax_included= instance and instance.price_tax_included or False
        self.warehouse_id = instance and instance.warehouse_id and instance.warehouse_id.id or False
        self.lang_id = instance and instance.lang_id and instance.lang_id.id or False
        self.order_prefix = instance and instance.order_prefix and instance.order_prefix
        self.stock_field = instance and instance.stock_field and instance.stock_field.id or False
        self.pricelist_id = instance and instance.pricelist_id and instance.pricelist_id.id or False         
        self.fiscal_position_id = instance and instance.fiscal_position_id and instance.fiscal_position_id.id or False
        self.order_auto_import=instance and instance.order_auto_import
        self.stock_auto_export=instance and instance.stock_auto_export
        self.order_auto_update=instance and instance.order_auto_update
        self.ebay_default_product_category_id=instance and instance.ebay_default_product_category_id and instance.ebay_default_product_category_id.id or False
        self.pay_mthd=instance and instance.pay_mthd
        self.email_add=instance and instance.email_add
        self.site_id=instance and instance.site_id and instance.site_id.id or False        
        self.team_id=instance and instance.team_id and instance.team_id.id or False
        self.shipment_charge_product_id=instance and instance.shipment_charge_product_id and instance.shipment_charge_product_id.id or False
        self.post_code=instance and instance.post_code or False
        self.tax_id=instance and instance.tax_id and instance.tax_id.id or False
        self.create_new_product=instance and instance.create_new_product or False
        self.create_quotation_without_product=instance and instance.create_quotation_without_product or False
        self.company_id=instance and instance.company_id and instance.company_id.id or False
        self.manage_multi_tracking_number_in_delivery_order=instance and instance.manage_multi_tracking_number_in_delivery_order or False
        self.discount_charge_product_id=instance and instance.discount_charge_product_id and instance.discount_charge_product_id.id or False
        self.ebay_plus=instance and instance.ebay_plus or False
        self.auto_update_payment= instance and instance.auto_update_payment
        self.use_dynamic_desc=instance and instance.use_dynamic_desc or False
        try:
            inventory_cron_exist = instance and self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            inventory_cron_exist=False
        if inventory_cron_exist:
            self.update_stock_interval_number=inventory_cron_exist.interval_number or False
            self.update_stock_interval_type=inventory_cron_exist.interval_type or False
             
        try:
            order_import_cron_exist = instance and self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_import_cron_exist=False
        if order_import_cron_exist:
            self.order_import_interval_number = order_import_cron_exist.interval_number or False
            self.order_import_interval_type = order_import_cron_exist.interval_type or False
        try:
            order_update_cron_exist = instance and self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_update_cron_exist=False
        if order_update_cron_exist:
            self.order_update_interval_number= order_update_cron_exist.interval_number or False
            self.order_update_interval_type= order_update_cron_exist.interval_type or False
        
    @api.multi
    def execute(self):
        instance = self.instance_id
        values = {}
        if instance:
            values['warehouse_id'] = self.warehouse_id and self.warehouse_id.id or False
            values['lang_id'] = self.lang_id and self.lang_id.id or False
            values['order_prefix'] = self.order_prefix and self.order_prefix
            values['stock_field'] = self.stock_field and self.stock_field.id or False
            values['pricelist_id'] = self.pricelist_id and self.pricelist_id.id or False             
            values['fiscal_position_id'] = self.fiscal_position_id and self.fiscal_position_id.id or False
            values['order_auto_import']=self.order_auto_import
            values['stock_auto_export']=self.stock_auto_export
            values['create_new_product']=self.create_new_product or False
            values['create_quotation_without_product']=self.create_quotation_without_product or False
            values['order_auto_update']=self.order_auto_update
            values['ebay_default_product_category_id']=self.ebay_default_product_category_id and self.ebay_default_product_category_id.id or False
            values['pay_mthd']=self.pay_mthd
            values['email_add']=self.email_add
            values['site_id']=self.site_id and self.site_id.id or False            
            values['team_id']=self.team_id and self.team_id.id or False
            values['post_code']=self.post_code or False
            values['price_tax_included']=self.price_tax_included or False
            values['company_id']=self.company_id and self.company_id.id or False
            values['shipment_charge_product_id']=self.shipment_charge_product_id and self.shipment_charge_product_id.id or False
            values['manage_multi_tracking_number_in_delivery_order']=self.manage_multi_tracking_number_in_delivery_order or False
            values['discount_charge_product_id']=self.discount_charge_product_id and self.discount_charge_product_id.id or False
            values['ebay_plus']=self.ebay_plus or False
            values['tax_id']=self.tax_id and self.tax_id.id or False
            values['use_dynamic_desc']=self.use_dynamic_desc or False
            values['auto_update_payment']=self.auto_update_payment or False
            instance.write(values)
            instance.confirm()
            self.setup_order_import_cron(instance)
            self.setup_order_status_update_cron(instance)
            self.setup_update_stock_cron(instance)            
        return super(ebay_instance_general_conf_installer, self).execute()

    @api.multi   
    def setup_order_import_cron(self,instance):
        if self.order_auto_import:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.order_import_interval_type](self.order_import_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.order_import_interval_number,
                    'interval_type':self.order_import_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'args':"([{'instance_id':%d}])"%(instance.id),
                    'user_id': self.order_import_user_id and self.order_import_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True                                                                                                                
        
    @api.multi   
    def setup_order_status_update_cron(self,instance):
        if self.order_auto_update:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.order_update_interval_type](self.order_update_interval_number)
            vals = {'active' : True,
                    'interval_number':self.order_update_interval_number,
                    'interval_type':self.order_update_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'args':"([{'instance_id':%d}])"%(instance.id),
                    'user_id': self.order_status_update_user_id and self.order_status_update_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('ebay_ept.ir_cron_update_order_status')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_update_order_status_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_update_stock_cron(self,instance):
        if self.stock_auto_export:
            try:                
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.update_stock_interval_type](self.update_stock_interval_number)
            vals = {'active' : True,
                    'interval_number':self.update_stock_interval_number,
                    'interval_type':self.update_stock_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'args':"([{'instance_id':%d}])"%(instance.id),
                    'user_id': self.stock_update_user_id and self.stock_update_user_id.id}
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:                    
                    update_stock_cron = self.env.ref('ebay_ept.ir_cron_auto_export_inventory')
                except:
                    update_stock_cron=False
                if not update_stock_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_stock_cron.name
                vals.update({'name':name})
                new_cron = update_stock_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_auto_export_inventory_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True    

    @api.multi
    def modules_to_install(self):
        modules = super(ebay_instance_general_conf_installer, self).modules_to_install()
        return set([])
    
class ebay_get_ebay_detail_installer(models.TransientModel):
    _name = 'ebay.operation.installer'
    _inherit = 'res.config.installer'
    
    instance_ids = fields.Many2many("ebay.instance.ept",'ebay_instance_get_ebay_detail_rel','process_id','instance_id',"Instances")
    is_ebay_details=fields.Boolean("Get eBay Details",default=False)
    get_use_preferences=fields.Boolean("Get User Preferences",default=False)
    is_import_category=fields.Boolean("Import Categories",default=False)
    is_import_store_category=fields.Boolean("Import Store Categories",default=False)
    level_limit=fields.Integer("Level Limit",default=0)
    only_leaf_categories=fields.Boolean("Only Leaf Categories",default=True)
    store_level_limit=fields.Integer("Level Limit",default=0)
    store_only_leaf_categories=fields.Boolean("Only Leaf Categories",default=True)
    is_import_product=fields.Boolean("Sync Products",default=False)
    from_date=fields.Date("From Date")
    to_date=fields.Date("To Date")    
    import_sales_orders=fields.Boolean("Import Sales Order",default=False)
    
    @api.model
    def default_get(self,fields):
        res = super(ebay_get_ebay_detail_installer,self).default_get(fields)
        if 'instance_ids' in fields:
            instance_ids = self.env['ebay.instance.ept'].search([])
            res.update({'instance_ids':[(6,0,instance_ids.ids)]})
        return res

    @api.model
    def get_ebay_result(self,instance):
        api = instance.get_trading_api_object()
        para={}
        api.execute('GeteBayDetails', para)
        results = api.response.dict()                 
        return results
    
    @api.model
    def get_ebay_basic_result(self,instance):
        api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
        para={}
        api.execute('GeteBayDetails', para)
        results = api.response.dict()                 
        return results

    @api.model
    def update_ebay_result(self,instance,results):
        payment_option_obj=self.env['ebay.payment.options']
        site_details_obj=self.env['ebay.site.details']
        ebay_shipping_service_obj=self.env['ebay.shipping.service']
        shipping_locations_obj=self.env['ebay.shipping.locations']
        exclude_shipping_locations_obj=self.env['ebay.exclude.shipping.locations']
        refund_options_obj=self.env['ebay.refund.options']
        feedback_score_obj=self.env['ebay.feedback.score']

        payment_option_obj.get_payment_options(instance,results.get('PaymentOptionDetails',[]))
        site_details_obj.get_site_details(instance,results.get('SiteDetails',False))        
        refund_options_obj.create_refund_details(instance,results.get('ReturnPolicyDetails',{}))            
        feedback_score_obj.create_buyer_requirement(instance,results.get('BuyerRequirementDetails',{}))
        results_first_array = results.get('ShippingServiceDetails',[])
        results_second_array = results.get('ExcludeShippingLocationDetails',[])
        results_third_array = results.get('ShippingLocationDetails',[])
        
        ebay_shipping_service_obj.shipping_service_create(results_first_array,instance)
        exclude_shipping_locations_obj.create_exclude_shipping_locations(results_second_array,instance)
        shipping_locations_obj.create_shipping_locations(results_third_array,instance)                
        buyer_requirement=results.get('BuyerRequirementDetails',{})
        ship_to_register_country=buyer_requirement.get('ShipToRegistrationCountry',False)
        linked_paypal_account=buyer_requirement.get('LinkedPayPalAccount')
        ship_to_register_country=True if ship_to_register_country=='true' else False
        linked_paypal_account=True if linked_paypal_account=='true' else False
        instance.write({'is_paypal_account':linked_paypal_account,'is_primary_shipping_address':ship_to_register_country})
        return True
        
    @api.multi
    def execute(self):
        if self._context.get('get_ebay_detail',False) :
            if not self.is_ebay_details :
                raise Warning("You must need to select Get eBay Details in order to continue with the next step.")
        if self._context.get('get_user_preferences',False) :
            if not self.get_use_preferences :
                raise Warning("You must need to select Get User Preferences in order to continue with the next step or either you can skip this step.")
        if self._context.get('import_categories',False) :
            if not self.is_import_category :
                raise Warning("You must need to select Import Categories in order to continue with the next step or either you can skip this step.")
        if self._context.get('import_store_categories',False) :
            if not self.is_import_store_category :
                raise Warning("You must need to select Import Store Categories in order to continue with the next step or either you can skip this step.")
        if self._context.get('sync_active_products',False) :
            if not self.is_import_product :
                raise Warning("You must need to select Sync Products in order to continue with the next step or either you can skip this step.")
        if self._context.get('import_sale_order',False) :
            if not self.import_sales_orders :
                raise Warning("You must need to select Import Sales Order in order to finish with configuration process or either you can skip this and finished process.")                                    
#        self.execute_simple()
        return super(ebay_get_ebay_detail_installer, self).execute()

    @api.multi
    def execute_simple(self):
        if self.instance_ids:
            instances=self.instance_ids
        else:
            instances=self.env['ebay.instance.ept'].search([])
        ebay_site_policy_obj=self.env['ebay.site.policy.ept']
        category_obj=self.env['ebay.category.master.ept']
        ebay_product_listing_obj=self.env['ebay.product.listing.ept']
        sale_order_obj=self.env['sale.order']
        if self.is_ebay_details:
            for instance in instances:
                results=self.get_ebay_result(instance)
                results and self.update_ebay_result(instance, results)
                results=self.get_ebay_basic_result(instance)
                results and self.update_ebay_result(instance, results)
        if self.get_use_preferences:
            for instance in instances:
                ebay_site_policy_obj.sync_policies(instance)
        if self.is_import_category:
            category_obj.import_category(instances,self.level_limit,self.only_leaf_categories)
        if self.is_import_store_category:
            category_obj.import_store_category(instances,self.store_level_limit,self.store_only_leaf_categories)
        if self.is_import_product:
            from_date = datetime.strptime(self.from_date,"%Y-%m-%d").date()
            to_date = datetime.strptime(self.to_date,"%Y-%m-%d").date()
            delta = to_date - from_date
            if delta and delta.days > 120 :
                raise Warning("Time ranges must be a less than 120 days.")
            for instance in instances:
                ebay_product_listing_obj.sync_product_listings(instance,self.from_date,self.to_date)
        if self.import_sales_orders:
            for instance in instances:
                sale_order_obj.ebay_import_sales_order(instance,False)                                                          
        return True

    @api.multi
    def modules_to_install(self):
        modules = super(ebay_get_ebay_detail_installer, self).modules_to_install()
        return set([])
    
class ebay_payment_option_instance_conf_installer(models.TransientModel):
    _name = 'ebay.payment.option.instance.conf.installer'
    _inherit = 'res.config.installer'
    
    @api.model
    def _default_instance(self):
        instances = self.env['ebay.instance.ept'].search([])
        return instances and instances[0].id or False
    
    instance_id=fields.Many2one("ebay.instance.ept",string="Instance",required=True,default=_default_instance)
    payment_option_ids = fields.One2many("ebay.payment.option.conf.installer",'ebay_payment_option_wizard_id',string="Payment Options")

    @api.multi
    def execute(self):
        for payment_option in self.payment_option_ids :
            if payment_option.payment_option_id :
                payment_option.payment_option_id.write({
                                                    'auto_workflow_id' : payment_option.auto_workflow_id and payment_option.auto_workflow_id.id or False,
                                                    'payment_term_id' : payment_option.payment_term_id and payment_option.payment_term_id.id or False,
                                                    'update_payment_in_ebay' : payment_option.update_payment_in_ebay,})
        return super(ebay_payment_option_instance_conf_installer, self).execute()

    @api.onchange('instance_id')
    def onchange_instance(self):
        payment_option_obj = self.env['ebay.payment.options']
        payment_option_ids = []
        if self.instance_id :
            payment_options = payment_option_obj.search([('instance_id','=',self.instance_id.id)])
            for payment_option in payment_options :
                result= {}  
                result.update({'instance_id':payment_option.instance_id.id,
                               'detail_version' : payment_option.detail_version,
                               'description' : payment_option.description,
                               'auto_workflow_id' : payment_option.auto_workflow_id and payment_option.auto_workflow_id.id or False,
                               'payment_term_id' : payment_option.payment_term_id and payment_option.payment_term_id.id or False,
                               'update_payment_in_ebay' : payment_option.update_payment_in_ebay,
                               'payment_option_id' : payment_option.id})
                payment_option_ids.append(result)
        self.payment_option_ids = payment_option_ids
    
    @api.model
    def default_get(self, fields):
        res = super(ebay_payment_option_instance_conf_installer,self).default_get(fields)
        instances = self.env['ebay.instance.ept'].search([])
        if instances :
            payment_option_obj = self.env['ebay.payment.options']
            payment_options = payment_option_obj.search([('instance_id','=',instances[0].id)])
            payment_option_list = []
            for payment_option in payment_options :
                result= {}
                result.update({'instance_id':payment_option.instance_id.id,
                               'detail_version' : payment_option.detail_version,
                               'description' : payment_option.description,
                               'auto_workflow_id' : payment_option.auto_workflow_id and payment_option.auto_workflow_id.id or False,
                               'payment_term_id' : payment_option.payment_term_id and payment_option.payment_term_id.id or False,
                               'update_payment_in_ebay' : payment_option.update_payment_in_ebay,
                               'payment_option_id' : payment_option.id})
                payment_option_list.append((0, 0,result))
            res.update({'payment_option_ids' : payment_option_list})
        return res
        
class ebay_payment_option_conf_installer(models.TransientModel):
    _name = 'ebay.payment.option.conf.installer'
    
    instance_id=fields.Many2one("ebay.instance.ept",string="Instance",required=True)
#     name=fields.Char("PaymentOption")
    detail_version=fields.Char("DetailVersion")
    description=fields.Char("Description")
    auto_workflow_id=fields.Many2one("sale.workflow.process.ept","Auto Workflow")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')
    update_payment_in_ebay = fields.Boolean("Update Payment in eBay",default=False)  
    payment_option_id = fields.Many2one('ebay.payment.options','Payment Option')
    ebay_payment_option_wizard_id = fields.Many2one('ebay.payment.option.instance.conf.installer',string="Payment Option Wizard")  
