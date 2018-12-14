#!/usr/bin/python3

import imp, sys
from odoo import models, fields
imp.reload(sys)
PYTHONIOENCODING="UTF-8"

class res_partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"
    _description = "eBay Res Partner"
    
    ebay_eias_token = fields.Char('EIAS Token',size=256)
    ebay_reg_date = fields.Char('Registration Date',size=64)
    ebay_user_id = fields.Char('User ID',size=64)
    ebay_user_id_last_changed = fields.Char('User ID Last Changed',size=64)
    ebay_user_emaid_id = fields.Char('User Email',size=100)
    ebay_address_id = fields.Char('Address ID',size=64)
    

class delivery_carrier(models.Model):
    _name = "delivery.carrier"
    _inherit = "delivery.carrier"
    _description = "eBay Delivery Carrier"
    
    ebay_code = fields.Char('eBay Carrier Code', size=64, required=False)