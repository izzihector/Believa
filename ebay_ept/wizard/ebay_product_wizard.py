from odoo import models, fields, api, _

class ebay_product_wizard(models.TransientModel):
    _name = 'ebay.product.wizard' 
    _description = "eBay Product Wizard"
    
    template_id = fields.Many2one('ebay.template.ept',string="Select Listing Template",help="Selected Template Configuration will be applied to the Listing Products")
    publish_in_ebay = fields.Boolean('Start Listing Immediately',help="Will Active Product Immediately on eBay")
    schedule_time = fields.Datetime('Scheduled Time',help="Time At which the product will be active on eBay")
    ending_reason = fields.Selection([('Incorrect','The start price or reserve price is incorrect'),('LostOrBroken','The item was lost or broken'),('NotAvailable','The item is no longer available for sale'),('OtherListingError','The listing contained an error'),('SellToHighBidder','The listing has qualifying bids')],'Ending Reason')
    
    @api.multi
    def update_payment_in_ebay(self):
        active_ids=self._context.get('active_ids')
        invoices=self.env['account.invoice'].search([('id','in',active_ids)])
        for invoice in invoices:
            invoice.update_payment_in_ebay()
        return True
    
    @api.multi
    def update_stock_in_ebay(self):
        ebay_instance_obj=self.env['ebay.instance.ept']
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        active_ids=self._context.get('active_ids',[])
        ebay_instances=ebay_instance_obj.search([('state','=','confirmed')])
        for instance in ebay_instances:
            ebay_products = ebay_product_product_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('exported_in_ebay','=',True)])
            if ebay_products:                               
                ebay_product_product_obj.export_stock_levels_ebay(instance,ebay_products)
                
    @api.multi                
    def update_price_in_ebay(self):
        ebay_instance_obj=self.env['ebay.instance.ept']
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        active_ids=self._context.get('active_ids',[])                                            
        ebay_instances=ebay_instance_obj.search([('state','=','confirmed')])
        for instance in ebay_instances:
            ebay_products = ebay_product_product_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('exported_in_ebay','=',True)])
            if ebay_products:                               
                ebay_product_product_obj.update_price(instance,ebay_products)
                
    @api.multi
    def export_product_in_ebay(self):
        self.ensure_one()
        if self.template_id.listing_type=='Chinese' and self.template_id.duration_id.name=='GTC':
            raise Warning("GTC is not allow if Listing Type is Chinese")
        
        ebay_log_book_obj = self.env['ebay.log.book']
        ebay_log_line_obj = self.env['ebay.transaction.line']
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']
        
        ebay_instance_obj=self.env['ebay.instance.ept']
        active_ids=self._context.get('active_ids',[])                                            
        ebay_instances=ebay_instance_obj.search([('state','=','confirmed')])
        ebay_error_sku_list = []
        job = False
        
        for instance in ebay_instances:
            ebay_product_templates = ebay_product_tmpl_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('exported_in_ebay','=',False)])            
            for ebay_product_template in ebay_product_templates:
                if ebay_product_template.product_type == 'individual' :
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
                                    'ebay_order_ref': list(ebay_error_sku_dict.keys()) and list(ebay_error_sku_dict.keys())[0] or '',
                                    'job_id': job.id,
                                    'log_type': 'error',
                                    'action_type': 'skip_line',
                                    'operation_type': 'export',
                                    'message': list(ebay_error_sku_dict.keys()) and ebay_error_sku_dict.get(list(ebay_error_sku_dict.keys())[0]) or '',
                                }
                ebay_log_line_obj.create(job_line_val)
        return True        

    @api.multi
    def update_product_in_ebay(self):
        self.ensure_one()
        
        if self.template_id.listing_type=='Chinese' and self.template_id.duration_id.name=='GTC':
            raise Warning("GTC is not allow if Listing Type is Chinese")
        
        ebay_log_book_obj = self.env['ebay.log.book']
        ebay_log_line_obj = self.env['ebay.transaction.line']
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']      
        ebay_instance_obj=self.env['ebay.instance.ept']
        
        active_ids=self._context.get('active_ids',[])                                            
        ebay_instances=ebay_instance_obj.search([('state','=','confirmed')])
        ebay_error_sku_list = []
        update_prod_flag = False
        job = False
        
        for instance in ebay_instances:
            ebay_product_templates = ebay_product_tmpl_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('exported_in_ebay','=',True)])            
            for ebay_product_template in ebay_product_templates:
                if ebay_product_template.product_type == 'individual' :
                    update_prod_flag,ebay_error_sku = ebay_product_tmpl_obj.update_individual_item(self.template_id,ebay_product_template,instance,self.publish_in_ebay,self.schedule_time)
                else:
                    update_prod_flag,ebay_error_sku = ebay_product_tmpl_obj.update_variation_item(self.template_id,ebay_product_template,instance,self.publish_in_ebay,self.schedule_time)
                if update_prod_flag and ebay_error_sku:
                    ebay_error_sku_list += ebay_error_sku
                    
        if ebay_error_sku_list:
            for i, ebay_error_sku_dict in enumerate(ebay_error_sku_list,1):
                if not job:
                    value = {
                                'message': 'Update Products in eBay Time Arrives Error.',
                                'application': 'update_products',
                                'operation_type': 'export',
                                'skip_process':True
                            }             
                    job = ebay_log_book_obj.create(value)
                job_line_val = {
                                    'res_id': i,
                                    'ebay_order_ref': list(ebay_error_sku_dict.keys())and list(ebay_error_sku_dict.keys())[0] or '',
                                    'job_id': job.id,
                                    'log_type': 'error',
                                    'action_type': 'skip_line',
                                    'operation_type': 'export',
                                    'message': list(ebay_error_sku_dict.keys()) and ebay_error_sku_dict.get(list(ebay_error_sku_dict.keys())[0]) or '',
                                }
                ebay_log_line_obj.create(job_line_val)
        return True            

    @api.multi
    def relist_product_in_ebay(self):
        self.ensure_one()
        if self.template_id.listing_type=='Chinese' and self.template_id.duration_id.name=='GTC':
            raise Warning("GTC is not allow if Listing Type is Chinese")
        
        ebay_log_book_obj = self.env['ebay.log.book']
        ebay_log_line_obj = self.env['ebay.transaction.line']
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']
        product_listing_obj = self.env['ebay.product.listing.ept']
        ebay_instance_obj=self.env['ebay.instance.ept']
        
        active_ids=self._context.get('active_ids',[])                                            
        ebay_instances=ebay_instance_obj.search([('state','=','confirmed')])
        ebay_error_sku_list = []
        relist_prod_flag = False
        job = False
        
        for instance in ebay_instances:
            ebay_product_templates = ebay_product_tmpl_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('exported_in_ebay','=',True)])            
            for ebay_product_template in ebay_product_templates:
                if ebay_product_template.product_type == 'individual':
                    for ebay_variant in ebay_product_template.ebay_variant_ids :
                        #Remove: ('ebay_template_id','=',self.template_id.id),
                        domain=[('instance_id','=',instance.id),
                                ('state','=','Ended'),
                                ('ebay_variant_id','=',ebay_variant.id)]
                        product_listing = product_listing_obj.search(domain,limit=1,order='id desc')
                        if product_listing:
                            relist_prod_flag,ebay_error_sku = ebay_product_tmpl_obj.relist_individual_products(self.template_id.listing_type,ebay_product_template,instance,product_listing,self.template_id)
                            if relist_prod_flag and ebay_error_sku:
                                ebay_error_sku_list += ebay_error_sku
                else:
                    #Remove: ('ebay_template_id','=',self.template_id.id),
                    domain=[('instance_id','=',instance.id),
                            ('state','=','Ended'),
                            ('ebay_product_tmpl_id','=',ebay_product_template.id)]
                    product_listing = product_listing_obj.search(domain,limit=1,order='id desc')
                    if product_listing:
                        relist_prod_flag,ebay_error_sku = ebay_product_tmpl_obj.relist_products(self.template_id.listing_type,ebay_product_template,instance,product_listing,self.template_id)
                        if relist_prod_flag and ebay_error_sku:
                                ebay_error_sku_list += ebay_error_sku
        if ebay_error_sku_list:
            for i, ebay_error_sku_dict in enumerate(ebay_error_sku_list,1):
                if not job:
                    value = {
                                'message': 'Relist Products in eBay Time Arrives Error.',
                                'application': 'relist_products',
                                'operation_type': 'export',
                                'skip_process':True
                            }          
                    job = ebay_log_book_obj.create(value)
                job_line_val = {
                                    'res_id': i,
                                    'ebay_order_ref': list(ebay_error_sku_dict.keys()) and list(ebay_error_sku_dict.keys())[0] or '',
                                    'job_id': job.id,
                                    'log_type': 'error',
                                    'action_type': 'skip_line',
                                    'operation_type': 'export',
                                    'message': list(ebay_error_sku_dict.keys()) and ebay_error_sku_dict.get(list(ebay_error_sku_dict.keys())[0]) or '',
                                }
                ebay_log_line_obj.create(job_line_val)
        return True
    
    @api.multi
    def cancel_product_listing_in_ebay(self):
        self.ensure_one()
        ebay_instance_obj = self.env['ebay.instance.ept']
        ebay_product_tmpl_obj = self.env['ebay.product.template.ept']
        
        active_ids = self._context.get('active_ids',[])
        ebay_instances = ebay_instance_obj.search([('state','=','confirmed')])
        for instance in ebay_instances:
            ebay_product_templates = ebay_product_tmpl_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('exported_in_ebay','=',True),('ebay_active_listing_id','!=',False)])
            for ebay_product_template in ebay_product_templates:
                if ebay_product_template.product_type == 'individual' :
                    ebay_product_tmpl_obj.cancel_individual_products_listing(ebay_product_template,instance,self.ending_reason)
                else:
                    ebay_product_tmpl_obj.cancel_products_listing(ebay_product_template,instance,ebay_product_template.ebay_active_listing_id,self.ending_reason)
        return True
    
    
    
    
    
    
    
    