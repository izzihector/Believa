from odoo import fields,api,models

class AmazonFulfillmentCenter(models.Model):
    _name = "amazon.fulfillment.country.rel"
    _description = 'amazon.fulfillment.country.rel'
    
    fulfillment_code = fields.Char(string="Fulfillment Center Code")
    country_id = fields.Many2one('res.country',string="Fulfillment Id")
    
class res_country(models.Model):
    _inherit = "res.country"
     
    fulfillment_code_ids = fields.One2many('amazon.fulfillment.country.rel','country_id',string="Fulfillment Center code")