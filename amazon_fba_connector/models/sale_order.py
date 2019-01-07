from odoo import models,fields,api, _
import odoo.addons.decimal_precision as dp
from . import api as amazon_api #import OutboundShipments_Extend
import odoo
from datetime import timedelta,datetime
from odoo.addons.amazon_ept.amazon_emipro_api.mws import Orders,Feeds, Reports
from odoo.addons.amazon_ept.models.amazon_process_log_book import amazon_process_log_book, amazon_transaction_log
from odoo.exceptions import RedirectWarning,Warning
import time
    
class amazon_sale_order_ept(models.Model):
    _inherit="sale.order"
    
    full_fill_ment_order_help=""" 
        RECEIVED:The fulfillment order was received by Amazon Marketplace Web Service (Amazon MWS) and validated. 
            Validation includes determining that the destination address is valid and that Amazon's records indicate that 
            the seller has enough sellable (undamaged) inventory to fulfill the order.
             The seller can cancel a fulfillment order that has a status of RECEIVED
        INVALID:The fulfillment order was received by Amazon Marketplace Web Service (Amazon MWS) but could not be validated. 
                The reasons for this include an invalid destination address or Amazon's records indicating 
                that the seller does not have enough sellable inventory to fulfill the order. 
                When this happens, the fulfillment order is invalid and no items in the order will ship
        PLANNING:The fulfillment order has been sent to the Amazon Fulfillment Network to begin shipment planning,
                 but no unit in any shipment has been picked from inventory yet. 
                 The seller can cancel a fulfillment order that has a status of PLANNING
        PROCESSING:The process of picking units from inventory has begun on at least one shipment in the fulfillment order.
                 The seller cannot cancel a fulfillment order that has a status of PROCESSING
        CANCELLED:The fulfillment order has been cancelled by the seller.
        COMPLETE:All item quantities in the fulfillment order have been fulfilled.
        COMPLETE_PARTIALLED:Some item quantities in the fulfillment order were fulfilled; the rest were either cancelled or unfulfillable.
        UNFULFILLABLE: item quantities in the fulfillment order could be fulfilled because t
        he Amazon fulfillment center workers found no inventory 
        for those items or found no inventory that was in sellable (undamaged) condition.
    """
    
    help_fulfillment_action=""" 
        Ship - The fulfillment order ships now
        
        Hold - An order hold is put on the fulfillment order.3
        
        Default: Ship in Create Fulfillment
        Default: Hold in Update Fulfillment    
    """
    
    help_fulfillment_policy=""" 
    
        FillOrKill - If an item in a fulfillment order is determined to be unfulfillable before any shipment in the order moves 
                    to the Pending status (the process of picking units from inventory has begun), 
                    then the entire order is considered unfulfillable. However, if an item in a fulfillment order is determined 
                    to be unfulfillable after a shipment in the order moves to the Pending status, 
                    Amazon cancels as much of the fulfillment order as possible
                    
        FillAll - All fulfillable items in the fulfillment order are shipped. 
                The fulfillment order remains in a processing state until all items are either shipped by Amazon or cancelled by the seller
                
        FillAllAvailable - All fulfillable items in the fulfillment order are shipped. 
            All unfulfillable items in the order are cancelled by Amazon.
            
        Default: FillOrKill
    """
        
    amz_fulfillment_by = fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')
    amz_fulfillment_action=fields.Selection([('Ship','Ship'),('Hold','Hold')],string="Fulfillment Action",default="Hold",help=help_fulfillment_action)
    amz_displayable_date_time=fields.Date("Displayable Order Date Time",required=False,help="Display Date in package")
    amz_shipment_service_level_category = odoo.fields.Selection(selection_add=[('Priority','Priority'),('ScheduledDelivery','ScheduledDelivery')],help="ScheduledDelivery used only for japan")
    amz_fulfillment_policy=fields.Selection([('FillOrKill','FillOrKill'),('FillAll','FillAll'),('FillAllAvailable','FillAllAvailable')],string="Fulfillment Policy",default="FillOrKill",required=False,help=help_fulfillment_policy)
    amz_is_outbound_order=fields.Boolean("Out Bound Order",default=False)
    amz_delivery_start_time=fields.Datetime("Delivery Start Time",help="Delivery Estimated Start Time")
    amz_delivery_end_time=fields.Datetime("Delivery End Time",help="Delivery Estimated End Time")
    exported_in_amazon=fields.Boolean("Exported In Amazon",default=False)
    notify_by_email=fields.Boolean("Notify By Email",default=False,help="If true then system will notify by email to followers")
    amz_fulfullment_order_status=fields.Selection([('RECEIVED','RECEIVED'),('INVALID','INVALID'),('PLANNING','PLANNING'),
                                               ('PROCESSING','PROCESSING'),('CANCELLED','CANCELLED'),('COMPLETE','COMPLETE'),
                                               ('COMPLETE_PARTIALLED','COMPLETE_PARTIALLED'),('UNFULFILLABLE','UNFULFILLABLE')],string="Fulfillment Order Status",help=full_fill_ment_order_help)
    
    amz_shipment_report_id=fields.Many2one('shipping.report.request.history',"Shipment Report")
    @api.one
    @api.constrains('amz_fulfillment_action')
    def check_fulfillment_action(self):
        for record in self:
            if record.exported_in_amazon and record.amz_fulfillment_action=='Hold':
                raise Warning("You can change action Ship to Hold Which are already exported in amazon")
    
    
    @api.multi
    def _check_is_fba_warhouse(self):
        for record in self:
            if record.warehouse_id.is_fba_warehouse:
                record.order_has_fba_warehouse = True
            else:
                record.order_has_fba_warehouse = False
     
    order_has_fba_warehouse=fields.Boolean("Order Has FBA Warehouse",compute="_check_is_fba_warhouse",store=False)
    
    
    #This Function will create wizard for creating outbound shiipment (For 1 record only)
    @api.multi
    def create_outbound_shipment(self):
        amazon_outbound_order_wizard_obj=self.env['amazon.outbound.order.wizard']
        created_id = amazon_outbound_order_wizard_obj.with_context({'active_model': self._name,'active_ids': self.ids,'active_id': self.id or False}).create({'sale_order_ids':[(6,0,[self.id])]})
        return amazon_outbound_order_wizard_obj.wizard_view(created_id)
    
    
    @api.multi    
    def action_cancel(self):
        for order in self:
            instance=order.amz_instance_id            
            if order.amz_is_outbound_order:
                if order.amz_fulfullment_order_status in ['PROCESSING','COMPLETE','COMPLETE_PARTIALLED']:
                    raise Warning("You cannot cancel a fulfillment order with a status of Processing, Complete, or CompletePartialled")
                try:
                    proxy_data=instance.seller_id.get_proxy_server()
                    mws_obj=amazon_api.OutboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code,proxies=proxy_data)
                    mws_obj.CancelFulfillmentOrder(order)
                except Exception as e:
                    if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                        error = mws_obj.parsed_response_error.parsed or {}
                        error_value = error.get('Message',{}).get('value')
                        error_value = error_value if error_value else str(mws_obj.response.content)  
                    else:
                        error_value = str(e)
                    raise Warning(error_value)                    
                    
                #order.sale_order_id.action_cancel()
        res = super(amazon_sale_order_ept,self).action_cancel()                
        return res
                
    @api.multi
    def action_button_confirm(self):
        for order in self:
            if order.amz_is_outbound_order:
                if order.amz_fulfillment_action!='Ship':
                    raise Warning("Set Fulfillment Action To Ship Otherwise you are not allow to confirm this order")
