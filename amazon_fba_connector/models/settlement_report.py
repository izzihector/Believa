from odoo import models,fields,api
from odoo.addons.amazon_ept.amazon_emipro_api.mws import Reports,DictWrapper
import time
class settlement_report(models.Model):
    _inherit="settlement.report.ept"
    
    @api.multi
    def _get_reimbursement_invoices(self):
        for report in self:
            report.invoice_count=len(report.reimbursement_invoice_ids.ids)
    reimbursement_invoice_ids=fields.Many2many("account.invoice",'amazon_rembursement_invoice_rel','report_id','invoice_id',string="Reimbursement Invoice")
    invoice_count=fields.Integer(compute="_get_reimbursement_invoices",string="Invoice Count")

    @api.multi
    def list_of_reimbursement_invoices(self):
        action = {
            'domain': "[('id', 'in', " + str(self.reimbursement_invoice_ids.ids) + " )]",
            'name': 'Reimbursement Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
                  }
        return action
    
    @api.model
    def check_or_create_invoice_if_not_exist(self,amz_orders):
        stock_immediate_transfer_obj=self.env['stock.immediate.transfer']
        for order in amz_orders:
            """Changes by Dhruvi
                default_fba_partner_id is fetched according to seller wise."""
            if order.amz_instance_id.seller_id.def_fba_partner_id.id == order.partner_id.id:
                continue
            if order.state=='draft':
                order.action_confirm()

            for picking in order.picking_ids:
                if picking.state in ['confirmed','partially_available','assigned']:
                    picking.action_confirm()
                    picking.action_assign()
                    stock_immediate_transfer_obj.create({'pick_ids':[(4,picking.id)]}).process()
                   
            if not order.invoice_ids:
                order.action_invoice_create()                                
            for invoice in order.invoice_ids:
                if invoice.state=='draft' and invoice.type=='out_invoice':
                    invoice.action_invoice_open()                    
        return True   
    
    @api.multi
    def make_amazon_reimbursement_line_entry(self,seller,bank_statement,date_posted,fees_type_dict,order_ref=''):
        bank_statement_line_obj = self.env['account.bank.statement.line']
        for fee_type, amount in fees_type_dict.items():
            bank_line_vals = {
                              'name':order_ref and order_ref+'_'+fee_type or fee_type,
                              'ref':bank_statement.settlement_ref,
                              'amount':amount,
                              'statement_id':bank_statement.id,
                              'date':date_posted,
                              'amazon_code':fee_type                                           
                             }
            statement_line = bank_statement_line_obj.create(bank_line_vals)            
        return statement_line    
    
    @api.multi
    def reconcile_reimbursement_invoice(self,reimbursement_invoices,reimbursement_line,bank_statement):
        move_line_obj=self.env['account.move.line']
        for reimbursement_invoice in reimbursement_invoices:
            if reimbursement_invoice.state=='draft':
                reimbursement_invoice.compute_taxes()
                reimbursement_invoice.action_invoice_open()                
        account_move_ids = list(map(lambda x:x.move_id.id,reimbursement_invoices))
        move_lines = move_line_obj.search([('move_id','in',account_move_ids),
                                           ('user_type_id.type','=','receivable'),
                                           ('reconciled','=',False)])
        mv_line_dicts = []
        move_line_total_amount = 0.0
        currency_ids = []                        
        for moveline in move_lines:
            amount = moveline.debit-moveline.credit
            amount_currency = 0.0
            if moveline.amount_currency:
                currency,amount_currency = self.convert_move_amount_currency(bank_statement,moveline,amount)
                if currency:
                    currency_ids.append(currency)
                    
            if amount_currency:
                amount = amount_currency 
            mv_line_dicts.append({
                                  'credit':abs(amount) if amount >0.0 else 0.0,
                                  'name':moveline.invoice_id.number,
                                  'move_line':moveline,
                                  'debit':abs(amount) if amount < 0.0 else 0.0
                                  })
            move_line_total_amount += amount
        if round(reimbursement_line.amount,10) == round(move_line_total_amount,10) and (not reimbursement_line.currency_id or  reimbursement_line.currency_id.id==bank_statement.currency_id.id):
            if currency_ids:
                currency_ids = list(set(currency_ids))
                if len(currency_ids)==1:
                    reimbursement_line.write({'amount_currency':move_line_total_amount,'currency_id':currency_ids[0]})
            reimbursement_line.process_reconciliation(mv_line_dicts)
        return True
    @api.multi
    def find_unreconcile_lines(self,seller_id,bank_statement,amazon_code=False):
        transaction_obj = self.env['amazon.transaction.line.ept']
        bank_statement_line_obj=self.env['account.bank.statement.line']
        amazon_seller_obj=self.env['amazon.seller.ept']
        seller=amazon_seller_obj.browse(seller_id)
        lines=super(settlement_report,self).find_unreconcile_lines(seller_id,bank_statement,amazon_code)
        account_invoice_obj=self.env['account.invoice']
        other_lines_ids=[]
        reimbursement_invoice=False
        invoice_amount_line_dict={}
        rem_line_ids=[]
        date_posted=False
        reimbursement_invoice_ids=self.reimbursement_invoice_ids.ids
        for invoice in self.reimbursement_invoice_ids:
            if invoice.state=='open':
                invoice.action_invoice_cancel()
                invoice.action_invoice_draft()
        for line in lines:
            trans_line = transaction_obj.search([('transaction_type_id.amazon_code','=',line.amazon_code),('seller_id','=',seller_id),('transaction_type_id.is_reimbursement','=',True)])
            if trans_line:
                rem_line_ids.append(line.id)  
                date_posted=line.date
            else:
                other_lines_ids.append(line.id)    
            if trans_line:
                reimbursement_invoice=account_invoice_obj.search([('state','=','draft'),('id','in',reimbursement_invoice_ids),('date_invoice','=',date_posted)],limit=1)
                if not reimbursement_invoice:
                    reimbursement_invoice=self.create_amazon_reimbursement_invoice(bank_statement, seller,date_posted)
                    self.write({'reimbursement_invoice_ids':[(4,reimbursement_invoice.id)]})
                    reimbursement_invoice_ids.append(reimbursement_invoice.id)
                amt=invoice_amount_line_dict.get(reimbursement_invoice,0.0)
                invoice_amount_line_dict.update({reimbursement_invoice:amt+line.amount})
                self.create_amazon_reimbursement_invoice_line(bank_statement, seller, reimbursement_invoice,line.name,line.amount,trans_line)
            
        rem_line_ids and bank_statement_line_obj.browse(rem_line_ids).unlink()        
        for invoice,amount in invoice_amount_line_dict.items():
            name='%s-%s'%(invoice.id,'Reimbursement')
            reimbursement_line=self.make_amazon_reimbursement_line_entry(seller,bank_statement,invoice.date_invoice,{name:amount})        
            self.reconcile_reimbursement_invoice(invoice, reimbursement_line, bank_statement)
        if other_lines_ids:
            return bank_statement_line_obj.browse(other_lines_ids)
        return []
            
            
    @api.multi
    def create_amazon_reimbursement_invoice_line(self,bank_statement,seller,reimbursement_invoice,name='REVERSAL_REIMBURSEMENT',amount=0.0,trans_line=False):
        invoice_line_obj=self.env['account.invoice.line']
        reimbursement_product=seller.reimbursement_product_id
        #account_id=invoice_line_obj.get_invoice_line_account('out_invoice', reimbursement_product,seller.reimbursement_customer_id.property_account_position_id,self.company_id)

        vals={'product_id':reimbursement_product.id,
              'name':name,
              'invoice_id':reimbursement_invoice.id,
              #'account_id':account_id,
              'price_unit':amount,
              'quantity':1,
              'uom_id':reimbursement_product.uom_id.id,
              }
        new_record=invoice_line_obj.new(vals)
        new_record._onchange_product_id()
        retval=invoice_line_obj._convert_to_write({name: new_record[name] for name in new_record._cache})
        retval.update({'price_unit':amount})
        trans_line and retval.update({'account_id':trans_line.account_id.id})
        if trans_line and trans_line.tax_id:
            tax_ids=[(6,0,trans_line.tax_id.ids)]
            retval.update({'invoice_line_tax_ids':tax_ids})                
        invoice_line_obj.create(retval)
        return True
    @api.multi
    def create_amazon_reimbursement_invoice(self,bank_statement,seller,date_posted):
        invoice_obj=self.env['account.invoice']
        partner_id=seller.reimbursement_customer_id.id
        account_id=seller.reimbursement_customer_id.property_account_receivable_id.id
        fiscal_position_id=seller.reimbursement_customer_id.property_account_position_id.id
        journal_id=seller.sale_journal_id.id
        invoice_vals = {
            'type': 'out_invoice',
            'reference': bank_statement.name,
            'account_id': account_id,
            'partner_id': partner_id,
            'journal_id': journal_id,
            'currency_id': self.currency_id.id,
            'amazon_instance_id':self.instance_id.id,
            'fiscal_position_id': fiscal_position_id,
            'company_id': self.company_id.id,
            'user_id': self._uid or False,
            'date_invoice':date_posted,
            'seller_id':self.instance_id and self.instance_id.seller_id and self.instance_id.seller_id.id or False,
            'global_channel_id': self.instance_id and self.instance_id.seller_id and self.instance_id.seller_id.global_channel_id and self.instance_id.seller_id.global_channel_id.id or False,
            
        }
        reimbursement_invoice=invoice_obj.create(invoice_vals) 
        return reimbursement_invoice
    @api.multi
    def make_amazon_other_transactions(self,seller,bank_statement,other_transactions):        
        transaction_obj = self.env['amazon.transaction.line.ept']
        account_invoice_obj=self.env['account.invoice']
        reimbursement_invoice=False
        reimbursement_invoices=[]
        invoice_amount_line_dict={}
        tran_type_inv={}
        for transaction in other_transactions:
            ref_name = transaction.get('AmazonOrderID',{}).get('value') 
            if not transaction:
                continue          
            sku=False
            other_transactions_items=transaction.get('OtherTransactionItem',{})
            if not isinstance(other_transactions_items,list):
                other_transactions_items=[other_transactions_items]
            for other_transactions_item in other_transactions_items:
                if other_transactions_item:
                    if not sku:
                        sku=other_transactions_item.get('SKU',{}).get('value')
                    else:
                        sku="%s/%s"%(sku,other_transactions_item.get('SKU',{}).get('value'))
            trans_type = transaction.get('TransactionType',{}).get('value','')
            trans_id=transaction.get('TransactionID',{}).get('value')
            amount = float(transaction.get('Amount',{}).get('value',0.0))
            date_posted = transaction.get('PostedDate',{}).get('value',time.strftime('%Y-%m-%d'))
            amazon_order_ref=transaction.get('AmazonOrderID',{}) and transaction.get('AmazonOrderID',{}).get('value') or False
            trans_line = transaction_obj.search([('transaction_type_id.amazon_code','=',trans_type),('seller_id','=',seller.id),('transaction_type_id.is_reimbursement','=',True)])
            name=''
            name=amazon_order_ref 
            if trans_type:
                name=name and "%s/%s"%(name,trans_type) or trans_type
            if trans_id:
                name=name and "%s/%s"%(name,trans_id) or trans_id     
            if sku:
                name=name and "%s/sku-%s"%(name,sku) or sku
                
            if not trans_line:
                self.make_amazon_fee_entry(seller,bank_statement,date_posted,{trans_type:amount},order_ref='',rei_name=name)            
            else:
                reimbursement_invoice=account_invoice_obj.search([('id','in',reimbursement_invoices),('date_invoice','=',date_posted)],limit=1)
                if not reimbursement_invoice:
                    reimbursement_invoice=self.create_amazon_reimbursement_invoice(bank_statement,seller,date_posted)
                    reimbursement_invoice.update({'reimbursement_id':trans_id,'name':ref_name or False})
                    reimbursement_invoices.append(reimbursement_invoice.id)
                amt=invoice_amount_line_dict.get(reimbursement_invoice,0.0)
                invoice_amount_line_dict.update({reimbursement_invoice:amt+amount})
                self.create_amazon_reimbursement_invoice_line(bank_statement, seller, reimbursement_invoice,name,amount,trans_line)
                tran_type_inv.update({reimbursement_invoice:trans_type})
        reimbursement_line=False        
        reimbursement_invoices and self.write({'reimbursement_invoice_ids':[(6,0,reimbursement_invoices)]})
        for invoice,amount in invoice_amount_line_dict.items():
            name=tran_type_inv.get(invoice)
            if not name:
                name='%s-%s'%(invoice.id,'Reimbursement')
            reimbursement_line=self.make_amazon_reimbursement_line_entry(seller,bank_statement,invoice.date_invoice,{name:amount})        
            self.reconcile_reimbursement_invoice(invoice, reimbursement_line, bank_statement)
        return True
