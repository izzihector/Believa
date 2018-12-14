#!/usr/bin/python3
from odoo import models,fields,api

class ebay_payment_options(models.Model):
    _name="ebay.payment.options"
    _description = "eBay Payment Options"
    _order = 'id desc'
    
    instance_id=fields.Many2one("ebay.instance.ept",string="Instance",required=True)
    name=fields.Char("PaymentOption",required=True)
    detail_version=fields.Char("DetailVersion",required=True)
    description=fields.Char("Description",required=True)
    auto_workflow_id=fields.Many2one("sale.workflow.process.ept","Auto Workflow")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')
    update_payment_in_ebay = fields.Boolean("Update Payment in eBay",default=False)
   
    @api.model
    def get_payment_options(self,instance,options):        
        for option in options:
            payment_option=self.search([('instance_id','=',instance.id),('name','=',option.get('PaymentOption'))])
            if payment_option:
                payment_option.write({'detail_version':option.get('DetailVersion'),'description':option.get('Description')})
            else:
                self.create({'instance_id':instance.id,'name':option.get('PaymentOption'),'detail_version':option.get('DetailVersion'),
                             'description':option.get('Description')
                             })
        return True