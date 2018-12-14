from odoo import models,fields,api
from odoo.exceptions import Warning
class amazon_transaction(models.Model):
    _inherit = 'amazon.transaction.log'
    
    
    is_model=fields.Boolean(compute='_checkmodel',string="Is model",store=False,help="")    
    @api.multi
    def _checkmodel(self):
        for record in self:
            model=self.env['amazon.transaction.log'].search([('model_id.model','=','shipping.report.request.history'),('id','=',record.id)],limit=1)
            if model:
                is_model=True
            else:
                is_model=False              
            record.is_model=is_model
            
    @api.multi
    def process_report(self):
        view=self.env.ref('amazon_fba_connector.amazon_shipping_report_request_history_form_view_ept')
        shipping_peport_request_history_obj=self.env['shipping.report.request.history']
        shipment_report=shipping_peport_request_history_obj.browse(self.res_id)
        
        
        if not shipment_report:
            raise Warning('Record was Deleted')
                                              
        action = {
                    'name': 'Feed Logs',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id':view.id,
                    'res_model': 'shipping.report.request.history',
                    'res_id':self.res_id,
                    'type': 'ir.actions.act_window',                                     
                 }
        
        return action