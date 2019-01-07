#!/usr/bin/python3
from odoo import models, fields

class account_tax(models.Model):
    _inherit='account.tax'
    
    export_in_ebay = fields.Boolean("Export In eBay",help="This tax applied on eBay.")