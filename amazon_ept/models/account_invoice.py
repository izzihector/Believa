from odoo import models,api,fields
class account_invoice(models.Model):
    _inherit="account.invoice"
    
    amazon_instance_id = fields.Many2one("amazon.instance.ept","Instances")
    
    #added by Dhruvi
    seller_id = fields.Many2one("amazon.seller.ept","Seller")
    reimbursement_id = fields.Char(string="Reimbursement Id")
    

    #added by Dhruvi [Changes on (27-09-2018) have used write() to set value]
    @api.multi
    def action_move_create(self):
        result=super(account_invoice,self).action_move_create()
        for record in self : 
            record.move_id.write({'seller_id':record.seller_id and record.seller_id.id or False,
                                  'amazon_instance_id':record.amazon_instance_id and record.amazon_instance_id.id or False
                                })
            for line in record.move_id.line_ids:
                line.write({'seller_id':record.seller_id and record.seller_id.id or False,
                            'amazon_instance_id':record.amazon_instance_id and record.amazon_instance_id.id or False
                            })
        return result
    
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(account_invoice,self)._prepare_refund(invoice, date_invoice=None, date=None, description=None, journal_id=None)
        values.update({'seller_id':self.seller_id and self.seller_id.id or False,
                       'global_channel_id':self.seller_id.global_channel_id and self.seller_id.global_channel_id.id or False,
                       'amazon_instance_id':self.amazon_instance_id and self.amazon_instance_id.id or False
                       })
        return values
        
    
    @api.model
    def send_amazon_invoice_via_email(self,args={}):
        instance_obj=self.env['amazon.instance.ept']
        seller_obj=self.env['amazon.seller.ept']
        invoice_obj=self.env['account.invoice']
        seller_id = args.get('seller_id',False)
        if seller_id:
            seller = seller_obj.search([('id','=',seller_id)])
            if not seller:
                return True
            
            email_template= self.env.ref('account.email_template_edi_invoice', False)
            instances = instance_obj.search([('seller_id','=',seller.id)])
            
            for instance in instances:
                if instance.invoice_tmpl_id:
                    email_template=instance.invoice_tmpl_id
                invoices=invoice_obj.search([('amazon_instance_id','=',instance.id),('state','in',['open','paid']),('sent','=',False),('type','=','out_invoice')])
                for invoice in invoices:                
                    email_template.send_mail(invoice.id)
                    invoice.write({'sent':True})                
        return True
    
    @api.model
    def send_amazon_refund_via_email(self,args={}):
        instance_obj=self.env['amazon.instance.ept']
        seller_obj=self.env['amazon.seller.ept']
        invoice_obj=self.env['account.invoice']
        seller_id = args.get('seller_id',False)
        if seller_id:
            seller = seller_obj.search([('id','=',seller_id)])
            if not seller:
                return True
            email_template= self.env.ref('account.email_template_edi_invoice', False)
            instances = instance_obj.search([('seller_id','=',seller.id)])
            for instance in instances:
                if instance.refund_tmpl_id:
                    email_template=instance.refund_tmpl_id
                invoices=invoice_obj.search([('amazon_instance_id','=',instance.id),('state','in',['open','paid']),('sent','=',False),('type','=','out_refund')],limit=1)
                for invoice in invoices:   
                    email_template.send_mail(invoice.id)
                    invoice.write({'sent':True})                
        return True