#             order.action_button_confirm()
        super(amazon_sale_order_ept,self).action_button_confirm()
        return True
    
    """This Function Cancel Orders into ERP System"""
    @api.multi
    def cancel_draft_sales_order(self,seller,list_of_wrapper,mws_obj):
        instance_obj = self.env['amazon.instance.ept']
        for wrapper_obj in list_of_wrapper:
            orders=[]
            if not isinstance(wrapper_obj.parsed.get('Orders',{}).get('Order',[]),list):
                orders.append(wrapper_obj.parsed.get('Orders',{}).get('Order',{})) 
            else:
                orders=wrapper_obj.parsed.get('Orders',{}).get('Order',[])               
            transaction_log_lines = []
            skip_order = False
            marketplace_instance_dict={}
            for order in orders:
                order_status = order.get('OrderStatus',{}).get('value','')
                if order_status != 'Canceled':
                    continue

                amazon_order_ref = order.get('AmazonOrderId',{}).get('value',False)
                if not amazon_order_ref:
                    continue

                marketplace_id = order.get('MarketplaceId',{}).get('value',False)
                instance=marketplace_instance_dict.get(marketplace_id)
                if not instance:
                    instance = instance_obj.search([('marketplace_id.market_place_id','=',marketplace_id),('seller_id','=',seller.id)])
                    marketplace_instance_dict.update({marketplace_id:instance})
                
                existing_order = self.search([('amazon_reference','=',amazon_order_ref),('amz_instance_id','=',instance.id),('state','!=','cancel')])
                if existing_order:
                    if existing_order.state != 'draft' and existing_order.state != 'cancel':
                        ### Create log to notify to user that order has been processed in odoo but in amazon it's cancel
                        log_message = 'Sale order %s not in draft state, only draft order can be cancelled.'%(existing_order.name)
                        skip_order = True
                        log_line_vals = {
                             'model_id' : self.env['amazon.transaction.log'].get_model_id('sale.order'),
                             'res_id' : existing_order.id or 0,
                             'log_type' : 'not_found',
                             'action_type' : 'skip_line',
                             'not_found_value' : existing_order.name,
                             'user_id' : self.env.uid,
                             'skip_record' : skip_order,
                             'amazon_order_reference':amazon_order_ref,
                             'message' : log_message,
                             }
                        transaction_log_lines.append((0,0,log_line_vals))
                    else:
