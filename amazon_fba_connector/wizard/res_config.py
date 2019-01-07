from odoo import models,fields,api,_
from odoo.exceptions import Warning
from datetime import datetime        
from dateutil.relativedelta import relativedelta

_intervalTypes = {
#     'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}



"""added by Dhruvi [17-08-2018]
method to create unsellable location when seller is created form wizard and set value of
default FBA partner"""
class amazon_seller_config_ept(models.TransientModel):
    _inherit = 'res.config.amazon.seller'
    
    
    @api.multi
    def test_amazon_connection(self):
        amazon_seller_obj = self.env['amazon.seller.ept']
        result = super(amazon_seller_config_ept,self).test_amazon_connection()
        seller_id = amazon_seller_obj.browse([(result.get('seller_id'))])
        self.create_unsellable_location(seller_id)
        self.update_reimbursement_details(seller_id)
        
        action = self.env.ref('amazon_ept.action_amazon_configuration', False)
        res = action and action.read()[0] or {}
        res.update({'seller_id':seller_id.id})
        return res

    @api.one
    def create_unsellable_location(self,seller):
        stock_location_obj = self.env['stock.location']
        unsellable_vals={
            'name':seller.name+" Unsellable",
            'usage':'internal',
            'company_id':seller.company_id.id
            }
        location = stock_location_obj.create(unsellable_vals)
        seller.update({'unsellable_location_id':location.id})
        return True
    
    @api.one
    def update_reimbursement_details(self,seller):
        prod_obj = self.env['product.product']
        partner_obj = self.env['res.partner']
        product = prod_obj.search([('default_code','=','REIMBURSEMENT'),('type','=','service')])
        
        vals = {'name':'Amazon Reimbursement'}
        partner_id = partner_obj.create(vals)
        
        seller.update({'reimbursement_customer_id':partner_id.id,'reimbursement_product_id':product.id})
        return True
        
"""Added by Dhruvi [13-08-2018] 
Inherited Marketplace wizard to set FBA warehouse"""
class amazon_marketplace_config(models.TransientModel):
    _inherit = 'res.config.amazon.marketplace'
       
    """Added by Dhruvi [29-08-2018]
    Method to search FBM warehouse [default or according to seller wise or according to company of user
    and is_fba should be False]"""
    @api.multi
    def search_warehouse(self,company_id):
        default_warehouse = self.env.ref('stock.warehouse0')
        if self.seller_id.company_id == default_warehouse.company_id:
            warehouse_id = default_warehouse.id
        else:    
            warehouse = self.env['stock.warehouse'].search([('company_id','=',company_id.id),('is_fba_warehouse','=',False)])
            if warehouse:
                warehouse_id = warehouse[0].id
            else:
                warehouse = self.env['stock.warehouse'].search([])
                warehouse_id = warehouse and warehouse[0].id
                
        return warehouse_id
    
    def prepare_marketplace_vals(self,marketplace,warehouse_id,company_id,lang_id):
        vals = super(amazon_marketplace_config, self).prepare_marketplace_vals(marketplace,warehouse_id,company_id,lang_id)
        vals.update({'unsellable_location_id':self.seller_id.unsellable_location_id.id or False})
        return vals
      
    @api.multi
    def create_marketplace(self):
        res = super(amazon_marketplace_config,self).create_marketplace()
        stock_warehouse_obj = self.env['stock.warehouse']
        stock_location_obj = self.env['stock.location']
        procurement_rule_obj = self.env['stock.rule']
        amazon_fulfillment_code_obj = self.env['amazon.fulfillment.country.rel']
        amazon_instance_obj = self.env['amazon.instance.ept']
        amazon_instance_ids = amazon_instance_obj.browse(res[0])
        instance_check = amazon_instance_obj.search([('seller_id','=',self.seller_id.id),('fba_warehouse_id','!=',False)])
        if not instance_check:
            loc_vals = {'name':self.seller_id.name,
                            'usage':'view',
                            'company_id':self.seller_id.company_id.id,
                            'location_id': self.env.ref('stock.stock_location_locations').id
                    }
            view_location_id = stock_location_obj.create(loc_vals).id
               
            lot_loc_vals ={'name': _('Stock'), 
                           'active': True, 
                           'usage': 'internal',
                           'company_id':self.seller_id.company_id.id,
                           'location_id':view_location_id}
            lot_stock_id = stock_location_obj.create(lot_loc_vals).id
        else:
            view_location_id =instance_check[0].fba_warehouse_id.view_location_id.id
            lot_stock_id = instance_check[0].fba_warehouse_id.lot_stock_id.id 
        for instance in amazon_instance_ids:
            if instance.marketplace_id.name.find('.') != -1:
                name=instance.marketplace_id.name.rsplit('.',1)
                code=self.seller_id.short_code+""+name[1]
            else:
                code=self.seller_id.short_code+""+instance.marketplace_id.name

            warehouse_id = stock_warehouse_obj.search([('code','=',code)])
            if warehouse_id:
                instance.update({'fba_warehouse_id':warehouse_id.id})
            else:
                vals = {'name':'FBA %s(%s)'%(instance.marketplace_id.name,self.seller_id.name),
                  'is_fba_warehouse':True,
                  'code':code,
                  'company_id':self.seller_id.company_id.id,
                  'view_location_id':view_location_id,
                  'lot_stock_id':lot_stock_id,
                  'seller_id':self.seller_id.id,
                  'unsellable_location_id':self.seller_id.unsellable_location_id.id
                  }
                fbawarehouse_id = stock_warehouse_obj.create(vals)
                #fbawarehouse_id = stock_warehouse_obj.search([('seller_id','=',self.seller_id.id),('is_fba_warehouse','=',True)],limit=1)
                fbawarehouse_id.update({'view_location_id':view_location_id,'lot_stock_id':lot_stock_id})
                #self.fba_warehouse_id = fbawarehouse_id.id
                rule_id= procurement_rule_obj.search([('action','=','move'),('procure_method','=','make_to_stock'),('location_id.usage','=','customer'),('warehouse_id','=',fbawarehouse_id.id)])
                rule_id.update({'location_src_id':lot_stock_id})
                instance.write({'fba_warehouse_id':fbawarehouse_id.id})
                amazon_fulfillment_code_obj.load_fulfillment_code(fbawarehouse_id)
        return True
    
"""Added by Dhruvi
Method to load all fulfillmentcenter code according to country wise"""
class AmazonFulfillmentCenterCode(models.Model):
    _inherit = "amazon.fulfillment.country.rel"
    
    @api.model
    def load_fulfillment_code(self,warehouse):
        fulfillment_center_obj=self.env['amazon.fulfillment.center']
        amazon_instance = self.env['amazon.instance.ept'].search([('fba_warehouse_id','=',warehouse.id)])
        country=amazon_instance.country_id
        if country:
            amazon_fulfillment=self.search([('country_id','=',country.id)])
            for fulfillment in amazon_fulfillment:    
                fulfillment_center_obj.create(
                    {'center_code':fulfillment.fulfillment_code,
                     'seller_id':amazon_instance.seller_id.id,
                     'warehouse_id':warehouse.id
                    })
        
          
class amazon_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    
    help_fulfillment_action = """ 
        Ship - The fulfillment order ships now

        Hold - An order hold is put on the fulfillment order.3

        Default: Ship in Create Fulfillment
        Default: Hold in Update Fulfillment    
    """
    
    help_fulfillment_policy = """ 

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
    
    def_fba_warehouse_id = fields.Many2one('stock.warehouse', string='FBA Warehouse')
    validate_stock_inventory_for_report = fields.Boolean("Auto Validate Amazon FBA Live Stock Report")
    def_fba_partner_id = fields.Many2one('res.partner', string='Default Customer for FBA pending order')
    
    stock_auto_import_by_report = fields.Boolean(string='Auto Import FBA Live Stock Report?')
    inventory_import_next_execution = fields.Datetime('Inventory Import Next Execution', help='Next execution time')
    inventory_import_interval_number = fields.Integer('Import stock Interval Number',help="Repeat every x.")
    inventory_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Stock Interval Unit')
    inventory_import_user_id=fields.Many2one("res.users",string="Inventory Import User")
    
    auto_process_fba_live_stock_report = fields.Boolean(string='Auto Process FBA Live Stock Report?')
    process_fba_live_stock_next_execution = fields.Datetime('FBA Live Stock Next Execution', help='Next execution time')
    process_fba_live_stock_interval_number = fields.Integer('FBA Live Stock Interval Number',help="Repeat every x.")
    process_fba_live_stock_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'FBA Live Stock Interval Unit')
    process_fba_live_stock_user_id = fields.Many2one("res.users",string="FBA Live Stock User")
    
    fba_auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Auto Workflow (FBA)')
    
    auto_import_shipment_report = fields.Boolean(string='Auto Import FBA Shipment Report?')
    ship_report_import_next_execution = fields.Datetime('Ship Report Import Next Execution', help='Next execution time')
    ship_report_import_interval_number = fields.Integer('Import Shipment Report Interval Number',help="Repeat every x.")
    ship_report_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Shipment Report Unit')
    ship_report_import_user_id=fields.Many2one("res.users",string="Ship Report Import User")
    
    auto_process_shipment_report = fields.Boolean(string='Auto Process FBA Shipment Report?')
    ship_report_process_next_execution = fields.Datetime('Ship Report Processs Next Execution', help='Next execution time')
    ship_report_process_interval_number = fields.Integer('Process Shipment Report Interval Number',help="Repeat every x.")
    ship_report_process_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Process Shipment Report Unit')
    ship_report_process_user_id=fields.Many2one("res.users",string="Ship Report Process User")
        
    auto_import_fba_pending_order = fields.Boolean(string='Auto Import FBA Pending Order?')
    pending_order_next_execution = fields.Datetime('Pending Order Next Execution', help='Next execution time')
    pending_order_import_interval_number = fields.Integer('Pending Order Interval Number',help="Repeat every x.")
    pending_order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Pending Order Unit')
    pending_order_import_user_id=fields.Many2one("res.users",string="Pending Order Import User")

    auto_import_inboud_shipment_status = fields.Boolean(string='Auto Import FBA Inbound Shipment Item Status?')
    shipment_status_import_next_execution = fields.Datetime('Shipment Status Next Execution', help='Next execution time')
    shipment_status_import_interval_number = fields.Integer('Shipment Status Interval Number',help="Repeat every x.")
    shipment_status_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Shipment Status Unit')        
    shipment_status_import_user_id=fields.Many2one("res.users",string="Shipment Status Import User")

    auto_import_return_report = fields.Boolean(string='Auto Import FBA Customer Return Report?')
    return_report_import_next_execution = fields.Datetime('Import Return Report Next Execution', help='Next execution time')
    return_report_import_interval_number = fields.Integer('Import Return Report Interval Number',help="Repeat every x.")
    return_report_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Return Report Unit')
    return_report_import_user_id=fields.Many2one("res.users",string="Import Return Report User")
    
    auto_process_return_report = fields.Boolean(string='Auto Process FBA Customer Returns?')
    return_process_report_next_execution = fields.Datetime('Process Return Report Next Execution', help='Next execution time')
    return_process_report_interval_number = fields.Integer('Process Return Report Interval Number',help="Repeat every x.")
    return_process_report_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Process Return Report Unit')
    return_process_report_user_id=fields.Many2one("res.users",string="Process Return Report User")

    auto_update_small_parcel_tracking = fields.Boolean(string='Auto Update Small Parcel Tracking')
    small_parcel_next_execution = fields.Datetime('Small Parcel Next Execution', help='Next execution time')
    small_parcel_interval_number = fields.Integer('Small Parcel Interval Number',help="Repeat every x.")
    small_parcel_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Small Parcel Interval Unit')
    small_parcel_user_id=fields.Many2one("res.users",string="Small Parcel User")

    auto_check_cancel_order = fields.Boolean(string='Auto Check Canceled FBA Order in Amazon?')
    cancel_order_next_execution = fields.Datetime('Cancel Order Next Execution', help='Next execution time')
    cancel_order_interval_number = fields.Integer('Cancel Order Interval Number',help="Repeat every x.")
    cancel_order_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Cancel Order Interval Unit')
    cancel_order_report_user_id=fields.Many2one("res.users",string="Cancel Order User")

    #Inbound Shipment
    allow_process_unshipped_products=fields.Boolean("Allow Process Unshipped Products in Inbound Shipment ?",default=True)
    update_partially_inbound_shipment=fields.Boolean('Allow Update Partially Inbound Shipment ?',default=False)
    is_allow_prep_instruction = fields.Boolean(string="Allow Prep Instruction in Inbound Shipment ?",default=False,help="Amazon FBA: If ticked then allow to pass the prep-instructions details during create Inbount Shipment Plan in Amazon.")
    check_status_days = fields.Integer("Check Status Days",default=30,help="System will check status after closed shipment.")
    
    auto_update_ltl_parcel_tracking = fields.Boolean(string='Auto Update LTL Tracking')
    ltl_parcel_next_execution = fields.Datetime('LTL Parcel Next Execution', help='Next execution time')
    ltl_parcel_interval_number = fields.Integer('LTL Parcel Interval Number',help="Repeat every x.")
    ltl_parcel_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'LTL Parcel Interval Unit')
    ltl_parcel_user_id=fields.Many2one("res.users",string="LTL Parcel User")

    process_reimbursed_lines_in_return_report=fields.Boolean(string="Process Reimbursed Lines In Return Report",default=False)
    reimbursed_warehouse_id=fields.Many2one("stock.warehouse", string="Reimbursed warehouse id")    
    is_another_soft_create_fba_shipment=fields.Boolean(string="Does another software create the FBA shipment reports?",default=False)
    
    # Unsellable Location
    unsellable_location_id = fields.Many2one('stock.location',string="Unsellable Location",help="Select instance wise amazon unsellable location")
    
    # Outbound Orders
    is_auto_create_outbound_order = fields.Boolean(string="Auto Create Outbound Order ?",default=False,help="This box is ticked to automatically create Outbound Order.") 
    auto_create_outbound_order_interval_number = fields.Integer("Outbound Order Interval Number",help="Repeat every x.")
    auto_create_outbound_order_interval_type = fields.Selection(
        [('minutes', 'Minutes'),
         ('hours','Hours'),
         ('days', 'Days'),
         ('weeks', 'Weeks'), 
         ('months', 'Months')],"Auto Create Outbound Interval Unit")
    auto_create_outbound_order_next_execution = fields.Datetime("Outbound Order Next Execution", help="Next execution time")
    auto_create_outbound_order_user_id = fields.Many2one("res.users",string="User Name")
    
    fulfillment_action = fields.Selection([('Ship', 'Ship'), ('Hold', 'Hold')], string="Fulfillment Action",
                                          default="Hold", help=help_fulfillment_action)
    shipment_service_level_category = fields.Selection(
        [('Expedited', 'Expedited'), ('NextDay', 'NextDay'), ('SecondDay', 'SecondDay'), ('Standard', 'Standard'),
         ('Priority', 'Priority'), ('ScheduledDelivery', 'ScheduledDelivery')], "Shipment Category", default='Standard', help="Amazon shipment category")
    fulfillment_policy = fields.Selection(
        [('FillOrKill', 'FillOrKill'), ('FillAll', 'FillAll'), ('FillAllAvailable', 'FillAllAvailable')],
        string="Fulfillment Policy", default="FillOrKill", help=help_fulfillment_policy)
    notify_by_email = fields.Boolean("Notify By Email", default=False, help="If true then system will notify by email to followers")
    
    #added by Dhruvi
    install_fba_reimbursement = fields.Boolean(string="Track Amazon FBA Reimbursement?")#for FBA reimbursement
    import_inbound_shipment = fields.Boolean(string="Import inbound shipment from Amazon?")#for inbound shipment
    manage_removal_order = fields.Boolean(string="Manage Removal Order")#for managing removal order
    track_fba_inventory = fields.Boolean(string="Track & Process FBA Inventory Adjustment?")#for tracking inventory
    buynow_fba_reimbursement = fields.Boolean(string="Buy now FBA Reimbursement")
    buynow_import_inbound_shipment = fields.Boolean(string="Buy now Import Inbound Shipment")
    buynow_manage_removal_order = fields.Boolean(string="Buy now Manage Removal Order")
    buynow_manage_track_fba_inventory = fields.Boolean(string="Buy now Manage Track FBA Inventory")
    create_inventory = fields.Boolean(string="Create Inventory ?")
    
    #added by dhaval
    is_default_odoo_sequence_in_sales_order_fba = fields.Boolean("Is default Odoo Sequence In Sales Orders (FBA) ?")
    
    @api.model
    def default_get(self, fields):
        res = super(amazon_config_settings, self).default_get(fields)  
        
        check_install_fba_reimbursement = self.env['ir.module.module'].search([('name', '=', 'amazon_reimbursement_ept')])
        reimbursement =False
        buynow_fba_reimbursement = False
        if check_install_fba_reimbursement and check_install_fba_reimbursement.state == "installed":
            reimbursement = True
        if not check_install_fba_reimbursement:
            buynow_fba_reimbursement = True
        res.update({'install_fba_reimbursement' : reimbursement,'buynow_fba_reimbursement':buynow_fba_reimbursement})
    
        check_import_inbound_shipment = self.env['ir.module.module'].search([('name', '=', 'amazon_import_shipment_plan_ept')])
        import_inbound = False
        buynow_import_inbound_shipment = False
        if check_import_inbound_shipment and check_import_inbound_shipment.state == "installed":
            import_inbound = True
        if not check_import_inbound_shipment:
            buynow_import_inbound_shipment = True
        res.update({'import_inbound_shipment' : import_inbound,'buynow_import_inbound_shipment':buynow_import_inbound_shipment})
    
        check_manage_removal_order = self.env['ir.module.module'].search([('name', '=', 'amazon_removal_order_ept')])
        removal_order = False
        buynow_manage_removal_order = False
        if check_manage_removal_order and check_manage_removal_order.state == "installed":
            removal_order = True
        if not check_manage_removal_order:
            buynow_manage_removal_order = True
        res.update({'manage_removal_order' : removal_order,'buynow_manage_removal_order':buynow_manage_removal_order})
            
        check_track_fba_inventory = self.env['ir.module.module'].search([('name', '=', 'amazon_stock_adjustment_report_ept')])
        track_fba = False
        buynow_manage_track_fba_inventory = False
        if check_track_fba_inventory and check_track_fba_inventory.state == "installed":
            track_fba = True
        if not check_track_fba_inventory:
            buynow_manage_track_fba_inventory = True
        res.update({'track_fba_inventory' : track_fba,'buynow_manage_track_fba_inventory':buynow_manage_track_fba_inventory})
        
        return res
    
    
    @api.one
    @api.constrains('warehouse_id','company_id')
    def onchange_company_fba_warehouse_id(self):
        if self.def_fba_warehouse_id and self.company_id and self.def_fba_warehouse_id.company_id.id != self.company_id.id:
            raise Warning("Company in FBA warehouse is different than the selected company. Selected Company and Company in FBA Warehouse must be same.")
     
    @api.onchange('seller_id')
    def onchange_seller_id(self):
        values = super(amazon_config_settings,self).onchange_seller_id()#seller_id,instance_id,product_ads_account
        if not values.get('value'):
            values['value'] = {}
        if self.seller_id:
            seller = self.seller_id
            values['value']['auto_import_shipment_report'] = seller.auto_import_shipment_report or False
            values['value']['auto_process_shipment_report'] = seller.auto_process_shipment_report or False
            values['value']['auto_import_return_report'] = seller.auto_import_return_report or False
            values['value']['auto_process_return_report'] = seller.auto_process_return_report or False
            values['value']['auto_check_cancel_order'] = seller.auto_check_cancel_order or False
            values['value']['auto_import_fba_pending_order'] = seller.auto_import_fba_pending_order or False
            values['value']['auto_import_inboud_shipment_status'] = seller.auto_import_inboud_shipment_status or False
            values['value']['auto_update_small_parcel_tracking'] = seller.auto_update_small_parcel_tracking or False
            values['value']['auto_update_ltl_parcel_tracking'] = seller.auto_update_ltl_parcel_tracking or False
            values['value']['reimbursed_warehouse_id']=seller.reimbursed_warehouse_id.id or False            

            values['value']['is_another_soft_create_fba_shipment'] = seller.is_another_soft_create_fba_shipment or False             
			
			#added by dhaval
            values['value']['is_default_odoo_sequence_in_sales_order_fba']=seller.is_default_odoo_sequence_in_sales_order_fba or False
			
            #added by Dhruvi
            values['value']['create_inventory'] = seller.create_inventory or False     
            values['value']['def_fba_partner_id'] = seller.def_fba_partner_id and seller.def_fba_partner_id.id  or False
            values['value']['is_auto_create_outbound_order'] = seller.is_auto_create_outbound_order or False
            values['value']['fulfillment_action'] = seller.fulfillment_action or False
            values['value']['shipment_service_level_category'] = seller.shipment_service_level_category or False
            values['value']['fulfillment_policy'] = seller.fulfillment_policy or False
            values['value']['notify_by_email'] =  seller.notify_by_email or False 
            values['value']['fba_auto_workflow_id'] = seller.fba_auto_workflow_id and seller.fba_auto_workflow_id.id or False
            
            #added by Dhruvi
            auto_create_outbound_order_cron_exist = self.env.ref("amazon_fba_connector.ir_cron_auto_create_outbound_order_instance_%d"%(seller.id),raise_if_not_found=False)
            if auto_create_outbound_order_cron_exist:
                values['value']['auto_create_outbound_order_interval_number'] = auto_create_outbound_order_cron_exist.interval_number or False
                values['value']['auto_create_outbound_order_interval_type'] = auto_create_outbound_order_cron_exist.interval_type or False
                values['value']['auto_create_outbound_order_next_execution'] = auto_create_outbound_order_cron_exist.nextcall or False
                values['value']['auto_create_outbound_order_user_id'] = auto_create_outbound_order_cron_exist.user_id.id or False

            
            import_pending_order_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_import_amazon_fba_pending_order_seller_%d'%(seller.id),raise_if_not_found=False)
            if import_pending_order_cron_exist:
                values['value']['pending_order_import_interval_number'] = import_pending_order_cron_exist.interval_number or False
                values['value']['pending_order_import_interval_type'] = import_pending_order_cron_exist.interval_type or False                
                values['value']['pending_order_next_execution'] = import_pending_order_cron_exist.nextcall or False
                values['value']['pending_order_import_user_id']=  import_pending_order_cron_exist.user_id.id or False          
            import_ship_report_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_import_amazon_fba_shipment_report_seller_%d'%(seller),raise_if_not_found=False)
            if import_ship_report_cron_exist:
                values['value']['ship_report_import_interval_number'] = import_ship_report_cron_exist.interval_number or False
                values['value']['ship_report_import_interval_type'] = import_ship_report_cron_exist.interval_type or False
                values['value']['ship_report_import_next_execution'] = import_ship_report_cron_exist.nextcall or False
                values['value']['ship_report_import_user_id']=  import_ship_report_cron_exist.user_id.id or False          
                
            process_ship_report_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_process_amazon_fba_shipment_report_seller_%d'%(seller),raise_if_not_found=False)
            if process_ship_report_cron_exist:
                values['value']['ship_report_process_interval_number'] = process_ship_report_cron_exist.interval_number or False
                values['value']['ship_report_process_interval_type'] = process_ship_report_cron_exist.interval_type or False
                values['value']['ship_report_process_next_execution'] = process_ship_report_cron_exist.nextcall or False
                values['value']['ship_report_process_user_id'] = process_ship_report_cron_exist.user_id.id or False
                
            import_return_report_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_auto_import_customer_return_report_seller_%d'%(seller),raise_if_not_found=False)
            if import_return_report_cron_exist:
                values['value']['return_report_import_interval_number'] = import_return_report_cron_exist.interval_number or False
                values['value']['return_report_import_interval_type'] = import_return_report_cron_exist.interval_type or False
                values['value']['return_report_import_next_execution'] = import_return_report_cron_exist.nextcall or False
                values['value']['return_report_import_user_id'] = import_return_report_cron_exist.user_id.id or False
                
            process_return_report_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_auto_process_customer_return_report_seller_%d'%(seller),raise_if_not_found=False)
            if process_return_report_cron_exist:
                values['value']['return_process_report_interval_number'] = process_return_report_cron_exist.interval_number or False
                values['value']['return_process_report_interval_type'] = process_return_report_cron_exist.interval_type or False
                values['value']['return_process_report_next_execution'] = process_return_report_cron_exist.nextcall or False
                values['value']['return_process_report_user_id'] = process_return_report_cron_exist.user_id.id or False
                
            cancel_order_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_auto_check_canceled_order_in_amazon_seller_%d'%(seller),raise_if_not_found=False)
            if cancel_order_cron_exist:
                values['value']['cancel_order_interval_number'] = cancel_order_cron_exist.interval_number or False
                values['value']['cancel_order_interval_type'] = cancel_order_cron_exist.interval_type or False
                values['value']['cancel_order_next_execution'] = cancel_order_cron_exist.nextcall or False
                values['value']['cancel_order_report_user_id'] = cancel_order_cron_exist.user_id.id or False
                
            import_inbound_shipment_status_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_import_inbound_shipment_item_status_seller_%d'%(seller.id),raise_if_not_found=False)
            if import_inbound_shipment_status_cron_exist:
                values['value']['shipment_status_import_interval_number'] = import_inbound_shipment_status_cron_exist.interval_number or False
                values['value']['shipment_status_import_interval_type'] = import_inbound_shipment_status_cron_exist.interval_type or False
                values['value']['shipment_status_import_next_execution'] = import_inbound_shipment_status_cron_exist.nextcall or False
                values['value']['shipment_status_import_user_id'] = import_inbound_shipment_status_cron_exist.user_id.id or False
                
            auto_update_small_parcel_tracking_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_auto_update_fba_small_parcel_shipment_tracking_seller_%d'%(seller.id),raise_if_not_found=False)
            if auto_update_small_parcel_tracking_cron_exist:
                values['value']['small_parcel_interval_number'] = auto_update_small_parcel_tracking_cron_exist.interval_number or False
                values['value']['small_parcel_interval_type'] = auto_update_small_parcel_tracking_cron_exist.interval_type or False
                values['value']['small_parcel_next_execution'] = auto_update_small_parcel_tracking_cron_exist.nextcall or False        
                values['value']['small_parcel_user_id'] = auto_update_small_parcel_tracking_cron_exist.user_id.id or False        
                                            
            auto_update_ltl_tracking_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_auto_update_fba_ltl_shipment_tracking_seller_%d'%(seller.id),raise_if_not_found=False)
            if auto_update_ltl_tracking_cron_exist:
                values['value']['ltl_parcel_interval_number'] = auto_update_ltl_tracking_cron_exist.interval_number or False
                values['value']['ltl_parcel_interval_type'] = auto_update_ltl_tracking_cron_exist.interval_type or False
                values['value']['ltl_parcel_next_execution'] = auto_update_ltl_tracking_cron_exist.nextcall or False                                                    
                values['value']['ltl_parcel_user_id'] = auto_update_ltl_tracking_cron_exist.user_id.id or False                                                    

        else:
            values['value']['ship_report_import_interval_number'] = False
            values['value']['ship_report_import_interval_type'] = False
            values['value']['ship_report_process_interval_number'] = False
            values['value']['ship_report_process_interval_type'] = False
            values['value']['return_report_import_interval_number'] = False
            values['value']['return_report_import_interval_type'] = False
            values['value']['return_process_report_interval_number'] = False
            values['value']['return_process_report_interval_type'] = False
            values['value']['cancel_order_interval_number'] = False
            values['value']['cancel_order_interval_type'] = False
            values['value']['pending_order_import_interval_number'] = False
            values['value']['pending_order_import_interval_type'] = False                                    
        return values
          
    @api.onchange('instance_id')
    def onchange_instance_id(self):
        values = super(amazon_config_settings,self).onchange_instance_id()#,instance,product_ads_account
        if not values.get('value'):
            values['value'] = {}
        instance = self.instance_id 
        if instance:                                    
            values['value']['def_fba_warehouse_id'] = instance.fba_warehouse_id and instance.fba_warehouse_id.id or False
            #self.fba_warehouse_id = instance.fba_warehouse_id and instance.fba_warehouse_id.id or False
            values['value']['validate_stock_inventory_for_report'] = instance.validate_stock_inventory_for_report or False
            values['value']['stock_auto_import_by_report'] = instance.stock_auto_import_by_report or False
            values['value']['auto_process_fba_live_stock_report']=instance.auto_process_fba_live_stock_report or False
            values['value']['allow_process_unshipped_products']=instance.allow_process_unshipped_products or False
            values['value']['update_partially_inbound_shipment']=instance.update_partially_inbound_shipment or False
            
            """Commented by Dhruvi as these field are added to amazon seller"""
#             values['value']['default_fba_partner_id'] = instance.default_fba_partner_id and instance.default_fba_partner_id.id or False
#             values['value']['is_auto_create_outbound_order'] = instance.is_auto_create_outbound_order or False
#             values['value']['fulfillment_action'] = instance.fulfillment_action
#             values['value']['shipment_service_level_category'] = instance.shipment_service_level_category
#             values['value']['fulfillment_policy'] = instance.fulfillment_policy
#             values['value']['notify_by_email'] =  instance.notify_by_email or False
#             values['value']['fba_auto_workflow_id'] = instance.fba_auto_workflow_id and instance.fba_auto_workflow_id.id or False

            values['value']['check_status_days'] = instance.check_status_days            
            values['value']['unsellable_location_id'] = instance.unsellable_location_id and instance.unsellable_location_id.id or False
            values['value']['is_allow_prep_instruction'] = instance.is_allow_prep_instruction or False
            


            
            import_inventory_cron_exist = self.env.ref('amazon_fba_connector.ir_cron_import_stock_from_amazon_fba_live_report_instance_%d'%(instance.id),raise_if_not_found=False)
            if import_inventory_cron_exist:
                values['value']['inventory_import_interval_number'] = import_inventory_cron_exist.interval_number or False
                values['value']['inventory_import_interval_type'] = import_inventory_cron_exist.interval_type or False
                values['value']['inventory_import_next_execution'] = import_inventory_cron_exist.nextcall or False
                values['value']['inventory_import_user_id'] = import_inventory_cron_exist.user_id.id or False
                
            process_fba_live_stock_report_cron_exist=self.env.ref('amazon_fba_connector.ir_cron_process_fba_live_stock_report_instance_%d'%(instance.id),raise_if_not_found=False)
            if process_fba_live_stock_report_cron_exist:
                values['value']['process_fba_live_stock_interval_number']=process_fba_live_stock_report_cron_exist.interval_number or False
                values['value']['process_fba_live_stock_interval_type']=process_fba_live_stock_report_cron_exist.interval_type or False
                values['value']['process_fba_live_stock_next_execution']=process_fba_live_stock_report_cron_exist.nextcall or False
                values['value']['process_fba_live_stock_user_id']=process_fba_live_stock_report_cron_exist.user_id.id or False    
            
            """Commented by Dhruvi as this cron is being set according to seller wise."""
#             auto_create_outbound_order_cron_exist = self.env.ref("amazon_fba_connector.ir_cron_auto_create_outbound_order_instance_%d"%(instance.id),raise_if_not_found=False)
#             if auto_create_outbound_order_cron_exist:
#                 values['value']['auto_create_outbound_order_interval_number'] = auto_create_outbound_order_cron_exist.interval_number or False
#                 values['value']['auto_create_outbound_order_interval_type'] = auto_create_outbound_order_cron_exist.interval_type or False
#                 values['value']['auto_create_outbound_order_next_execution'] = auto_create_outbound_order_cron_exist.nextcall or False
#                 values['value']['auto_create_outbound_order_user_id'] = auto_create_outbound_order_cron_exist.user_id.id or False
        return values
    
    @api.multi
    def execute(self):
        #added by Dhruvi
        #to install ,amazon_reimbursement_v11,amazon_import_shipment_plan_ept,amazon_removal_order_ept,amazon_stock_adjustment_report_ept module
       
            
        if self.install_fba_reimbursement:    
            reimbursement_fba_module = self.env['ir.module.module'].search([('name', '=', 'amazon_reimbursement_ept')])
            if not reimbursement_fba_module:
                self.install_fba_reimbursement = False
                self._cr.commit()
                raise Warning('No module HAmazon Reimbursement found')
            if reimbursement_fba_module and reimbursement_fba_module.state=='to install':
                reimbursement_fba_module.button_install_cancel()
                reimbursement_fba_module.button_immediate_install()
            if reimbursement_fba_module and reimbursement_fba_module.state not in ('installed'):
                reimbursement_fba_module.button_immediate_install()
              
        if self.import_inbound_shipment:  
            import_inbound_shipment_module = self.env['ir.module.module'].search([('name', '=', 'amazon_import_shipment_plan_ept')])
            if not import_inbound_shipment_module:
                self.import_inbound_shipment = False
                self._cr.commit()
                raise Warning('No module Amazon Import Shipment Plan found')
            if import_inbound_shipment_module and import_inbound_shipment_module.state=='to install':
                import_inbound_shipment_module.button_install_cancel()
                import_inbound_shipment_module.button_immediate_install()
            if import_inbound_shipment_module and import_inbound_shipment_module.state not in ('installed'):
                import_inbound_shipment_module.button_immediate_install()
              
        if self.manage_removal_order:  
            manage_removal_order_module = self.env['ir.module.module'].search([('name', '=', 'amazon_removal_order_ept')])
            if not manage_removal_order_module:
                self.manage_removal_order = False
                self._cr.commit()
                raise Warning('No module Amazon Removal Order Process')
            if manage_removal_order_module and manage_removal_order_module.state=='to install':
                manage_removal_order_module.button_install_cancel()
                manage_removal_order_module.button_immediate_install()
            if manage_removal_order_module and manage_removal_order_module.state not in ('installed'):
                manage_removal_order_module.button_immediate_install()
               
        if self.track_fba_inventory: 
            track_fba_inventory_module = self.env['ir.module.module'].search([('name', '=', 'amazon_stock_adjustment_report_ept')])
            if not track_fba_inventory_module:
                self.track_fba_inventory = False
                self._cr.commit()
                raise Warning('No module Amazon Stock Adjustment Report Process')
            if track_fba_inventory_module and track_fba_inventory_module.state=='to install':
                track_fba_inventory_module.button_install_cancel()
                track_fba_inventory_module.button_immediate_install()
            if track_fba_inventory_module and track_fba_inventory_module.state not in ('installed'):
                track_fba_inventory_module.button_immediate_install()
                
                
        instance = self.instance_id
        seller = self.seller_id
        values,vals = {},{}
        res = super(amazon_config_settings,self).execute()
        if instance:
            values['fba_warehouse_id'] = self.def_fba_warehouse_id and self.def_fba_warehouse_id.id or False
            values['validate_stock_inventory_for_report'] = self.validate_stock_inventory_for_report or False
            values['stock_auto_import_by_report'] = self.stock_auto_import_by_report or False
            values['auto_process_fba_live_stock_report']=self.auto_process_fba_live_stock_report or False
            
            """Commented by Dhruvi as these fields are being added in amazon seller."""
#             values['default_fba_partner_id'] = self.default_fba_partner_id and self.default_fba_partner_id.id  or False
#             values['is_auto_create_outbound_order'] = self.is_auto_create_outbound_order or False
#             values['fulfillment_action'] = self.fulfillment_action or False
#             values['shipment_service_level_category'] = self.shipment_service_level_category or False
#             values['fulfillment_policy'] = self.fulfillment_policy or False
#             values['notify_by_email'] =  self.notify_by_email or False
#             values['fba_auto_workflow_id'] = self.fba_auto_workflow_id and self.fba_auto_workflow_id.id or False

            values['allow_process_unshipped_products']=self.allow_process_unshipped_products or False
            values['update_partially_inbound_shipment']=self.update_partially_inbound_shipment or False
            values['check_status_days'] = self.check_status_days
            values['unsellable_location_id'] = self.unsellable_location_id and self.unsellable_location_id.id or False

            if self.unsellable_location_id and self.def_fba_warehouse_id:
                self.def_fba_warehouse_id.unsellable_location_id=self.unsellable_location_id.id
      
            values['is_allow_prep_instruction'] = self.is_allow_prep_instruction or False
            
            instance.write(values)
            self.setup_instance_cron(instance,self.stock_auto_import_by_report,self.inventory_import_interval_type,self.inventory_import_interval_number,self.inventory_import_next_execution,self.inventory_import_user_id,'FBM','ir_cron_import_stock_from_amazon_fba_live_report')
            self.setup_instance_cron(instance,self.auto_process_fba_live_stock_report, self.process_fba_live_stock_interval_type, self.process_fba_live_stock_interval_number, self.process_fba_live_stock_next_execution,self.process_fba_live_stock_user_id,'FBA', 'ir_cron_process_fba_live_stock_report')
            
            """Commented by Dhruvi as these cron is now according to seller wise."""                        
#             self.setup_instance_cron(instance,self.is_auto_create_outbound_order,self.auto_create_outbound_order_interval_type,self.auto_create_outbound_order_interval_number,self.auto_create_outbound_order_next_execution,self.auto_create_outbound_order_user_id,'FBA','ir_cron_auto_create_outbound_order')
        if seller:
            vals['auto_update_small_parcel_tracking'] = self.auto_update_small_parcel_tracking or False
            vals['auto_update_ltl_parcel_tracking']=self.auto_update_ltl_parcel_tracking or False
            vals['auto_import_shipment_report'] = self.auto_import_shipment_report or False
            vals['auto_process_shipment_report'] = self.auto_process_shipment_report or False
            vals['auto_import_return_report'] = self.auto_import_return_report or False
            vals['auto_process_return_report'] = self.auto_process_return_report or False
            vals['auto_check_cancel_order'] = self.auto_check_cancel_order or False
            vals['auto_import_fba_pending_order'] = self.auto_import_fba_pending_order or False
            vals['auto_import_inboud_shipment_status'] = self.auto_import_inboud_shipment_status or False
            vals['reimbursed_warehouse_id']=self.reimbursed_warehouse_id.id or False
            vals['is_another_soft_create_fba_shipment'] = self.is_another_soft_create_fba_shipment or False
            
            """Added by Dhruvi"""
            vals['create_inventory'] = self.create_inventory or False
            vals['def_fba_partner_id'] = self.def_fba_partner_id and self.def_fba_partner_id.id  or False
            vals['is_auto_create_outbound_order'] = self.is_auto_create_outbound_order or False
            vals['fulfillment_action'] = self.fulfillment_action or False
            vals['shipment_service_level_category'] = self.shipment_service_level_category or False
            vals['fulfillment_policy'] = self.fulfillment_policy or False
            vals['notify_by_email'] =  self.notify_by_email or False 
            vals['fba_auto_workflow_id'] = self.fba_auto_workflow_id and self.fba_auto_workflow_id.id or False           
            
            #addedd by dhaval
            vals['is_default_odoo_sequence_in_sales_order_fba']=self.is_default_odoo_sequence_in_sales_order_fba or False
            
            seller.write(vals)
            self.setup_seller_cron(seller,self.small_parcel_user_id.id,self.auto_update_small_parcel_tracking,self.small_parcel_interval_type,self.small_parcel_interval_number,self.small_parcel_next_execution,'FBA','ir_cron_auto_update_fba_small_parcel_shipment_tracking')
            self.setup_seller_cron(seller,self.ltl_parcel_user_id.id,self.auto_update_ltl_parcel_tracking,self.ltl_parcel_interval_type,self.ltl_parcel_interval_number,self.ltl_parcel_next_execution,'FBA','ir_cron_auto_update_fba_ltl_shipment_tracking')
            self.setup_seller_cron(seller,self.shipment_status_import_user_id.id,self.auto_import_inboud_shipment_status,self.shipment_status_import_interval_type,self.shipment_status_import_interval_number,self.shipment_status_import_next_execution,'FBA','ir_cron_import_inbound_shipment_item_status')
            self.setup_seller_cron(seller,self.pending_order_import_user_id.id,self.auto_import_fba_pending_order,self.pending_order_import_interval_type,self.pending_order_import_interval_number,self.pending_order_next_execution,'FBA','ir_cron_import_amazon_fba_pending_order')
            self.setup_seller_cron(seller,self.ship_report_import_user_id.id,self.auto_import_shipment_report,self.ship_report_import_interval_type,self.ship_report_import_interval_number,self.ship_report_import_next_execution,'FBA','ir_cron_import_amazon_fba_shipment_report')
            self.setup_seller_cron(seller,self.ship_report_process_user_id.id,self.auto_process_shipment_report,self.ship_report_process_interval_type,self.ship_report_process_interval_number,self.ship_report_process_next_execution,'FBA','ir_cron_process_amazon_fba_shipment_report')
            self.setup_seller_cron(seller,self.return_report_import_user_id.id,self.auto_import_return_report, self.return_report_import_interval_type, self.return_report_import_interval_number,self.return_report_import_next_execution,'FBA', 'ir_cron_auto_import_customer_return_report')
            self.setup_seller_cron(seller,self.return_process_report_user_id.id,self.auto_process_return_report, self.return_process_report_interval_type, self.return_process_report_interval_number,self.return_process_report_next_execution,'FBA', 'ir_cron_auto_process_customer_return_report')
            self.setup_seller_cron(seller,self.cancel_order_report_user_id.id,self.auto_check_cancel_order, self.cancel_order_interval_type, self.cancel_order_interval_number,self.cancel_order_next_execution,'FBA', 'ir_cron_auto_check_canceled_order_in_amazon')
            
            """Added by Dhruvi"""
            self.setup_seller_cron(seller,self.auto_create_outbound_order_user_id.id,self.is_auto_create_outbound_order,self.auto_create_outbound_order_interval_type,self.auto_create_outbound_order_interval_number,self.auto_create_outbound_order_next_execution,'FBA','ir_cron_auto_create_outbound_order')                
        return res

    @api.model   
    def setup_seller_cron(self,seller,user_id,auto_import,interval_type,interval_number,next_call,prefix,cron_xml_id,module='amazon_fba_connector'):
        if auto_import:
            cron_exist = self.env.ref(module+'.'+cron_xml_id+'_seller_%d'%(seller.id),raise_if_not_found=False)
#             nextcall = datetime.now()
#             nextcall += _intervalTypes[interval_type](interval_number)                
            vals = {'active' : True,
                    'interval_number':interval_number,
                    'interval_type':interval_type,
                    'nextcall':next_call,
                    'user_id':user_id,#'code':"model.({'seller_id':%d})"%(seller.id)
                    }
            if cron_xml_id=='ir_cron_auto_check_canceled_order_in_amazon':
                vals.update({'code':"model.auto_check_cancel_order_in_amazon({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_auto_update_fba_ltl_shipment_tracking':
                vals.update({'code':"model.auto_export_ltl_parcel_tracking({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_import_inbound_shipment_item_status':
                vals.update({'code':"model.auto_import_fba_shipment_status_ept({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_import_amazon_fba_pending_order':
                vals.update({'code':"model.auto_import_fba_pending_sale_order_ept({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_process_amazon_fba_shipment_report':
                vals.update({'code':"model.auto_process_shipment_report({'seller_id':%d})"%(seller.id)})            
            if cron_xml_id=='ir_cron_import_amazon_fba_shipment_report':
                vals.update({'code':"model.auto_import_shipment_report({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_check_tracking_details':
                vals.update({'code':"model.update_tracking_status({'seller_id':%d})"%(seller.id)})
            
            if cron_xml_id=='ir_cron_auto_update_fba_small_parcel_shipment_tracking':
                vals.update({'code':"model.auto_export_small_parcel_tracking({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_auto_import_customer_return_report':
                vals.update({'code':"model.auto_import_return_report({'seller_id':%d})"%(seller.id)})
            if cron_xml_id=='ir_cron_auto_process_customer_return_report':
                vals.update({'code':"model.auto_process_return_order_report({'seller_id':%d})"%(seller.id)})
            
            """Added by Dhruvi as these cron is set according to seller wise"""
            if cron_xml_id == "ir_cron_auto_create_outbound_order":
                vals.update({
                    'code': "model.auto_create_outbound_order({'seller_id':%d})"%(seller.id)
                })

            if cron_exist:
                cron_exist.write(vals)
            else:
                import_return_cron = self.env.ref(module+'.'+cron_xml_id,raise_if_not_found=False)
                if not import_return_cron:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                cron_name = import_return_cron.name.replace('(Do Not Delete)','')
                    
                name = prefix and prefix+'-'+seller.name + ' : '+cron_name or seller.name + ' : '+cron_name
                vals.update({'name':name})
                new_cron = import_return_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':module,
                                                  'name':cron_xml_id+'_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref(module+'.'+cron_xml_id+'_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True

    @api.model   
    def setup_instance_cron(self, instance, auto_import, interval_type, interval_number, next_call, cron_user,prefix, cron_xml_id, module='amazon_fba_connector'):
        if auto_import:
            cron_exist = self.env.ref(module+'.'+cron_xml_id+'_instance_%d'%(instance.id),raise_if_not_found=False)
#             nextcall = datetime.now()
#             nextcall += _intervalTypes[interval_type](interval_number)
            vals = {
                        'active' : True,
                        'interval_number':interval_number,
                        'interval_type':interval_type,
                        'nextcall':next_call,
                        'code':"model.({'instance_id':%d})"%(instance.id),
                        'user_id': cron_user and cron_user.id
                        
                    }
            
            if cron_xml_id == 'ir_cron_import_stock_from_amazon_fba_live_report':
                vals.update({
                    'code':"model.auto_import_amazon_fba_live_stock_report({'instance_id':%d})"%(instance.id)
                })
            if cron_xml_id == 'ir_cron_process_fba_live_stock_report':
                vals.update({
                    'code':"model.auto_process_amazon_fba_live_stock_report({'instance_id':%d})"%(instance.id)
                })
            """Commented by Dhruvi as these cron is being set according to seller"""
#             if cron_xml_id == "ir_cron_auto_create_outbound_order":
#                 vals.update({
#                     'code': "model.auto_create_outbound_order({'instance_id':%d})"%(instance.id)
#                 })
                            
            if cron_exist:
                cron_exist.write(vals)
            else:
                import_return_cron = self.env.ref(module+'.'+cron_xml_id,raise_if_not_found=False)
                if not import_return_cron:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                cron_name = import_return_cron.name.replace('(Do Not Delete)','')
                name = prefix and prefix+'-'+instance.name + ' : '+cron_name or instance.name + ' : '+cron_name
                vals.update({'name':name})
                new_cron = import_return_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':module,
                                                  'name':cron_xml_id+'_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref(module+'.'+cron_xml_id+'_instance_%d'%(instance.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True    
    
