from openerp import models,fields,api
import time


class stock_inventory(models.Model):
    _inherit="stock.inventory"
    
    fba_live_stock_report_id = fields.Many2one('amazon.fba.live.stock.report.ept', "FBA Live Inventory Report")
    allow_validate_inventory=fields.Boolean("Allow Validate Inventory",default=False)
    @api.model
    def create_log(self, message, model_id, job, report_id, missing_value='', log_type='not_found'):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        amazon_transaction_log_obj.create({
                                   'model_id':model_id,
                                   'message':message,
                                   'res_id':report_id,
                                   'operation_type':'import',
                                   'job_id':job.id,
                                   'skip_record' : True,
                                   'log_type' : log_type,  
                                   'not_found_value' : missing_value or '',  
                                   'action_type' : 'skip_line',                                                    
       })
    
    @api.multi
    def _get_theoretical_qty(self, product,file_qty,location):
        location_obj = self.env['stock.location']        
        locations = location_obj.search([('id', 'child_of', [location])])
        domain = ' location_id in %s and product_id = %s'
        args = (tuple(locations.ids),(product.id,))
        vals = []
        flag = True                                 
        self._cr.execute('''
           SELECT product_id, sum(quantity) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
           FROM stock_quant WHERE''' + domain + '''
           GROUP BY product_id, location_id, lot_id, package_id, partner_id''', args)
        
        for product_line in self._cr.dictfetchall():            
            for key, value in product_line.items():
                if not value:
                    product_line[key] = False
            product_line['inventory_id'] = self.id
            product_line['theoretical_qty'] = product_line['product_qty']
            if flag:
                product_line['product_qty'] = file_qty
                flag = False
            else:
                product_line['product_qty'] = 0.0
            if product_line['product_id']:                
                product_line['product_uom_id'] = product.uom_id.id
            vals.append(product_line)            

        if not vals:
            if file_qty > 0.0:
                vals.append({'product_id':product.id,
                                       'inventory_id': self.id,
                                       'theoretical_qty': 0.0,
                                       'location_id':location,
                                       'product_qty':file_qty,
                                       'product_uom_id':product.uom_id.id,
                                       })            

        return vals
    
    @api.model
    def create_stock_inventory_from_amazon_live_report(self, sellable_line_dict,unsellable_line_dict, warehouse, inventory_report_id,seller = False,job=''):#,inv_mismatch_details_sellable,inv_mismatch_details_unsellable 
        sellable_products = []
        unsellable_products = []
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        amazon_live_stock_report_obj=self.env['amazon.fba.live.stock.report.ept']
        model_id=amazon_transaction_log_obj.get_model_id('amazon.fba.live.stock.report.ept')
        inventory_line_obj=self.env['stock.inventory.line']
        inventory_report=amazon_live_stock_report_obj.browse(inventory_report_id)
        
        if sellable_line_dict:
            name=inventory_report.name or "INV-HIST"
            inventory_name='Sellable_%s_%s'%(name,inventory_report.report_date)        
            
            inventory_vals = {
                              'name':inventory_name,
                              'fba_live_stock_report_id' : inventory_report_id,
                              'location_id':warehouse.lot_stock_id.id or False,
                              'date':time.strftime("%Y-%m-%d %H:%M:%S"),
                              'company_id':warehouse.company_id and warehouse.company_id.id or False,
                              'filter':'partial',
                              }
            inventory = self.create(inventory_vals)
            
            for product,product_qty in sellable_line_dict.items():
                if product.id in sellable_products:
                    continue            
                sellable_products.append(product.id)
                values = inventory._get_theoretical_qty(product,product_qty,warehouse.lot_stock_id.id)
                for product_line in values:
                    inventory_line_obj.create(product_line)            

            if inventory:
                try:        
                    inventory.action_start()
                    if seller:
                        instances=self.env['amazon.instance.ept'].search([('seller_id','=',seller.id)])
                    if instances[0].validate_stock_inventory_for_report:
                        inventory.action_done()   
                except Exception as e:
                    message = 'Error found while creating inventory %s.'%(str(e))
                    if not amazon_transaction_log_obj.search([('message','=',message),('manually_processed','=',False)]):
                        self.create_log(message, model_id, job, inventory_report_id, log_type='error') 
        
        if not warehouse.unsellable_location_id:
            message = 'unsellable location not found for warehouse %s.'%(warehouse.name)
            if not amazon_transaction_log_obj.search([('message','=',message),('manually_processed','=',False)]):
                self.create_log(message, model_id, job, inventory_report_id, missing_value=warehouse.name)
        else:    
            if unsellable_line_dict:  
                name=inventory_report.name or "INV-HIST"        
                unsellable_inventory_name='Unsellable_%s_%s'%(name,inventory_report.report_date)
                unsellable_inventory_vals={
                                  'name':unsellable_inventory_name,
                                  'fba_live_stock_report_id' : inventory_report_id,
                                  'location_id':warehouse.unsellable_location_id.id,
                                  'date':time.strftime("%Y-%m-%d %H:%M:%S"),
                                  'company_id':warehouse.company_id and warehouse.company_id.id or False,
                                  'filter':'partial',
                                  }
                unsellable_inventory=self.create(unsellable_inventory_vals)
                
                for product,product_qty in unsellable_line_dict.items():
                    if product.id in unsellable_products:
                        continue            
                    unsellable_products.append(product.id)
                    values = unsellable_inventory._get_theoretical_qty(product,product_qty,warehouse.unsellable_location_id.id)
                    for product_line in values:
                        inventory_line_obj.create(product_line) 
             
                if unsellable_inventory:        
                    try:
                        unsellable_inventory.action_start()    
                        if seller:
                            instances=self.env['amazon.instance.ept'].search([('seller_id','=',seller.id)])
                        if instances[0].validate_stock_inventory_for_report:
                            unsellable_inventory.action_done() 
                    except Exception as e:
                        message = 'Error found while creating inventory %s.'%(str(e))
                        if not amazon_transaction_log_obj.search([('message','=',message),('manually_processed','=',False)]):
                            self.create_log(message, model_id, job, inventory_report_id, log_type='error')                   
        if not job.transaction_log_ids:
            job.unlink()
        else:
            job and  job.write({'message' : 'Inventory adjustment process has been completed, open log to view products which are not processed due to any reason.'})        
        return True
    
    