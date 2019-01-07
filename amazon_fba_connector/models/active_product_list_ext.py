from odoo import models,fields,api

class active_product_list_ept(models.Model):
    _inherit='active.product.listing.report.ept'
    
    def get_fulfillment_type(self,fulfillment_channel):
        res = super(active_product_list_ept,self).get_fulfillment_type(fulfillment_channel)
        if res:
            return res
        else:
            return 'AFN'