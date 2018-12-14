from odoo import models,fields,api
from ..models.api import OutboundShipments_Extend
class amazon_instace_ept(models.Model):
    _inherit="amazon.instance.ept"
    
#     help_fulfillment_action = """ 
#         Ship - The fulfillment order ships now
# 
#         Hold - An order hold is put on the fulfillment order.3
# 
#         Default: Ship in Create Fulfillment
#         Default: Hold in Update Fulfillment    
#     """
#     
#     help_fulfillment_policy = """ 
# 
#         FillOrKill - If an item in a fulfillment order is determined to be unfulfillable before any shipment in the order moves 
#                     to the Pending status (the process of picking units from inventory has begun), 
#                     then the entire order is considered unfulfillable. However, if an item in a fulfillment order is determined 
#                     to be unfulfillable after a shipment in the order moves to the Pending status, 
#                     Amazon cancels as much of the fulfillment order as possible
# 
#         FillAll - All fulfillable items in the fulfillment order are shipped. 
#                 The fulfillment order remains in a processing state until all items are either shipped by Amazon or cancelled by the seller
# 
#         FillAllAvailable - All fulfillable items in the fulfillment order are shipped. 
#             All unfulfillable items in the order are cancelled by Amazon.
# 
#         Default: FillOrKill
#     """
    
    fba_warehouse_id = fields.Many2one('stock.warehouse', string='FBA Warehouse')
    validate_stock_inventory_for_report = fields.Boolean("Auto Validate Amazon FBA Live Stock Report")
    fulfillment_by=fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')
    stock_auto_import_by_report = fields.Boolean(string='Auto Import FBA Live Stock Report?')
    
    """Commented by Dhruvi as these field is added to amazon seller."""
#     default_fba_partner_id = fields.Many2one('res.partner', string='Default Customer for FBA pending order')
#     fba_auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Auto Workflow (FBA)')
    split_order =fields.Boolean('Split FBA Order by Warehouse',default=True)    
    order_return_config_ids = fields.One2many('order.return.config','instance_id',string='Order Return Conditions')
    
    # Inbound Shipment
    allow_process_unshipped_products=fields.Boolean("Allow Process Unshipped Products in Inbound Shipment ?",default=True)
    update_partially_inbound_shipment=fields.Boolean('Allow Update Partially Inbound Shipment ?',default=False)
    is_allow_prep_instruction = fields.Boolean(string="Allow Prep Instruction in Inbound Shipment ?",default=False,help="Amazon FBA: If ticked then allow to pass the prep-instructions details during create Inbount Shipment Plan in Amazon.")
    
    check_status_days = fields.Integer("Check Status Days",default=30,help="System will check status after closed shipment")
    auto_process_fba_live_stock_report = fields.Boolean(string='Auto Process FBA Live Stock Report?')
    amazon_sale_order_ids = fields.One2many('sale.order', 'amz_instance_id',domain=[('amz_fulfillment_by','=','MFN'),('amz_is_outbound_order','=',False)], string='(FBM)Orders')
    quotation_ids = fields.One2many('sale.order','amz_instance_id',domain=[('state','in',['draft','sent']),('amz_fulfillment_by','=','MFN'),('amz_is_outbound_order','=',False)],string="(FBM)Quotations")
    order_ids = fields.One2many('sale.order','amz_instance_id',domain=[('state','not in',['draft','sent','cancel']),('amz_fulfillment_by','=','MFN'),('amz_is_outbound_order','=',False)],string="(FBM)Sales Order")
    
    # Unsellable Location
    unsellable_location_id = fields.Many2one('stock.location',string="Unsellable Location",help="Amazon unsellabel location")
    
    """Commented by Dhruvi as these fields are added to amazon seller"""
    # Outbound Order
