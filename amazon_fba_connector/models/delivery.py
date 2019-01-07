from odoo import models, fields, api

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    
    amazon_code = fields.Char('Amazon Carrier Code')
    
