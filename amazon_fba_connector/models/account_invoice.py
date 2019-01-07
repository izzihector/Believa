from odoo import models,api,fields
class account_invoice(models.Model):
    _inherit="account.invoice"
    
    fulfillment_by = fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')

