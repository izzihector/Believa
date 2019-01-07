from odoo import models,fields,api

class stock_picking(models.Model):
    _inherit='stock.picking'

    amazon_instance_id = fields.Many2one("amazon.instance.ept","Instances")   
    
    is_amazon_delivery_order = fields.Boolean("Amazon Delivery Order",default=False,copy=False)    
    updated_in_amazon=fields.Boolean("Updated In Amazon",default=False,copy=False)
    
    seller_id = fields.Many2one("amazon.seller.ept","Seller")

    @api.multi
    def mark_sent_amazon(self):
        for picking in self:
            picking.write({'updated_in_amazon':False})
        return True
    @api.multi
    def mark_not_sent_amazon(self):
        for picking in self:
            picking.write({'updated_in_amazon':True})
        return True

    