#     is_auto_create_outbound_order = fields.Boolean(string="Auto Create Outbound Order ?",default=False,help="This box is ticked to automatically create Outbound Order.")
#     fulfillment_action = fields.Selection([('Ship', 'Ship'), ('Hold', 'Hold')], string="Fulfillment Action", help=help_fulfillment_action)
#     shipment_service_level_category = fields.Selection(
#         [('Expedited', 'Expedited'), ('NextDay', 'NextDay'), ('SecondDay', 'SecondDay'), ('Standard', 'Standard'),
#          ('Priority', 'Priority'), ('ScheduledDelivery', 'ScheduledDelivery')], "Shipment Category", help="Amazon shipment category")
#     fulfillment_policy = fields.Selection(
#         [('FillOrKill', 'FillOrKill'), ('FillAll', 'FillAll'), ('FillAllAvailable', 'FillAllAvailable')], string="Fulfillment Policy", help=help_fulfillment_policy)
#     notify_by_email = fields.Boolean("Notify By Email", default=False, help="If true then system will notify by email to followers")
    
    def _fba_count_all(self):
        inbound_shipment_plan_ept_obj=self.env['inbound.shipment.plan.ept']
        inbound_shipment_ept_obj=self.env['amazon.inbound.shipment.ept']
        for instance in self:
            instance.fba_sale_order_count = len(instance.amazon_fba_sale_order_ids)
            instance.fba_quotation_count = len(instance.fba_quotation_ids)
            instance.fba_order_count = len(instance.fba_order_ids)
            instance.fba_return_delivery_order_count = len(instance.fba_return_delivery_order_ids)
            
            draft_inbound_shipment_plans=inbound_shipment_plan_ept_obj.search([('instance_id','=',instance.id),('state','=','draft')])
            instance.count_draft_inbound_shipment_plan=len(draft_inbound_shipment_plans)
            approved_inbound_shipment_plans=inbound_shipment_plan_ept_obj.search([('instance_id','=',instance.id),('state','=','plan_approved')])
            instance.count_approved_inbound_shipment_plan=len(approved_inbound_shipment_plans)
            
            working_inbound_shipments=inbound_shipment_ept_obj.search([('shipment_plan_id.instance_id','=',instance.id),('state','=','WORKING')])
            instance.count_working_inbound_shipment=len(working_inbound_shipments)            
            shipped_inbound_shipments=inbound_shipment_ept_obj.search([('shipment_plan_id.instance_id','=',instance.id),('state','=','SHIPPED')])
            instance.count_shipped_inbound_shipment=len(shipped_inbound_shipments)            
            cancelled_inbound_shipments=inbound_shipment_ept_obj.search([('shipment_plan_id.instance_id','=',instance.id),('state','=','CANCELLED')])
            instance.count_cancelled_inbound_shipment=len(cancelled_inbound_shipments)            
            closed_inbound_shipments=inbound_shipment_ept_obj.search([('shipment_plan_id.instance_id','=',instance.id),('state','=','CLOSED')])
            instance.count_closed_inbound_shipment=len(closed_inbound_shipments)
    
    amazon_fba_sale_order_ids = fields.One2many('sale.order', 'amz_instance_id',domain=[('amz_fulfillment_by','=','AFN'),('amz_is_outbound_order','=',False)], string='(FBA)Sale Orders')
    fba_sale_order_count = fields.Integer(compute='_fba_count_all', string="(FBA)Orders")
    fba_quotation_ids = fields.One2many('sale.order','amz_instance_id',domain=[('state','in',['draft','sent']),('amz_fulfillment_by','=','AFN'),('amz_is_outbound_order','=',False)],string="(FBA)Sale Quotations")
    fba_quotation_count = fields.Integer(compute='_fba_count_all', string="(FBA)Quotations")
    fba_order_ids = fields.One2many('sale.order','amz_instance_id',domain=[('state','not in',['draft','sent','cancel']),('amz_fulfillment_by','=','AFN'),('amz_is_outbound_order','=',False)],string="(FBA)Sales Order")
    fba_order_count =fields.Integer(compute='_fba_count_all', string="(FBA)Sales Orders")
    
    count_draft_inbound_shipment_plan=fields.Integer(string="Count Draft Inbound Shipment Plan",compute="_fba_count_all")
    count_approved_inbound_shipment_plan=fields.Integer(string="Count Approved Inbound Shipment Plan",compute="_fba_count_all")

    count_working_inbound_shipment=fields.Integer(string="Count Working Inbound Shipment",compute="_fba_count_all")
    count_shipped_inbound_shipment=fields.Integer(string="Count Shipped Inbound Shipment",compute="_fba_count_all")
    count_cancelled_inbound_shipment=fields.Integer(string="Count Cancelled Inbound Shipment",compute="_fba_count_all")
    count_closed_inbound_shipment=fields.Integer(string="Count Closed Inbound Shipment",compute="_fba_count_all")
    
    fba_return_delivery_order_ids = fields.One2many('stock.picking','amazon_instance_id',domain=[('is_amazon_fba_return_delivery_order','=','True')],string="FBA Return Picking")
    fba_return_delivery_order_count = fields.Integer(compute='_fba_count_all', string="FBA Return Pickings")   
    
    @api.one
    @api.constrains('fba_warehouse_id','company_id')        
    def onchange_company_warehouse_id(self):
        if self.fba_warehouse_id and self.company_id and self.fba_warehouse_id.company_id.id != self.company_id.id:
            raise Warning("Company in warehouse is different than the selected company. Selected Company and FBA Warehouse company must be same.")

    @api.model
    def auto_create_outbound_order(self,args={}):
        """
            This function trigger to instance wise automatic create out-bound orders.
            @return: True
        """
        
        amazon_seller_obj = self.env['amazon.seller.ept']
        amazon_instance_obj =self.env['amazon.instance.ept']
        sale_order_obj = self.env['sale.order']
        amazon_product_obj = self.env['amazon.product.ept']

        active_seller_id = args.get('seller_id',False)
        seller = active_seller_id and amazon_seller_obj.search([('id','=',active_seller_id)]) or False
        instance_ids = seller and amazon_instance_obj.search([('seller_id','=',seller.id)])
        
        if seller:
            mws_obj = OutboundShipments_Extend(access_key=str(seller.access_key), secret_key=str(seller.secret_key),
                                                account_id=str(seller.merchant_id),
                                                region=seller.country_id.amazon_marketplace_code or seller.country_id.code)
            
            
            """Changes by Dhruvi all these fields are fetched according to seller wise."""
            fulfillment_action = seller.fulfillment_action
            shipment_service_level_category = seller.shipment_service_level_category
            fulfillment_policy = seller.fulfillment_policy
            notify_by_email = seller.notify_by_email or False
            
            for instance in instance_ids:
                fba_warehouse = instance.fba_warehouse_id or False
                
                """Changes by Dhruvi
                    default_fba_partner_id is fetched according to seller wise."""
                def_fba_partner_id = seller.def_fba_partner_id or False
                 
                _amazon_sale_order_domain = [
                    ('warehouse_id','=',fba_warehouse and fba_warehouse.id or False),
                    ('partner_id','!=',def_fba_partner_id and def_fba_partner_id.id or False),
                    ('state','=','draft')
                ]
    
                sale_orders = sale_order_obj.search(_amazon_sale_order_domain)
                for sale_order in sale_orders:
                    if not sale_order.order_line:
                        continue
                    
                    amazon_sale_order = sale_order
                    if not amazon_sale_order.amz_fulfillment_instance_id:
                        amazon_sale_order.write({
                            'amz_instance_id': instance.id,
                            'amz_fulfillment_instance_id': instance.id,
                            'amz_fulfillment_action': fulfillment_action,
                            'warehouse_id': fba_warehouse and fba_warehouse.id or False,
                            'pricelist_id': instance.pricelist_id and instance.pricelist_id.id or False,
                            'amz_fulfillment_policy': fulfillment_policy,                                
                            'amz_shipment_service_level_category': shipment_service_level_category,
                            'amz_is_outbound_order': True,
                            'notify_by_email': notify_by_email,
                            'amazon_reference': sale_order.name,
                            'note':sale_order.note or sale_order.name
                             
                        })
                    
                    create_order=True
                    for line in amazon_sale_order.order_line:
                        if line.product_id.type=='service':
                            continue
                        if line.product_id:
                            amz_product = amazon_product_obj.search([('product_id','=',line.product_id and line.product_id.id),('instance_id','=',instance.id),('fulfillment_by','=','AFN')],limit=1)
                            if not amz_product:
                                create_order=False
                                break
                            line.write({'amazon_product_id': amz_product.id})
                    if create_order:
                        try:
                            mws_obj.CreateFulfillmentOrder(amazon_sale_order)
                            self._cr.commit()
                        except Exception as e:                       
                            pass 
            
        return True
    
