from odoo import tools
from odoo import fields,models,api

class sale_report(models.Model):
    _inherit = "amazon.sale.report"

    amz_fulfillment_by = fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')


    
    def _select(self):
        result=super(sale_report,self)._select()
        result="%s,%s"%(result,"s.amz_fulfillment_by as amz_fulfillment_by")
        return result
    
    def _group_by(self):
        result=super(sale_report,self)._group_by()
        result="%s,%s"%(result,"s.amz_fulfillment_by")
        return result
        