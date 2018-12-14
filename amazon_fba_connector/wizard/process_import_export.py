from odoo import models, fields, api, _
from collections import defaultdict
from odoo.addons.amazon_ept.amazon_emipro_api.mws import Reports
import time

class amazon_process_import_export(models.TransientModel):
    _inherit = 'amazon.process.import.export'
   
    import_fba_pending_sale_order = fields.Boolean('Sale order(Only Pending Orders)', help="System will import pending FBA orders from Amazon")
    check_order_status = fields.Boolean("Check Cancelled Order in Amazon", help="If ticked, system will check the orders status in Amazon for the selected instances and if order is canceled in Amazon, then system will cancel that order is Odoo too.")
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')

    
    @api.multi
    def import_export_processes(self):
        res = super(amazon_process_import_export,self).import_export_processes()
        sale_order_obj = self.env['sale.order']
        # group shipments by seller
        seller_pending_order_marketplaces = defaultdict(list)
        cancel_order_marketplaces = defaultdict(list)
        for instance in self.instance_ids:
            if self.check_order_status:
#                 sale_order_obj.check_cancel_order_in_amazon(instance)
                cancel_order_marketplaces[instance.seller_id].append(instance.market_place_id)    
            if self.import_fba_pending_sale_order:
                seller_pending_order_marketplaces[instance.seller_id].append(instance.market_place_id)

        if cancel_order_marketplaces:
            for seller,marketplaces in cancel_order_marketplaces.items():
                sale_order_obj.check_cancel_order_in_amazon(seller,marketplaceids = marketplaces, instance_ids = self.instance_ids and self.instance_ids.ids or [])
                                
        if seller_pending_order_marketplaces:
            for seller,marketplaces in seller_pending_order_marketplaces.items():
                sale_order_obj.import_fba_pending_sales_order(seller,marketplaces)  
        return res
