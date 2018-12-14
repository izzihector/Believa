from odoo import models,fields,api

class amazon_operations_ept(models.Model):
    _inherit = "amazon.operations.ept"
    @api.model
    def find_amazon_cron(self,action_id):
        cron_ids = super(amazon_operations_ept,self).find_amazon_cron(action_id)
        xml_ids = ['amazon_fba_connector.ir_cron_import_stock_from_amazon_fba',
                   'amazon_fba_connector.ir_cron_process_amazon_fba_shipment_report',
                   'amazon_fba_connector.ir_cron_import_inbound_shipment_item_status',
                   'amazon_fba_connector.ir_cron_import_amazon_fba_shipment_report',
                   'amazon_fba_connector.ir_cron_import_amazon_fba_pending_order',
                   'amazon_fba_connector.ir_cron_auto_import_customer_return_report',
                   'amazon_fba_connector.ir_cron_auto_process_customer_return_report',
                   'amazon_fba_connector.ir_cron_auto_update_fba_small_parcel_shipment_tracking',
                   'amazon_fba_connector.ir_cron_auto_check_canceled_order_in_amazon',
                   ]
        for xml_id in xml_ids:
            cron_exit = self.env.ref(xml_id,raise_if_not_found=False)
            if cron_exit:
                cron_ids.append(cron_exit.id)                
        for instance in self.env['amazon.instance.ept'].search([]):
            for xml_id in xml_ids:
                cron_exit = self.env.ref(xml_id+'_instance_%d'%(instance.id),raise_if_not_found=False)
                if cron_exit:
                    cron_ids.append(cron_exit.id)
                            
        for seller in self.env['amazon.seller.ept'].search([]):
            for xml_id in xml_ids:
                cron_exit = self.env.ref(xml_id+'_seller_%d'%(seller.id),raise_if_not_found=False)
                if cron_exit:
                    cron_ids.append(cron_exit.id)
        return cron_ids
    
    @api.multi
    def count_fba_all(self):
        inbound_shipment_plan_ept_obj=self.env['inbound.shipment.plan.ept']
        inbound_shipment_ept_obj=self.env['amazon.inbound.shipment.ept']
        
        
        for record in self:
            draft_inbound_shipment_plans=inbound_shipment_plan_ept_obj.search([('state','=','draft')])
            record.count_draft_inbound_shipment_plan=len(draft_inbound_shipment_plans.ids)
            approved_inbound_shipment_plans=inbound_shipment_plan_ept_obj.search([('state','=','plan_approved')])
            record.count_approved_inbound_shipment_plan=len(approved_inbound_shipment_plans.ids)
            
            working_inbound_shipments=inbound_shipment_ept_obj.search([('state','=','WORKING')])
            record.count_working_inbound_shipment=len(working_inbound_shipments.ids)            
            shipped_inbound_shipments=inbound_shipment_ept_obj.search([('state','=','SHIPPED')])
            record.count_shipped_inbound_shipment=len(shipped_inbound_shipments.ids)            
            cancelled_inbound_shipments=inbound_shipment_ept_obj.search([('state','=','CANCELLED')])
            record.count_cancelled_inbound_shipment=len(cancelled_inbound_shipments.ids)            
            closed_inbound_shipments=inbound_shipment_ept_obj.search([('state','=','CLOSED')])
            record.count_closed_inbound_shipment=len(closed_inbound_shipments.ids)                                        
    
    use_inbound_shipment_plan = fields.Boolean("Use Inbound Shipment Plan",help="Check This box to manage Inbound Shipment Plan")
    use_inbound_shipment = fields.Boolean("Use Inbound Shipment",help="Check This box to manage Inbound Shipment")
    
    count_draft_inbound_shipment_plan=fields.Integer(string="Count Draft Inbound Shipment Plan",compute="count_fba_all")
    count_approved_inbound_shipment_plan=fields.Integer(string="Count Approved Inbound Shipment Plan",compute="count_fba_all")

    count_working_inbound_shipment=fields.Integer(string="Count Working Inbound Shipment",compute="count_fba_all")
    count_shipped_inbound_shipment=fields.Integer(string="Count Shipped Inbound Shipment",compute="count_fba_all")
    count_cancelled_inbound_shipment=fields.Integer(string="Count Cancelled Inbound Shipment",compute="count_fba_all")
    count_closed_inbound_shipment=fields.Integer(string="Count Closed Inbound Shipment",compute="count_fba_all")