#!/usr/bin/python3

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
#from odoo.addons.ebay_ept.ebaysdk.trading import Connection_multipart as trading_multipart
from  odoo.addons.ebay_ept.ebaysdk import config as Config


class ebay_process_import_export(models.TransientModel):
    _name="ebay.process.import.export"
    _description = "eBay Process Import Export"
     
    is_get_feedback = fields.Boolean('Get FeedBack')
    instance_ids = fields.Many2many("ebay.instance.ept",'ebay_instance_import_export_rel','process_id','instance_id',"Select Instances")
    
    is_import_category=fields.Boolean("Import Categories",default=False)
    is_import_store_category=fields.Boolean("Import Store Categories",default=False)
    is_import_product=fields.Boolean("Import Products",default=False)
    is_export_images=fields.Boolean("Export Images",default=False)
    level_limit=fields.Integer("Level Limit",default=0)
    only_leaf_categories=fields.Boolean("Only Leaf Categories",default=True)
    store_level_limit=fields.Integer("Store Level Limit",default=0)
    store_only_leaf_categories=fields.Boolean("Only Store Leaf Categories",default=True)
    get_use_preferences=fields.Boolean("GetUserPreferences",default=False)
    is_ebay_details=fields.Boolean("GeteBayDetails",default=False) 
    is_update_stock=fields.Boolean("Update Stock",default=False)
    is_update_price=fields.Boolean("Update Price",default=False)
    import_sales_orders=fields.Boolean("Import Sales Order",default=False)
    is_update_order_status=fields.Boolean("Update Order Status",default=False)
    from_date=fields.Date("From Date")
    to_date=fields.Date("To Date")
    is_export_product = fields.Boolean("Export Products",default=False)
    is_relist_product = fields.Boolean("Relist Products",default=False)
    template_id = fields.Many2one('ebay.template.ept',string="Template",help="Selected Template Configuration will be applied to the Listing Products")
    publish_in_ebay = fields.Boolean('Start Listing Immediately',help="Will Active Product Immediately on eBay")
    schedule_time = fields.Datetime('Scheduled Time',help="Time At which the product will be active on eBay")
    relist_template_id = fields.Many2one('ebay.template.ept',string="Relist Template",help="Selected Template Configuration will be applied to Relisting Products")
    max_name_levels = fields.Integer('Max Names Level', default=10, help="This field can be used if you want to limit the number of Item Specifics names that are returned for each eBay category. If you only wanted to retrieve the three most popular Item Specifics names per category, you would include this field and set its value to 3.")
    max_value_per_name = fields.Integer('Max Value Per Name', default=25, help="This field can be used if you want to limit the number of Item Specifics values (for each Item Specifics name) that are returned for each eBay category. If you only wanted to retrieve the 10 most popular Item Specifics values per Item Specifics name per category, you would include this field and set its value to 10.")
    is_import_get_item_condition = fields.Boolean('Get-Item Condition', default=False, help="Category wise import item condition.")
    is_create_auto_odoo_product = fields.Boolean("Auto Create Product ?", default=False, help="When you select this option to find the product in eBay erp & odoo erp if not get product so automatic create new product.")
    
    # Import Shipped Order
    is_import_shipped_order = fields.Boolean("Import Shipped Order",default=False,help="Import shipped order from the eBay.")
    shipped_order_from_date = fields.Datetime("Order From Date",help="Select import shipped order From Date.")
    shipped_order_to_date = fields.Datetime("Order To Date",help="Select import shipped order To Date")
    
    
    @api.model
    def default_get(self,fields):
        res = super(ebay_process_import_export,self).default_get(fields)
        if self._context and self._context.get('instance_ids') :
            res.update({'instance_ids':[(6,0,self._context.get('instance_ids'))]})
            return res        
        if 'instance_ids' in fields:
            instance_ids = self.env['ebay.instance.ept'].search([('state','=','confirmed')])
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
        api.execute('GeteBayDetails', {})
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
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        category_obj=self.env['ebay.category.master.ept']
        sale_order_obj=self.env['sale.order']
        ebay_product_listing_obj=self.env['ebay.product.listing.ept']
        ebay_site_policy_obj=self.env['ebay.site.policy.ept']
        ebay_feedback_obj=self.env['ebay.feedback.ept']
        
        if self.instance_ids:
            instances = self.instance_ids
        else:
            instances=self.env['ebay.instance.ept'].search([('state','=','confirmed')])
            
        if self.is_get_feedback:
            ebay_feedback_obj.get_feedback(instances)
            
        if self.is_import_category:
            category_obj.import_category(instances,self.level_limit,self.only_leaf_categories, self.is_import_get_item_condition)
        
        if self.is_import_store_category:
            category_obj.import_store_category(instances,self.store_level_limit,self.store_only_leaf_categories)            
        
        if self.is_import_product:
            from_date = self.from_date
            to_date = self.to_date
            date_range = []
            while True:
                to_date_tmp = from_date + relativedelta(days=119)
                if to_date_tmp > to_date :
                    date_range.append((datetime.strftime(from_date,DEFAULT_SERVER_DATE_FORMAT),datetime.strftime(to_date,DEFAULT_SERVER_DATE_FORMAT)))
                    break
                else :
                    date_range.append((datetime.strftime(from_date,DEFAULT_SERVER_DATE_FORMAT),datetime.strftime(to_date_tmp,DEFAULT_SERVER_DATE_FORMAT)))
                    from_date = to_date_tmp
            for instance in instances:
                for from_date,to_date in date_range :
                    ebay_product_listing_obj.sync_product_listings(instance,from_date,to_date,self.is_create_auto_odoo_product)
       
        if self.get_use_preferences:
            for instance in instances:
                ebay_site_policy_obj.sync_policies(instance)
        
        if self.is_ebay_details:
            for instance in instances:
                results=self.get_ebay_result(instance)
                results and self.update_ebay_result(instance, results)
                results=self.get_ebay_basic_result(instance)
                results and self.update_ebay_result(instance, results)                
        
        if self.is_update_stock:            
            for instance in instances:                               
                ebay_product_product_obj.export_stock_levels_ebay(instance)
        
        if self.is_update_price:
            for instance in instances:                               
                ebay_product_product_obj.update_price(instance)
        
        if self.import_sales_orders:
            for instance in instances:
                sale_order_obj.ebay_import_sales_order(instance,False)
        
        if self.is_update_order_status:
            for instance in instances:
                sale_order_obj.ebay_update_order_status(instance)
        
        if self.is_export_product :
            self.export_product()
        
        if self.is_relist_product:
            self.relist_product()
        
        ## Import shipped Order
        if self.is_import_shipped_order:
            for instance in instances:
                sale_order_obj.import_ebay_shipped_order(instance,self.shipped_order_from_date,self.shipped_order_to_date)
        return True
    
    @api.multi
    def relist_product(self):
        if self.instance_ids:
            instances=self.instance_ids
        else:
            instances=self.env['ebay.instance.ept'].search([])
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']
        product_listing_obj = self.env['ebay.product.listing.ept']
        for instance in instances :
            if instance.id != self.relist_template_id.instance_id.id :
                continue
            ebay_product_templates = ebay_product_tmpl_obj.search([('instance_id','=',instance.id),('exported_in_ebay','=',True)])            
            for ebay_product_template in ebay_product_templates:
                if ebay_product_template.product_type == 'individual':
                    for ebay_variant in ebay_product_template.ebay_variant_ids :
                        domain=[('instance_id','=',instance.id),
                                ('ebay_template_id','=',self.relist_template_id.id),
                                ('state','=','Ended'),
                                ('ebay_variant_id','=',ebay_variant.id)]
                        product_listing = product_listing_obj.search(domain,limit=1,order='id desc')
                        product_listing and ebay_product_tmpl_obj.relist_individual_products(self.relist_template_id.listing_type,ebay_product_template,instance,product_listing,self.relist_template_id)
                else:
                    domain=[('instance_id','=',instance.id),
                            ('ebay_template_id','=',self.relist_template_id.id),
                            ('state','=','Ended'),
                            ('ebay_product_tmpl_id','=',ebay_product_template.id)                  
                            ]
                    product_listing = product_listing_obj.search(domain,limit=1,order='id desc')
                    product_listing and ebay_product_tmpl_obj.relist_products(self.relist_template_id.listing_type,ebay_product_template,instance,product_listing,self.relist_template_id)
        return True
            
    @api.multi
    def export_product(self):
        ebay_log_book_obj = self.env['ebay.log.book']
        ebay_log_line_obj = self.env['ebay.transaction.line']
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']
        ebay_error_sku_list = []
        job = False
        
        instances = self.instance_ids if self.instance_ids else self.env['ebay.instance.ept'].search([])  
        for instance in instances :
            if instance.id != self.template_id.instance_id.id :
                continue
            ebay_product_templates = ebay_product_tmpl_obj.search([('instance_id','=',instance.id),('exported_in_ebay','=',False)])            
            for ebay_product_template in ebay_product_templates:
                if len(ebay_product_template.ebay_variant_ids.ids) == 1:
                    export_prod_flag,ebay_error_sku = ebay_product_tmpl_obj.create_individual_item(self.template_id,ebay_product_template,instance,self.publish_in_ebay,self.schedule_time)
                else:
                    export_prod_flag,ebay_error_sku = ebay_product_tmpl_obj.create_variation_item(self.template_id,ebay_product_template,instance,self.publish_in_ebay,self.schedule_time)
                if export_prod_flag and ebay_error_sku:
                        ebay_error_sku_list += ebay_error_sku
                        
        if ebay_error_sku_list:
            for i, ebay_error_sku_dict in enumerate(ebay_error_sku_list,1):
                if not job:
                    value = {
                                'message': 'Export Product in eBay Time Arrives Error.',
                                'application': 'export_products',
                                'operation_type': 'export',
                                'skip_process':True
                            }             
                    job = ebay_log_book_obj.create(value)
                job_line_val = {
                                    'res_id': i,
                                    'ebay_order_ref': list(ebay_error_sku_dict.keys())[0],
                                    'job_id': job.id,
                                    'log_type': 'error',
                                    'action_type': 'skip_line',
                                    'operation_type': 'export',
                                    'message': ebay_error_sku_dict.get(list(ebay_error_sku_dict.keys())[0]),
                                }
                ebay_log_line_obj.create(job_line_val)
        return True
    
    @api.multi
    def get_item_conditions(self):
        category_obj=self.env['ebay.category.master.ept']
        active_ids=self._context.get('active_ids')
        categs=category_obj.browse(active_ids)
        for categ in categs:            
            categ.get_item_conditions()
        return True
    
    @api.multi
    def get_attributes(self):
        category_obj=self.env['ebay.category.master.ept']
        active_ids=self._context.get('active_ids')
        categs=category_obj.browse(active_ids)
        """
            @note: Here we have added the validation on the users input
        """
        if self.max_name_levels and self.max_name_levels > 30 or self.max_name_levels < 1 : 
            raise Warning("Max Names Level has max value is 30 and min value is 1")
        if self.max_value_per_name and self.max_value_per_name > 2147483647 or self.max_value_per_name < 1 : 
            raise Warning("Max Value Per Name has max value is 2147483647 and min value is 1")
        for categ in categs :
            categ.get_attributes(self.max_name_levels, self.max_value_per_name)
        return True
        
    @api.multi
    def prepare_product_for_export(self):
        ebay_template_obj=self.env['ebay.product.template.ept']
        ebay_product_obj=self.env['ebay.product.product.ept']
        
        template_ids = self._context.get('active_ids',[])
        odoo_templates = self.env['product.template'].search([('id','in',template_ids),('type','!=','service')])
        for instance in self.instance_ids:
            for odoo_template in odoo_templates:
                ebay_template=ebay_template_obj.search([('instance_id','=',instance.id),('product_tmpl_id','=',odoo_template.id)])                
                if not ebay_template:
                    if len(odoo_template.product_variant_ids.ids) == 1 :
                        ebay_template=ebay_template_obj.create({'instance_id':instance.id,'product_tmpl_id':odoo_template.id,'name':odoo_template.name,'description':odoo_template.description_sale,'product_type' : 'individual','attribute_id':odoo_template.attribute_line_ids and odoo_template.attribute_line_ids[0].attribute_id.id or False})
                    else:
                        ebay_template=ebay_template_obj.create({'instance_id':instance.id,'product_tmpl_id':odoo_template.id,'name':odoo_template.name,'description':odoo_template.description_sale,'product_type' : 'variation','attribute_id':odoo_template.attribute_line_ids and odoo_template.attribute_line_ids[0].attribute_id.id or False})
                for variant in odoo_template.product_variant_ids:
                    ebay_variant=ebay_product_obj.search([('instance_id','=',instance.id),('product_id','=',variant.id)])
                    if not ebay_variant:
                        ebay_product_obj.create({'instance_id':instance.id,'product_id':variant.id,'ebay_product_tmpl_id':ebay_template.id,'ebay_sku':variant.default_code,'name':variant.name,})
        return True
