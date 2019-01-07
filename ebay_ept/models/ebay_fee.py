#!/usr/bin/python3
from odoo import models,fields


class ebay_fee(models.Model):
    _name="ebay.fee.ept"
    _description = "eBay Fee"
    
    name=fields.Char("Name")
    currency_id=fields.Many2one("res.currency","Currency")
    value=fields.Float("Value")
    ebay_product_tmpl_id=fields.Many2one("ebay.product.template.ept","Template")
    ebay_variant_id = fields.Many2one('ebay.product.product.ept', string='Variant Name',readonly= True)
    