#                         existing_order.action_cancel()
                        super(amazon_sale_order_ept,existing_order).action_cancel()
            if skip_order and transaction_log_lines:   
                job_log_vals = {
                                'transaction_log_ids' : transaction_log_lines,
                                'skip_process' : skip_order,
                                'application' : 'sales',
                                'operation_type' : 'import',
                                'message' : "Cancelled orders process has not been completed successfully, due to cancelled amazon orders processed in odoo.",
                                }
                self.env['amazon.process.log.book'].create(job_log_vals)  
        return True 

    """Check Status of draft order in Amazon and if it is cancel, then cancel that order in Odoo"""
    @api.multi
    def check_cancel_order_in_amazon(self,seller,marketplaceids=[], instance_ids = []):
        """Create Object for the integrate with amazon"""
        proxy_data=seller.get_proxy_server()
        mws_obj = Orders(access_key=str(seller.access_key),secret_key=str(seller.secret_key),account_id=str(seller.merchant_id),region=seller.country_id.amazon_marketplace_code or seller.country_id.code,proxies=proxy_data)        
        """If Last FBA Sync Time is define then system will take those orders which are created after last import time 
          Otherwise System will take last 30 days orders
        """
        auto_process=self._context.get('auto_process',False)
        domain = [('state','=','draft')]
        if instance_ids:
            domain.append(('amz_instance_id','in',instance_ids))
            
        min_draft_order = self.search(domain, limit=1, order='date_order')
        max_draft_order = self.search(domain, limit=1, order='date_order desc')
        
        if not min_draft_order or not max_draft_order:
            if auto_process:
                return []
            else:
                raise Warning("No draft order found in odoo")
        
        min_date = datetime.strptime(str(min_draft_order.date_order), "%Y-%m-%d %H:%M:%S")
        max_date = datetime.strptime(str(max_draft_order.date_order), "%Y-%m-%d %H:%M:%S")
        date_ranges={}
        date_from=min_date
        while date_from < max_date or date_from < datetime.now():
            date_to = date_from + timedelta(days=30)
            if date_to > max_date:
                date_to=max_date
            if date_to > datetime.now():
                date_to = datetime.now()
            date_ranges.update({date_from : date_to})
            date_from = date_from+timedelta(days=31)
        
        list_of_wrapper=[]
        for from_date,to_date in list(date_ranges.items()):
            min_date_str = from_date.strftime("%Y-%m-%dT%H:%M:%S")
            created_after = min_date_str+'Z'
            
            max_date_str = to_date.strftime("%Y-%m-%dT%H:%M:%S")
            created_before = max_date_str+'Z'
            
            if not marketplaceids:
                instances = self.env['amazon.instance.ept'].search([('seller_id','=',seller.id)])
                marketplaceids = tuple([x.market_place_id for x in instances])
            if not marketplaceids:
                if auto_process:
                    raise Warning("There is no any instance is configured of seller %s"%(seller.name))
                else:
                    return []
            """Call List Order Method Of Amazon API for the Read Orders and API give response in DictWrapper"""
            while True:
                try:
                    result = mws_obj.list_orders(marketplaceids=marketplaceids,created_after=created_after,created_before=created_before,orderstatus=('Canceled',),fulfillment_channels=('AFN',))
                    amazon_order_list = self.cancel_draft_sales_order(seller,[result],mws_obj)
                    self._cr.commit()
                    time.sleep(1)
                    break
                except Exception as e:
                    if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                        error = mws_obj.parsed_response_error.parsed or {}
                        error_value = error.get('Message',{}).get('value')
                        error_value = error_value if error_value else str(mws_obj.response.content)  
                    else:
                        error_value = str(e)
                    if error_value!='Request is throttled':
                        raise Warning(error_value)
                    time.sleep(2)
            list_of_wrapper.append(result)
            next_token=result.parsed.get('NextToken',{}).get('value')
    
            while next_token:
                try:
                    result=mws_obj.list_orders_by_next_token(next_token)
                    amazon_order_list = self.cancel_draft_sales_order(seller,[result],mws_obj)
                    self._cr.commit()
                    time.sleep(1)
                except Exception as e:
                    if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                        error = mws_obj.parsed_response_error.parsed or {}
                        error_value = error.get('Message',{}).get('value')
                        error_value = error_value if error_value else str(mws_obj.response.content)  
                    else:
                        error_value = str(e)
                    if error_value!='Request is throttled':
                        raise Warning(error_value)
                    else:
                        time.sleep(1)                
                        continue
                next_token=result.parsed.get('NextToken',{}).get('value')
                list_of_wrapper.append(result)            
        """We have create list of Dictwrapper now we create orders into system"""             
        #amazon_order_list = self.cancel_draft_sales_order(seller,list_of_wrapper,mws_obj)
        return amazon_order_list    
    
    
    """Import FBA Pending Sales Order From Amazon"""
    @api.multi
    def import_fba_pending_sales_order(self,seller,marketplaceids=[]):
        """Create Object for the integrate with amazon"""
        proxy_data=seller.get_proxy_server()
        mws_obj = Orders(access_key=str(seller.access_key),secret_key=str(seller.secret_key),account_id=str(seller.merchant_id),region=seller.country_id.amazon_marketplace_code or seller.country_id.code,proxies=proxy_data)        
        """If Last FBA Sync Time is define then system will take those orders which are created after last import time 
          Otherwise System will take last 30 days orders
        """
        today = datetime.now()
        earlier = today - timedelta(days=30)
        earlier_str = earlier.strftime("%Y-%m-%dT%H:%M:%S")
        created_after = earlier_str+'Z'
        created_before =''
        if not marketplaceids:
            instances = self.env['amazon.instance.ept'].search([('seller_id','=',seller.id)])
            marketplaceids = tuple([x.market_place_id for x in instances])
        if not marketplaceids:
            raise Warning("There is no any instance is configured of seller %s"%(seller.name))
            
        """Call List Order Method Of Amazon API for the Read Orders and API give response in DictWrapper"""
        while True:
            try:
                result = mws_obj.list_orders(marketplaceids=marketplaceids,created_after=created_after,created_before=created_before,orderstatus=('Pending',),fulfillment_channels=('AFN',))
                time.sleep(1)
                break
            except Exception as e:
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)
                if error_value!='Request is throttled':
                    raise Warning(error_value)
                time.sleep(2)
        amazon_order_list=[]
