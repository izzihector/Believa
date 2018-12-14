from odoo import models,fields, api
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

class amazon_seller_ept(models.Model):
    _inherit = "amazon.seller.ept"

    #added by Dhruvi    
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
    

    @api.model
    def _default_journal(self):
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [                      
            ('type', 'in', list(filter(None, list(map(TYPE2JOURNAL.get, inv_types))))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    """Added by Dhruvi [28-08-2018]
    method to set default value for default fba customer"""
    @api.model
    def _get_default_fba_partner_id(self):
        
        try:
            return self.env.ref('amazon_fba_connector.amazon_fba_pending_order')
        except:
            pass
     
    @api.model
    def _get_default_fba_auto_workflow(self):
        try:
            return self.env.ref('auto_invoice_workflow_ept.automatic_validation_ept')
        except:
            pass
    auto_process_shipment_report = fields.Boolean(string='Auto Process Shipment Report?')
    auto_import_shipment_report = fields.Boolean(string='Auto Import Shipment Report?')
    shipping_report_last_sync_on = fields.Datetime("Last Shipping Report Request Time")
    return_report_last_sync_on = fields.Datetime("Last Return Report Request Time")
    auto_process_return_report = fields.Boolean(string='Auto Process Return Report?')
    auto_import_return_report = fields.Boolean(string='Auto Import Return Report?')
    auto_check_cancel_order = fields.Boolean(string='Auto chack canceled order in Amazon?')
    auto_import_fba_pending_order = fields.Boolean(string='Auto Import FBA Pending Order?')
    fba_order_last_sync_on = fields.Datetime("Last FBA Order Sync Time")
    fba_pending_order_last_sync_on = fields.Datetime("Last FBA Pending Order Sync Time")
    auto_import_inboud_shipment_status = fields.Boolean(string='Auto Import FBA Inbound Shipment Item Status?')
    auto_update_small_parcel_tracking = fields.Boolean('Auto Update Small Parcel(Non Partnered) Tracking')
    reimbursement_customer_id=fields.Many2one("res.partner",string="Reimbursement Customer")
    reimbursement_product_id=fields.Many2one("product.product",string="Product")
    sale_journal_id = fields.Many2one('account.journal', string='Sales Journal',default=_default_journal,domain=[('type','=','sale')])
    auto_update_ltl_parcel_tracking=fields.Boolean("Auto Update Ltl Parcel Tracking",default=False,copy=False)
    reimbursed_warehouse_id=fields.Many2one("stock.warehouse", string="Reimbursed warehouse id")

    is_another_soft_create_fba_shipment = fields.Boolean(string="Does another software create the FBA shipment reports?",default=False)
    fba_shipment_report_days=fields.Integer("Default Shipment Request Report Days",default=3)
    

    #added by Dhruvi
    create_inventory = fields.Boolean(string="Create Inventory ?")
    def_fba_partner_id = fields.Many2one('res.partner', string='Default Customer for FBA pending order',default=_get_default_fba_partner_id)
    fba_auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Auto Workflow (FBA)',default=_get_default_fba_auto_workflow)
    # Outbound Order
    is_auto_create_outbound_order = fields.Boolean(string="Auto Create Outbound Order ?",default=False,help="This box is ticked to automatically create Outbound Order.")
    fulfillment_action = fields.Selection([('Ship', 'Ship'), ('Hold', 'Hold')], string="Fulfillment Action", help=help_fulfillment_action)
    shipment_service_level_category = fields.Selection(
         [('Expedited', 'Expedited'), ('NextDay', 'NextDay'), ('SecondDay', 'SecondDay'), ('Standard', 'Standard'),
          ('Priority', 'Priority'), ('ScheduledDelivery', 'ScheduledDelivery')], "Shipment Category", help="Amazon shipment category")
    fulfillment_policy = fields.Selection(
         [('FillOrKill', 'FillOrKill'), ('FillAll', 'FillAll'), ('FillAllAvailable', 'FillAllAvailable')], string="Fulfillment Policy", help=help_fulfillment_policy)
    notify_by_email = fields.Boolean("Notify By Email", default=False, help="If true then system will notify by email to followers")    
    unsellable_location_id = fields.Many2one('stock.location',string="Unsellable Location")
    
    #added by dhaval
    is_default_odoo_sequence_in_sales_order_fba = fields.Boolean("Is default Odoo Sequence In Sales Orders (FBA) ?")

    @api.model
    def auto_import_fba_pending_sale_order_ept(self,args={}):
        sale_order_obj = self.env['sale.order']
        seller_id = args.get('seller_id',False)
        if seller_id:
            seller = self.browse(int(seller_id))
            sale_order_obj.import_fba_pending_sales_order(seller)
            seller.write({'fba_order_last_sync_on':datetime.now()})
        return True
        
    @api.model
    def auto_check_cancel_order_in_amazon(self,args={}):
        sale_order_obj=self.env['sale.order']
        seller_id = args.get('seller_id',False)
        if seller_id:
            seller=self.env['amazon.seller.ept'].browse(int(seller_id))
            sale_order_obj.with_context({'auto_process':True}).check_cancel_order_in_amazon(seller)
        return True
        
    @api.model
    def auto_import_fba_shipment_status_ept(self,args={}):
        inbound_shipment_obj=self.env['amazon.inbound.shipment.ept']
        seller_id = args.get('seller_id',False)
        if seller_id:
            instances = self.env['amazon.instance.ept'].search([('seller_id','=',seller_id)])
            shipments=inbound_shipment_obj.search([('state','not in',['draft','CLOSED','CANCELLED','DELETED','ERROR','WORKING']),('shipment_plan_id.instance_id','in',instances.ids)])
            for shipment in shipments:
                shipment.check_status()
                self._cr.commit()
            shipments=inbound_shipment_obj.search([('closed_date','!=',False),('state','in',['CLOSED']),('shipment_plan_id.instance_id.check_status_days','>',0),('shipment_plan_id.instance_id','in',instances.ids),('is_finally_closed','=',False)])
            for shipment in shipments:
                instance=shipment.shipment_plan_id.instance_id
                closed_date=datetime.strptime(shipment.closed_date,"%Y-%m-%d")
                closed_date=date(day=closed_date.day,month=closed_date.month,year=closed_date.year)
                closed_date=closed_date+relativedelta(days=instance.check_status_days)
                today_date=date.today()
                if today_date<=closed_date:
                    shipment.check_status()
                    self._cr.commit()
                over_days=(today_date-closed_date).days
                if over_days>=0:
                    shipment.write({'is_finally_closed':True})     
                    
            shipments = inbound_shipment_obj.search([('state','not in',['draft','CLOSED','CANCELLED','DELETED','ERROR']),('shipment_plan_id.instance_id','in',instances.ids),('is_partnered','=',True),('transport_state','in',['CONFIRMING','CONFIRMED'])])
            for shipment in shipments:
                shipment.check_status()
                self._cr.commit()           
        return True    
                
        
    
