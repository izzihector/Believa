#!/usr/bin/python3
from odoo import models,fields

class ebay_stock_update_history(models.Model):
    _name="ebay.stock.update.history"
    _description = "eBay Stock Update History"
    
    ebay_product_id=fields.Many2one('ebay.product.product.ept',string="Product")
    last_updated_qty=fields.Integer("Last Updated Qty")
    