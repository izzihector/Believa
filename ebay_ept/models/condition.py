#!/usr/bin/python3
from odoo import models, fields

class condition_class(models.Model):
    _name = "ebay.condition.ept"
    _description = "eBay Condition"

    name = fields.Char('Condition Name',required=True)
    condition_id = fields.Char('Condition ID',required=True)
    category_id = fields.Many2one('ebay.category.master.ept','Category ID',required=True)
    description=fields.Text("Description")