#         amazon_instance_ept_obj = self.env['amazon.instance.ept']
#         sale_order_obj = self.env['sale.order']
#         amazon_product_obj = self.env['amazon.product.ept']
#         
#         active_instance_id = args.get('instance_id', False)
#         instance = active_instance_id and amazon_instance_ept_obj.search([('id','=',active_instance_id)],limit=1) or False
#         if instance:
#             mws_obj = OutboundShipments_Extend(access_key=str(instance.access_key), secret_key=str(instance.secret_key),
#                                                account_id=str(instance.merchant_id),
#                                                region=instance.country_id.amazon_marketplace_code or instance.country_id.code)
#             
#             """Changes by Dhruvi all these fields are fetched according to seller wise."""
#             fulfillment_action = instance.seller_id.fulfillment_action
#             shipment_service_level_category = instance.seller_id.shipment_service_level_category
#             fulfillment_policy = instance.seller_id.fulfillment_policy
#             notify_by_email = instance.seller_id.notify_by_email or False
#             
#             fba_warehouse = instance.fba_warehouse_id or False
#             
#             """Changes by Dhruvi
#                 default_fba_partner_id is fetched according to seller wise."""
#             default_fba_partner_id = instance.seller_id.default_fba_partner_id or False
#             
#             _amazon_sale_order_domain = [
#                 ('warehouse_id','=',fba_warehouse and fba_warehouse.id or False),
#                 ('partner_id','!=',default_fba_partner_id and default_fba_partner_id.id or False),
#                 ('state','=','draft')
#             ]
#             sale_orders = sale_order_obj.search(_amazon_sale_order_domain)
#             for sale_order in sale_orders:
#                 if not sale_order.order_line:
#                     continue
#                 
#                 amazon_sale_order = sale_order
#                 if not amazon_sale_order.amz_fulfillment_instance_id:
#                     amazon_sale_order.write({
#                         'amz_instance_id': instance.id,
#                         'amz_fulfillment_instance_id': instance.id,
#                         'amz_fulfillment_action': fulfillment_action,
#                         'warehouse_id': fba_warehouse and fba_warehouse.id or False,
#                         'pricelist_id': instance.pricelist_id and instance.pricelist_id.id or False,
#                         'amz_fulfillment_policy': fulfillment_policy,                                
#                         'amz_shipment_service_level_category': shipment_service_level_category,
#                         'amz_is_outbound_order': True,
#                         'notify_by_email': notify_by_email,
#                         'amazon_reference': sale_order.name,
#                         'note':sale_order.note or sale_order.name
#                         
#                     })
#                 create_order=True
#                 for line in amazon_sale_order.order_line:
#                     if line.product_id.type=='service':
#                         continue
#                     if line.product_id:
#                         amz_product = amazon_product_obj.search([('product_id','=',line.product_id and line.product_id.id),('instance_id','=',instance.id),('fulfillment_by','=','AFN')],limit=1)
#                         if not amz_product:
#                             create_order=False
#                             break
#                         line.write({'amazon_product_id': amz_product.id})
#                 if create_order:
#                     try:
#                         mws_obj.CreateFulfillmentOrder(amazon_sale_order)
#                         self._cr.commit()
#                     except Exception as e:                       
#                         pass 
#        return True
        
        
        
        