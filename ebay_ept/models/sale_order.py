#!/usr/bin/python3
from odoo import models, fields,api
import time
from pytz import timezone
from datetime import timedelta,datetime
from odoo.exceptions import Warning

class sale_order(models.Model):
    _inherit = "sale.order"

    @api.one
    def _get_ebay_status(self):
        for order in self:
            if order.picking_ids:
                order.updated_in_ebay=True
            else:
                order.updated_in_ebay=False
            for picking in order.picking_ids:
                if picking.state =='cancel':
                    continue
                if picking.picking_type_id.code!='outgoing':
                    continue
                if not picking.updated_in_ebay:
                    order.updated_in_ebay=False
                    break
                
    def _search_ebay_order_ids(self,operator,value):
        query="""
                select sale_order.id from stock_picking
                inner join sale_order on sale_order.procurement_group_id=stock_picking.group_id and sale_order.ebay_order_id is not null
                inner join stock_location on stock_location.id=stock_picking.location_dest_id and (stock_location.usage='customer')
                where stock_picking.updated_in_ebay=False and stock_picking.state='done'    
              """
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids=[]
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        return [('id','in',order_ids)]
    
    feedback_ids=fields.One2many("ebay.feedback.ept","sale_order_id",'ebay Feedback')
    ebay_order_id = fields.Char(size=350, string='eBay Order Ref', required=False)
    ebay_instance_id=fields.Many2one("ebay.instance.ept","Instance")
    shipping_id = fields.Many2one('ebay.shipping.service', 'Shipping')
    updated_in_ebay = fields.Boolean('Updated in eBay',search="_search_ebay_order_ids",compute="_get_ebay_status")
    ebay_payment_option_id = fields.Many2one('ebay.payment.options',"Payment Option")
    ebay_mismatch_order = fields.Boolean(string="eBay Mismatch Order",default=False)    
    ebay_buyer_id=fields.Char("Ebay Buyer Id",default=False,copy=False)    
    
    @api.multi
    def _prepare_invoice(self):
        """We need to Inherit this method to set eBay instance id in Invoice"""
        res = super(sale_order,self)._prepare_invoice()
        res.update({'ebay_instance_id' : self.ebay_instance_id and self.ebay_instance_id.id or False,
                    'ebay_payment_option_id':self.ebay_payment_option_id.id,
                    'global_channel_id':self.global_channel_id and self.global_channel_id.id or False})
        return res  
      
    @api.multi
    def import_ebay_shipped_order(self, instance, shipped_order_from_date, shipped_order_to_date):
        """
            Import shipped order from eBay.
            @return: True
        """
        stock_immediate_transfer_obj = self.env['stock.immediate.transfer']
        
        from_date = shipped_order_from_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        to_date = shipped_order_to_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        page_number = 1
        resultfinal = []
        
        while True:
            orders = {}
            try:
                results={}
                api = instance.get_trading_api_object()
                order_status = 'Completed'
                shipped_order_param = {'CreateTimeFrom':from_date,'CreateTimeTo':to_date,'OrderStatus':order_status,'OrderRole':'Seller','Pagination':{'PageNumber':page_number}}
                api.execute('GetOrders', shipped_order_param)
                results = api.response.dict()
                orders = results.get('OrderArray',{}) and results['OrderArray'].get('Order',[]) or []
            except Exception as e:
                raise Warning(e)
            if type(orders) == dict:
                orders = [orders]
            has_more_trans = results.get('HasMoreOrders','false')
            for result in orders:
                if result.get('ShippedTime'):
                    resultfinal = resultfinal + [result]
            if has_more_trans == 'false':
                break
            page_number=page_number+1
        
        if resultfinal:
            odoo_order_list = self.create_ebay_sales_order_ept(instance,resultfinal,False)
            odoo_orders = self.env['sale.order'].browse(odoo_order_list)
            for odoo_order in odoo_orders:
                if odoo_order.state == "draft":
                    odoo_order.action_confirm()
                for picking in odoo_order.picking_ids:
                    if picking.state in ['waiting','confirmed']:
                        picking.action_assign()
                    #if picking.state in ['confirmed','partially_available']:
                    #    picking.force_assign()
                    if picking.state == 'assigned':   
                        stock_immediate_transfer_obj.create({'pick_ids':[(4,picking.id)]}).process()
        return True
    
    """Import Sales Order From eBay"""
    @api.multi
    def ebay_import_sales_order(self,instance,is_import_shipped_order=False):
        """If Last Sync Time is definds then system will take those orders which are created after last import time 
          Otherwise System will take last 30 days orders
        """
        now_tm = datetime.now()
        current_now = str(now_tm)[:19]
        now_utc = datetime.now(timezone('UTC'))

        #########################Timezone Logic########################
        timezone_time = self.env.user.tz
        if timezone_time:
            current_timezone = now_utc.astimezone(timezone(timezone_time))
            current_timezone = str(current_timezone)[:19]
        else:
            current_timezone = current_now
        ###############################################################
            
        try:
            current_time_to = instance.get_ebay_official_time()
        except Exception as e:
            raise Warning("Call GeteBayOfficialTime API time error.")

        if instance.last_ebay_order_import_date:
            current_time_from = instance.last_ebay_order_import_date
            current_time_from=current_time_from - timedelta(days=10)
            current_time_from = current_time_from.strftime("%Y-%m-%dT%H:%M:%S")
            current_time_from = str(current_time_from)+'.000Z'
        else:
            current_time = datetime.strptime(current_time_to, "%Y-%m-%dT%H:%M:%S.000Z")
            now = current_time - timedelta(days=30)
            current_time_from = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")            
        page_number = 1
        resultfinal = []
        while True:
            orders = {}
            try:
                results={}
                api = instance.get_trading_api_object()
                #order_status = 'All'
                order_status = 'Completed'
                api.execute('GetOrders', {'CreateTimeFrom':current_time_from,'CreateTimeTo':current_time_to,'OrderStatus':order_status,'OrderRole':'Seller','Pagination':{'PageNumber':page_number}})
                results = api.response.dict()
                orders = results.get('OrderArray',{}) and results['OrderArray'].get('Order',[]) or []
            except Exception as e:
                raise Warning(e)
            if type(orders) == dict:
                orders = [orders]
            has_more_trans = results.get('HasMoreOrders','false')
            for result in orders:
                if not result.get('ShippedTime'):
                    resultfinal = resultfinal + [result]
                if result.get('ShippedTime') and is_import_shipped_order:
                    resultfinal = resultfinal + [result]
            if has_more_trans == 'false':
                break
            page_number=page_number+1

        if resultfinal:
            self.create_ebay_sales_order_ept(instance,resultfinal,is_import_shipped_order)
        instance.write({'last_ebay_order_import_date':datetime.now()})
        return True

    @api.multi
    def check_vatidation_of_order(self,order_dict,instance,job):
        ebay_product=False
        ebay_product_obj=self.env['ebay.product.product.ept']
        odoo_product_obj=self.env['product.product']
        ebay_product_tmpl_obj=self.env['ebay.product.template.ept']
        sale_order_line_obj=self.env['sale.order.line']
        ebay_product_listing_obj=self.env['ebay.product.listing.ept']
        payment_option_obj=self.env['ebay.payment.options'] 
        ebay_process_job_log_obj=self.env['ebay.log.book']
        ebay_transaction_line_obj=self.env['ebay.transaction.line']
        ebay_order_ref=order_dict.get('OrderID',False)
        skip_order = False
        is_ebay_mismatch = False                    
        message = ''
        log_message = ''
        res_id = False
        model_name = 'ebay.product.product.ept'
        order_checkout_status=order_dict.get('CheckoutStatus')
        ebay_payment_status=order_checkout_status.get('eBayPaymentStatus')
        
        if ebay_payment_status=='BuyerCreditCardFailed' or ebay_payment_status=='BuyerECheckBounced':
            if not job:
                job_log_vals = {
                                'skip_process' : True,
                                'application' : 'sales',
                                'operation_type' : 'import',
                                'instance_id':instance.id
                                }
                job=ebay_process_job_log_obj.create(job_log_vals) 
            log_line_vals = {
                             'model_id' : ebay_transaction_line_obj.get_model_id('sale.order'),
                             'res_id' :  0,
                             'log_type' : 'mismatch',
                             'action_type' : 'skip_line',
                             'job_id':job.id,
                             'message' :"Order %s skiped due to Payment Status is %s"%(ebay_order_ref,ebay_payment_status),
                             'ebay_order_ref':ebay_order_ref,
                             }
            ebay_transaction_line_obj.create(log_line_vals)
            return True,False,job
        payment_method=order_checkout_status.get('PaymentMethod','Paypal')
        #payment_method='PayPal'
        payment_option=payment_option_obj.search([('name','=',payment_method),('instance_id','=',instance.id),('auto_workflow_id','!=',False)],limit=1)
        if not payment_option:
            if not job:
                job_log_vals = {
                                'skip_process' : True,
                                'application' : 'sales',
                                'operation_type' : 'import',
                                'instance_id':instance.id
                                }
                job=ebay_process_job_log_obj.create(job_log_vals) 
            log_line_vals = {
                             'model_id' : ebay_transaction_line_obj.get_model_id('sale.order'),
                             'res_id' :  0,
                             'log_type' : 'mismatch',
                             'action_type' : 'skip_line',
                             'job_id':job.id,
                             'message' :"Order %s skiped due to autoworkflow configuration not found for payment method %s"%(ebay_order_ref,payment_method),
                             'ebay_order_ref':ebay_order_ref,
                             }
            ebay_transaction_line_obj.create(log_line_vals)
            return True,False,job
        if payment_option and not payment_option.payment_term_id:
            if not job:
                job_log_vals = {
                                'skip_process' : True,
                                'application' : 'sales',
                                'operation_type' : 'import',
                                'instance_id':instance.id
                                }
                job=ebay_process_job_log_obj.create(job_log_vals) 
            log_line_vals = {
                             'model_id' : ebay_transaction_line_obj.get_model_id('sale.order'),
                             'res_id' :  0,
                             'log_type' : 'mismatch',
                             'action_type' : 'skip_line',
                             'job_id':job.id,
                             'message' :"Order %s skiped due to Payment Term not found in payment method %s"%(ebay_order_ref,payment_method),
                             'ebay_order_ref':ebay_order_ref,
                             }
            ebay_transaction_line_obj.create(log_line_vals)
            return True,False,job
            
            
        transaction_log_lines = []
        order_lines = order_dict.get('TransactionArray',False) and order_dict['TransactionArray'].get('Transaction',[])
        if type(order_lines) == dict:
            order_lines = [order_lines]
        for order_line in order_lines:
            ebay_sku=order_line.get('Variation',{}).get('SKU',False)
            if not ebay_sku:
                ebay_sku=order_line.get('Item',{}).get('SKU',False)
            title=order_line.get('VariationTitle')
            if not title:
                title=order_line.get('Item',{}).get('Title',False)
            item_id=order_line.get('Item',{}).get('ItemID',{})
            if not ebay_sku:
                listing_record=ebay_product_listing_obj.search([('name','=',item_id),('instance_id','=',instance.id)],limit=1)
                if not listing_record:
                    ebay_sku=ebay_product_tmpl_obj.get_item(instance,item_id)
                else:
                    ebay_sku=listing_record.ebay_variant_id and listing_record.ebay_variant_id.ebay_sku
            domain = [('instance_id','=',instance.id)]
            if ebay_sku:
                ebay_sku and domain.append(('ebay_sku','=',ebay_sku))
                ebay_product = ebay_product_obj.search(domain)
            else:
                ebay_product=False
            if not ebay_product:
                odoo_product = odoo_product_obj.search([('default_code','=',ebay_sku),'|',('active','=',False),('active','=',True)], limit=1)
                if  odoo_product and not odoo_product.active:
                    odoo_product.write({'active':True})
                    
                """
                    If odoo product founds and ebay product not found then no need to check anything 
                    and create new ebay product and create log for that, if odoo product not found then 
                    go to check configuration which action has to be taken for that.
                    
                    There are following situations managed by code. 
                    In any situation log that event and action.
                    
                    1). eBay product and Odoo product not found
                        => Check seller configuration if allow to create new product then create product.
                        => Enter log details with action.
                    2). eBay product not found but odoo product is there.
                        => Created eBay product with log and action.
                """
                if odoo_product:
                    log_action_type = 'create'
                    message = 'Order is imported with creating new ebay product.'
                    log_message = 'Product %s created in ebay for %s instance'%(ebay_sku, instance.name)
                elif not instance.create_new_product:
                    skip_order = True
                    message = 'Order is not imported due to product not found issue.'
                    log_action_type = 'skip_line'
                    log_message = 'Product %s not found for %s instance'%(ebay_sku, instance.name )
                else:
                    log_action_type = 'create'
                    message = 'Order is imported with creating new odoo product.'
                    log_message = 'Product %s created in odoo for %s instance'%(ebay_sku, instance.name )
                if not ebay_sku:
                    skip_order = True
                    message = 'Order is not imported due to product sku found Null.'
                    log_action_type = 'skip_line'
                    log_message = 'Product SKU null found for %s instance'%(instance.name)
                if ebay_sku and not instance.create_new_product and instance.create_quotation_without_product:
                    skip_order = False
                    is_ebay_mismatch = True
                    log_action_type = 'create'
                    message = 'Order Created without products based on instance %s configuration.'%(instance.name)
                if not skip_order:
                    if odoo_product:
                        ebay_product=sale_order_line_obj.create_ebay_products(odoo_product,instance)                    
                    else:
                        if instance.create_new_product:
                            ebay_product=sale_order_line_obj.create_product_vals(ebay_sku,title,instance)
                    if not odoo_product:
                        res_id = ebay_product and ebay_product.product_id.id or False
                        model_name = 'product.product'
                    else:
                        res_id = ebay_product and ebay_product.id or False                    
                if not job:   
                    job_log_vals = {
                                    'transaction_log_ids' : transaction_log_lines,
                                    'skip_process' : skip_order,
                                    'application' : 'sales',
                                    'operation_type' : 'import',
                                    'message' : message,
                                    'instance_id':instance.id
                                    }
                    job=ebay_process_job_log_obj.create(job_log_vals)

                log_line_vals = {
                                 'model_id' : ebay_transaction_line_obj.get_model_id(model_name),
                                 'res_id' : res_id or 0,
                                 'log_type' : 'not_found',
                                 'action_type' : log_action_type,
                                 'not_found_value' : ebay_sku,
                                 'job_id':job.id,
                                 'message' : log_message,
                                 'ebay_order_ref':ebay_order_ref,
                                 }
                ebay_transaction_line_obj.create(log_line_vals)

        return skip_order,is_ebay_mismatch,job
    
    """This Function Create Orders into ERP System"""
    @api.multi
    def create_ebay_sales_order_ept(self,instance,orders,is_import_shipped_order=False):
        auto_work_flow_obj=self.env['sale.workflow.process.ept']
        sale_order_line_obj=self.env['sale.order.line']
        sale_order_object = self.env['sale.order']
        stock_immediate_transfer_obj=self.env['stock.immediate.transfer']
        odoo_order_ids,shipped_orders,shipped_orders_ids = [],[],[]
       
        job=False
        for order_dict in orders:       
            ebay_order_ref=order_dict.get('OrderID',False)
            if not ebay_order_ref:
                continue
            existing_order=self.search([('ebay_order_id','=',ebay_order_ref),('ebay_instance_id','=',instance.id)])
            if existing_order:
                continue
            skip_order,is_ebay_mismatch,job=self.check_vatidation_of_order(order_dict, instance, job)
            if skip_order:
                continue
            
            # Create/Update Partner
            partner_dict=self.create_or_update_partner(order_dict,instance)
                
            # Create Sale Order
            order_vals=self.create_ebay_sales_order_vals(partner_dict,order_dict,instance)
            
            if is_ebay_mismatch:
                order_vals.update({'ebay_mismatch_order':True})
            ebay_order = self.create(order_vals)
            
            if order_dict.get('ShippedTime') and is_import_shipped_order:
                shipped_orders.append(order_dict.get('OrderID',''))
            
            if not is_ebay_mismatch and ebay_order:
                odoo_order_ids.append(ebay_order.id)
                if ebay_order.ebay_order_id in shipped_orders:
                    shipped_orders_ids.append(ebay_order.id)
                
            shipping_cost= float(order_dict.get('ShippingServiceSelected',{}).get('ShippingServiceCost',{}).get('value',0.0))
            order_dicounts=order_dict.get('SellerDiscounts',{}).get('SellerDiscount')  
            if order_dicounts==None:
                order_dicounts=[]
            
            # Shipping Lines
            is_already_shipment_line=False
            if shipping_cost > 0.0:
                is_already_shipment_line=True
                shipment_charge_product=instance.shipment_charge_product_id
                order_line_vals=sale_order_line_obj.create_sale_order_line_vals({},shipping_cost,False,shipment_charge_product, ebay_order, instance,shipment_charge_product.name or 'ShippingServiceCost')
                order_line_vals.update({'is_delivery':True})
                sale_order_line_obj.create(order_line_vals)                
            if isinstance(order_dicounts,dict):
                order_dicounts=[order_dicounts]
            
            # Discount Lines
            for order_dicount in order_dicounts:
                seller_dicount_value = float(order_dicount.get('ItemDiscountAmount').get('value',0.0))
                if seller_dicount_value > 0.0:
                    discount_charge_product=instance.discount_charge_product_id
                    order_line_vals=sale_order_line_obj.create_sale_order_line_vals({},-seller_dicount_value,False,discount_charge_product, ebay_order, instance,'Seller Discount')
                    order_line_vals.update(
                                           {'seller_dicount_campaign_display_name':order_dicount.get('CampaignDisplayName').get('value'),
                                            'seller_dicount_campaign_id':order_dicount.get('CampaignID').get('value')
                                            }
                                           )
                    sale_order_line_obj.create(order_line_vals)
                    
                shipping_dicount_value = float(order_dicount.get('ShippingDiscountAmount').get('value',0.0))
                if shipping_dicount_value > 0.0:
                    discount_charge_product=instance.discount_charge_product_id
                    order_line_vals=sale_order_line_obj.create_sale_order_line_vals({},-shipping_dicount_value,False,discount_charge_product, ebay_order, instance,'Shipping Discount')
                    order_line_vals.update(
                                           {'seller_dicount_campaign_display_name':order_dicount.get('CampaignDisplayName').get('value'),
                                            'seller_dicount_campaign_id':order_dicount.get('CampaignID').get('value')
                                            }
                                           )
                    sale_order_line_obj.create(order_line_vals)
                    
            # Create Sale Order Line
            sale_order_line_obj.create_ebay_sale_order_line(order_dict,instance,ebay_order,is_already_shipment_line)
            
        if odoo_order_ids:
            odoo_orders = self.env['sale.order'].browse(odoo_order_ids)
            for order in odoo_orders:
                order.invoice_shipping_on_delivery = False
            auto_work_flow_obj.auto_workflow_process(False,odoo_order_ids)
            
            shipped_order_records = sale_order_object.browse(shipped_orders_ids)
            for shipped_order in shipped_order_records:
                for picking in shipped_order.picking_ids:
                    if picking.state in ['waiting','confirmed']:
                        picking.action_assign()
                    if picking.state in ['confirmed','partially_available']:
                        picking.force_assign()
                    if picking.state == 'assigned':
                        stock_immediate_transfer_obj.create({'pick_ids':[(4,picking.id)]}).process()            
        return odoo_order_ids
    
    @api.multi
    def create_ebay_sales_order_vals(self,partner_dict,order_dict,instance):  
        sale_order_obj=self.env['sale.order']     
        shipping_service_obj=self.env['ebay.shipping.service']
        delivery_carrier_obj=self.env['delivery.carrier']
        payment_option_obj=self.env['ebay.payment.options'] 
        
        shipping_service_name = order_dict.get('ShippingServiceSelected',{}).get('ShippingService',False)
        shipping_service = shipping_service_obj.search([('ship_service','=',shipping_service_name),('site_ids','in',instance.site_id.ids)],limit=1)
        delivery_carrier = delivery_carrier_obj.search(['|',('ebay_code','=',shipping_service_name),('name','=',shipping_service_name)],limit=1)
        
        order_checkout_status = order_dict.get('CheckoutStatus')
        payment_method = order_checkout_status.get('PaymentMethod')
        #payment_method='PayPal'
        payment_option = payment_option_obj.search([('name','=',payment_method),('instance_id','=',instance.id),('auto_workflow_id','!=',False)],limit=1)
        workflow_process_id = payment_option and payment_option.auto_workflow_id.id or False
        ebay_payment_option_id = payment_option and payment_option.id or False

        ordervals = {
            'company_id':instance.company_id.id,                   
            'partner_id' :partner_dict.get('invoice_address'),
            'partner_invoice_id' : partner_dict.get('invoice_address'),
            'partner_shipping_id' : partner_dict.get('delivery_address'),
            'warehouse_id' :instance.warehouse_id.id,
            'picking_policy': payment_option.auto_workflow_id.picking_policy or False,
            'date_order' : instance.openerp_format_date(order_dict.get('CreatedTime',False)),
            'pricelist_id' : partner_dict.get('pricelist_id'),
            'fiscal_position_id': instance.fiscal_position_id and instance.fiscal_position_id.id or False,
            'payment_term_id': payment_option.payment_term_id.id or False,
            'invoice_policy':payment_option.auto_workflow_id.invoice_policy or False,
            'team_id' : instance.team_id and instance.team_id.id or False,
            'carrier_id': delivery_carrier and delivery_carrier.id or False,
        }
        ordervals = sale_order_obj.create_sales_order_vals_ept(ordervals)
        ordervals.update({
            'name' : "%s%s" % (instance.order_prefix or '', order_dict.get('OrderID')),
            'ebay_instance_id': instance and instance.id or False,
            'ebay_buyer_id':order_dict.get('BuyerUserID',False),
            'ebay_order_id': order_dict.get('OrderID',False),
            'auto_workflow_process_id': workflow_process_id,
            'ebay_payment_option_id': ebay_payment_option_id,
            'shipping_id': shipping_service and shipping_service.id or False,
            'global_channel_id': instance.global_channel_id and instance.global_channel_id.id or False             
        })
        return ordervals
    
    @api.multi
    def create_or_update_partner(self,order,instance):
        partner_obj = self.env['res.partner']
        
        address_info = order.get('ShippingAddress',{})
        return_partner = {}
        if not instance.partner_id:
            partner_id=False
        else:
            partner_id=instance.partner_id.id
        
        ebay_user_id = order.get('BuyerUserID',False)
        ebay_eias_token = order.get('EIASToken',False)
        ebay_address_id = address_info.get('AddressID',False)
        
        transaction = order.get('TransactionArray',False) and order['TransactionArray'].get('Transaction',False) and order['TransactionArray']['Transaction'] or {}
        if type(transaction) == list:
            transaction = transaction[0]
            
        email = transaction.get('Buyer',False) and transaction['Buyer'].get('Email',False) or ''
        cust_name=address_info.get('Name','eBay Customer')
        if cust_name == 'None' or cust_name == None:
            cust_name='eBay Customer'
        
        pre_vals = {
            'name': cust_name,
            'country_code': address_info.get('Country',''),
            'country_name': address_info.get('CountryName',''),
            'state_code': address_info.get('StateOrProvince',False),
            'state_name': address_info.get('StateOrProvince',False), 
            'street': address_info.get('Street1',False),
            'street2': address_info.get('Street2',False),
            'city': address_info.get('CityName',False),
            'phone': address_info.get('Phone',False),
            'email': email,
            'zip': address_info.get('PostalCode',False),
            'lang':instance.lang_id.code,
            'type': 'delivery',
            'is_company': False,
            'parent_id': partner_id,
        }
        
        ctx = {'return_with_state_and_country_obj': True}
        if address_info.get('StateOrProvince',False) != 'None' and address_info.get('StateOrProvince',False) != None:
            ctx.update({'create_new_state': True,'new_state_code': address_info.get('StateOrProvince','')[:3]})
        
        partner_vals,country_id,state_id = partner_obj.with_context(ctx)._prepare_partner_vals(pre_vals)
        instance.pricelist_id and partner_vals.update({'property_product_pricelist': instance.pricelist_id.id})
        partner_vals.update({'ebay_user_emaid_id': email, 'ebay_address_id': ebay_address_id, 'customer' : True})
        
        exist_partner = partner_obj.search([('ebay_user_id','=',ebay_user_id)],limit=1)    
        if exist_partner:
            key_list = [('type','=','delivery')]
            address_info.get('Street1',False) and key_list.append('street')
            address_info.get('Street2',False) and key_list.append('street2')
            transaction.get('Buyer',False) and transaction['Buyer'].get('Email',False) and key_list.append('email')
            address_info.get('Phone',False) and key_list.append('phone')
            address_info.get('CityName',False) and key_list.append('city')
            address_info.get('PostalCode',False) and key_list.append('zip')
            state_id and key_list.append('state_id')
            country_id and key_list.append('country_id')
            cust_name and key_list.append('name') 
            
            exist_partner_id = exist_partner.id
            exist_partner = partner_obj._find_partner(partner_vals,key_list)
            if not exist_partner:
                partner_vals.update({'ebay_user_id':ebay_user_id,'ebay_eias_token':ebay_eias_token,'parent_id':exist_partner_id})
                if 'message_follower_ids' in partner_vals:
                    del partner_vals['message_follower_ids']
                partner=partner_obj.create(partner_vals)
                partner and return_partner.update({'invoice_address':partner.id,'delivery_address':partner.id,'pricelist_id':partner.property_product_pricelist and partner.property_product_pricelist.id})
            else:
                return_partner.update({'invoice_address':exist_partner.id,'delivery_address':exist_partner.id,'pricelist_id':exist_partner.property_product_pricelist and exist_partner.property_product_pricelist.id})
        else:
            partner_vals.update({'ebay_user_id':ebay_user_id,'ebay_eias_token':ebay_eias_token})       
            if 'message_follower_ids' in partner_vals:
                del partner_vals['message_follower_ids']
            partner = partner_obj.create(partner_vals)
            partner and return_partner.update({'invoice_address':partner.id,'delivery_address':partner.id,'pricelist_id':partner.property_product_pricelist and partner.property_product_pricelist.id})
        return return_partner

    @api.multi
    def get_listing_type(self,item_id,instance):
        productlisting_obj = self.env['ebay.product.listing.ept']
        ebay_product_tmpl_obj=self.env['ebay.product.template.ept']
        listing = productlisting_obj.search([('name','=',item_id),('instance_id','=',instance.id)],limit=1)
        if not listing:
            result=ebay_product_tmpl_obj.get_item(instance,item_id)
            if isinstance(result,dict):
                listing_type=result.get('Item',{}).get('ListingType','FixedPriceItem')
                return listing_type
        listing_type = listing and listing.listing_type or 'FixedPriceItem' 
        listing_type_new = 'FixedPriceItem'
        if listing_type =='FixedPriceItem' or listing_type == 'Fixed Price':
            listing_type_new = "FixedPriceItem"
        elif listing_type =='Auction':
            listing_type_new = "Chinese"
            
        return listing_type_new

    @api.multi
    def ebay_update_order_status(self,instance):
        """
            Update Order Status into eBay using CompleteSale API.
        """
        ebay_orders = self.check_already_status_updated_ebay(instance)
        picking_obj=self.env['stock.picking']
        results=False
        tracking_ref=False
        if not ebay_orders:
            return []
        api = instance.get_trading_api_object()
        for ebay_order in ebay_orders:
            pickings=picking_obj.search([('state','not in',['done','cancel']),('id','in',ebay_order.picking_ids.ids),('picking_type_id.code','=','outgoing')])
            if pickings:
                continue
            order_ref=ebay_order.ebay_order_id
            carrier_name=ebay_order.picking_ids[0].carrier_id and (ebay_order.picking_ids[0].carrier_id.ebay_code or ebay_order.picking_ids[0].carrier_id.name ) or False 
            tracking_numbers=[]
            pickings=ebay_order.picking_ids
            for picking in pickings:
                if picking.state=='done' and picking.carrier_tracking_ref:
                    tracking_numbers.append(picking.carrier_tracking_ref)
            for order_line in ebay_order.order_line:
                if not order_line.product_id:
                    continue
                if order_line.product_id.type=='service':
                    continue                
                ebay_order_line_item_id=order_line.ebay_order_line_item_id
                trans_split = ebay_order_line_item_id.split("-")
                item_id = trans_split[0]
                transaction_id = trans_split[1]
                listing_type=self.get_listing_type(item_id,instance)
                para = {'ItemID': item_id,'TransactionID':transaction_id,
                        'OrderID' : order_ref,'OrderLineItemID': ebay_order_line_item_id,'ListingType':listing_type
                        }
                if not instance.manage_multi_tracking_number_in_delivery_order:
                    tracking_shipment=[]
                    if tracking_numbers:
                        for tracking_ref in list(set(tracking_numbers)):
                            tracking_shipment.append({'ShipmentTrackingNumber':tracking_ref,'ShippingCarrierUsed':carrier_name or ''})
                        shipment = {'Shipped':True,'Shipment': {'ShipmentTrackingDetails':tracking_shipment}}
                    elif not tracking_ref:
                        shipment = {'Shipped':True}
                    #shipment.update({'OrderID':order_ref})
                else:
                    tracking_no_package_wise=[]
                    tracking_shipment=[]
                    for picking in pickings:
                        if picking.state!='done':
                            continue
                        for move in picking.move_lines:
                            if move.product_id.id==order_line.product_id.id and move.sale_line_id.id==order_line.id:
                                for move_line in move.move_line_ids:
                                    if move_line.product_qty < 0.0:
                                        continue
                                    tracking_no = move_line.result_package_id and move_line.result_package_id.tracking_no or False
                                    tracking_no and tracking_no_package_wise.append(tracking_no)
                    for tracking_no in list(set(tracking_no_package_wise)):
                        tracking_shipment.append({'ShipmentTrackingNumber':tracking_no,'ShippingCarrierUsed':carrier_name or ''})
                if tracking_shipment:
                    shipment = {'Shipped':True,'Shipment': {'ShipmentTrackingDetails':tracking_shipment}}  
                else:
                    shipment = {'Shipped':True}                
                para.update(shipment)
                try:                                        
                    api.execute('CompleteSale',para)
                    results = api.response.dict()
                    ack = results and results.get('Ack',False)
                    if ack != 'Failure' :
                        pickings.write({'updated_in_ebay':True})
                except Exception:
                    pass
        return True
        
    
    @api.model
    def check_already_status_updated_ebay(self,instance):
        sales_orders = self.search([
            ('warehouse_id','=',instance.warehouse_id.id),
            ('ebay_order_id','!=',False),
            ('ebay_instance_id','=',instance.id),
            ('state','!=','cancel'),                                                     
            ('updated_in_ebay','=',False)
        ],order='date_order')
        return sales_orders