#         list_of_wrapper.append(result)
        amazon_order_list = amazon_order_list + self.create_pending_sales_order(seller,[result],mws_obj)
        self._cr.commit()
        next_token=result.parsed.get('NextToken',{}).get('value')
        """We have create list of Dictwrapper now we create orders into system"""          
       
        while next_token:
            try:
                result=mws_obj.list_orders_by_next_token(next_token)
                time.sleep(1)
            except Exception as e:
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)    
                if error_value!='Request is throttled':
                    raise Warning(error_value)
                else:
                    time.sleep(1)                
                    continue
            next_token=result.parsed.get('NextToken',{}).get('value')               
            amazon_order_list =amazon_order_list +  self.create_pending_sales_order(seller,[result],mws_obj)
            self._cr.commit()
        return amazon_order_list

    """This Function Create Orders with Draft state into ERP System"""
    @api.multi
    def create_pending_sales_order(self,seller,list_of_wrapper,mws_obj):
        sale_order_line_obj=self.env['sale.order.line']
        instance_obj = self.env['amazon.instance.ept']
        amazon_order_list = []
        amazon_product_obj=self.env['amazon.product.ept']
        marketplace_instance_dict={}
        for wrapper_obj in list_of_wrapper:
            orders=[]
            if not isinstance(wrapper_obj.parsed.get('Orders',{}).get('Order',[]),list):
                orders.append(wrapper_obj.parsed.get('Orders',{}).get('Order',{})) 
            else:
                orders=wrapper_obj.parsed.get('Orders',{}).get('Order',[])
                               
            for order in orders:
                amazon_order_ref = order.get('AmazonOrderId',{}).get('value',False)
                if not amazon_order_ref:
                    break
                    continue
                
                marketplace_id = order.get('MarketplaceId',{}).get('value',False)
                instance=marketplace_instance_dict.get(marketplace_id)
                if not instance:
                    instance = instance_obj.search([('marketplace_id.market_place_id','=',marketplace_id),('seller_id','=',seller.id)])
                    marketplace_instance_dict.update({marketplace_id:instance})
                if not instance:
                    continue
                existing_order = self.search([('amazon_reference','=',amazon_order_ref),('amz_instance_id','=',instance.id)])
                if existing_order:
                    continue
                
                """Changes by Dhruvi 
                    default_fba_partner_id fetched according to seller wise"""
                partner_dict = {'invoice_address':instance.seller_id.def_fba_partner_id and instance.seller_id.def_fba_partner_id.id,'delivery_address':instance.seller_id.def_fba_partner_id and instance.seller_id.def_fba_partner_id.id,'pricelist_id':instance.pricelist_id and instance.pricelist_id.id}
                
                while True:
                    try:
                        result=mws_obj.list_order_items(amazon_order_ref)
                        time.sleep(1)
                        break
                    except Exception as e:
                        if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                            error = mws_obj.parsed_response_error.parsed or {}
                            error_value = error.get('Message',{}).get('value')
                            error_value = error_value if error_value else str(mws_obj.response.content)  
                        else:
                            error_value = str(e)
                        if error_value!='Request is throttled':
                            raise Warning(error_value)
                        time.sleep(2)                    

                list_of_orderlines_wrapper=[]
                list_of_orderlines_wrapper.append(result)
                next_token=result.parsed.get('NextToken',{}).get('value')
                while next_token:
                    try:
                        result=mws_obj.list_order_items_by_next_token(next_token)
                        time.sleep(1)
                    except Exception as e:
                        if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                            error = mws_obj.parsed_response_error.parsed or {}
                            error_value = error.get('Message',{}).get('value')
                            error_value = error_value if error_value else str(mws_obj.response.content)  
                        else:
                            error_value = str(e)
                        if error_value!='Request is throttled':
                            raise Warning(error_value)
                        else:
                            time.sleep(1)                
                            continue
                    next_token=result.parsed.get('NextToken',{}).get('value')
                    list_of_orderlines_wrapper.append(result)         
                
                amazon_order = False
                skip_order = False 
                message = ''
                log_message = ''
                log_action_type = 'skip_line'   
                for order_line_wrapper_obj in list_of_orderlines_wrapper:
                    order_lines=[]
                    skip_order = False
                    if not isinstance(order_line_wrapper_obj.parsed.get('OrderItems',{}).get('OrderItem',[]),list):
                        order_lines.append(order_line_wrapper_obj.parsed.get('OrderItems',{}).get('OrderItem',{}))
                    else:
                        order_lines=order_line_wrapper_obj.parsed.get('OrderItems',{}).get('OrderItem',[])

                    message = ''
                    log_message = ''
                    res_id = False
                    model_name = 'amazon.product.ept'
                    transaction_log_lines = []
                    for order_line in order_lines:
                        seller_sku=order_line.get('SellerSKU',{}).get('value',False)
                        domain = [('instance_id','=',instance.id)]
                        seller_sku and domain.append(('seller_sku','=',seller_sku))
                        amazon_product = amazon_product_obj.search_amazon_product(instance.id,seller_sku,'AFN')

                        if not amazon_product:
                            erp_product=amazon_product_obj.search_product(seller_sku)
                            """
                                If odoo product founds and amazon product not found then no need to check anything 
                                and create new amazon product and create log for that, if odoo product not found then 
                                go to check configuration which action has to be taken for that.
                                
                                There are following situations managed by code. 
                                In any situation log that event and action.
                                
                                1). Amazon product and odoo product not found
                                    => Check seller configuration if allow to create new product then create product.
                                    => Enter log details with action.
                                2). Amazon product not found but odoo product is there.
                                    => Created amazon product with log and action.
                            """
                            product_id = False            
                            if erp_product:
                                product_id = erp_product.id
                                log_action_type = 'create'
                                message = 'Order is imported with creating new amazon product.'
                                log_message = 'Odoo Product is already exists. System have created new Amazon Product %s for %s instance'%(seller_sku, instance.name )
                                #log_message = 'Product %s created in amazon->Products->Products for %s instance. Product already exist in Odoo and Amazon.'%(seller_sku, instance.name )
                            elif not seller.create_new_product:
                                skip_order = True
                                message = 'Order is not imported due to product not found issue.'
                                log_action_type = 'skip_line'
                                log_message = 'Product %s not found for %s instance'%(seller_sku, instance.name )
                            else:
                                log_action_type = 'create'
                                message = 'Order is imported with creating new odoo product.'
                                log_message = 'System have created new Odoo Product %s for %s instance'%(seller_sku, instance.name )
                                #log_message = 'Product %s created in odoo for %s instance'%(seller_sku, instance.name )
                            
                            if not skip_order:
                                sku = seller_sku or ( erp_product and erp_product[0].default_code) or False
                                prod_vals={
                                      'instance_id': instance.id,
                                      'product_asin': order_line.get('ASIN',{}).get('value',False),
                                      'seller_sku': sku,
                                      'type': erp_product and erp_product[0].type or 'product', 
                                      'product_id': product_id,             
                                      'purchase_ok' : True,
                                      'sale_ok' : True,    
                                      'exported_to_amazon': True,
                                      'fulfillment_by' : "AFN",          
                                      }
                                if not erp_product:
                                    prod_vals.update({'name':order_line.get('Title',{}).get('value'),'default_code':sku})
                            
                                amazon_product = amazon_product_obj.create(prod_vals)
                                if not erp_product:
                                    res_id = amazon_product and amazon_product.product_id.id or False
                                    model_name = 'product.product'
                                else:
                                    res_id = amazon_product and amazon_product.id or False
                                
                            log_line_vals = {
                                             'model_id' : self.env['amazon.transaction.log'].get_model_id(model_name),
                                             'res_id' : res_id or 0,
                                             'log_type' : 'not_found',
                                             'action_type' : log_action_type,
                                             'not_found_value' : seller_sku,
                                             'user_id' : self.env.uid,
                                             'skip_record' : skip_order,
                                             'amazon_order_reference':amazon_order_ref,
                                             'message' : log_message,
                                             }
                            transaction_log_lines.append((0,0,log_line_vals))  
                    
                    if not skip_order:
                        if not amazon_order:
                            order_vals=self.create_sales_order_vals(partner_dict,order,instance)
                            amazon_order = self.create(order_vals)
                            amazon_order_list.append(amazon_order)
                            
                        for order_line in order_lines:                        
                            sale_order_line_obj.create_sale_order_line(order_line,instance,amazon_order,False)  
                            
                    if skip_order or log_action_type == 'create':   
                        job_log_vals = {
                                        'transaction_log_ids' : transaction_log_lines,
                                        'skip_process' : skip_order,
                                        'application' : 'sales',
                                        'operation_type' : 'import',
                                        'message' : message,
                                        'instance_id':instance.id
                                        }
                        self.env['amazon.process.log.book'].create(job_log_vals)                    
        return amazon_order_list    
    
    
    @api.multi
    def create_sales_order_vals(self,partner_dict,order,instance):
        value = super(amazon_sale_order_ept,self).create_sales_order_vals(partner_dict,order,instance)
        fulfillment_channel = order.get('FulfillmentChannel',{}).get('value',False)
        if fulfillment_channel and fulfillment_channel=='AFN':
            
            """Changes by Dhruvi fba_auto_workflow_id is fetched according to seller wise"""
            workflow = instance.seller_id.fba_auto_workflow_id or instance.seller_id.auto_workflow_id
            value.update({'warehouse_id':instance.fba_warehouse_id and instance.fba_warehouse_id.id or instance.warehouse_id.id,
                          'auto_workflow_process_id' :workflow.id, 
                          'amz_fulfillment_by' : 'AFN',
                          'picking_policy' : workflow.picking_policy,
                          'invoice_policy':workflow.invoice_policy or False,
                          'seller_id':instance.seller_id and instance.seller_id.id or False,
                          'global_channel_id':instance.seller_id and instance.seller_id.global_channel_id and instance.seller_id.global_channel_id.id or False
                          })
                    
        return value 
                
class amazon_sale_order_line_ept(models.Model):
    _inherit="sale.order.line"    
    
    amz_gift_message=fields.Text("Gift Message")
    amz_displayable_comment=fields.Text("Displayable Comment")
    amz_per_unit_declared_value=fields.Float("Per Unit Declared Value",digits=dp.get_precision("Product Price"),default=0.0)
    amz_merchant_order_item_id = fields.Char(string="Merchant Item Id")
    amz_merchant_adjustment_item_id = fields.Char(string="Merchant Adjustment Item Id",default=False)
    amz_fulfillment_center_id = fields.Many2one('amazon.fulfillment.center',string='Fulfillment Center')
    
    

    
    