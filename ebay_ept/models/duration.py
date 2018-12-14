#!/usr/bin/python3
from odoo import models, fields

class duration_time(models.Model):
    _name = "duration.time"
    _description = "eBay Duration Time"

    name = fields.Char('Duration',size=64)
    type = fields.Selection([('Chinese','Auction'),('FixedPriceItem','Fixed Price'),('LeadGeneration','Classified Ad')],string='Type')