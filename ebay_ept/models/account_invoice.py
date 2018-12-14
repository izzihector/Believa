#!/usr/bin/python3
from odoo import models,fields,api
from odoo.exceptions import Warning

class account_invoice_line(models.Model):
    _inherit='account.invoice.line'
    
    payment_updated_in_ebay=fields.Boolean("Payment Updated In eBay ?",default=False)


class account_invoice(models.Model):    
    _inherit='account.invoice'
    
    @api.multi
    def action_invoice_paid(self):
        result=super(account_invoice,self).action_invoice_paid()
        for invoice in self:
            instance=invoice.ebay_instance_id
            if instance and instance.auto_update_payment and invoice.type=='out_invoice':            
                if invoice.ebay_payment_option_id.name=='PayPal' or invoice.payment_updated_in_ebay:
                    return result
                if invoice.ebay_payment_option_id and not invoice.ebay_payment_option_id.update_payment_in_ebay:
                    return result 
                invoice.update_payment_in_ebay()
        return result
    
    @api.multi
    @api.depends("invoice_line_ids.payment_updated_in_ebay")
    def _get_ebay_updated_status(self):
        for invoice in self:
            if invoice.ebay_instance_id:
                if not invoice.payment_partially_updated_in_ebay:
                    invoice.payment_partially_updated_in_ebay = any(invoice_line.invoice_id.state == 'paid' and invoice_line.payment_updated_in_ebay == True for invoice_line in invoice.invoice_line_ids)
                if invoice.payment_partially_updated_in_ebay:
                    invoice.payment_partially_updated_in_ebay = not all(invoice_line.invoice_id.state == 'paid' and invoice_line.payment_updated_in_ebay == True for invoice_line in invoice.invoice_line_ids)
                    if not invoice.payment_partially_updated_in_ebay:
                        invoice.payment_updated_in_ebay = True    
    
    @api.multi
    def check_payment_option(self,domain,value):
        print
        
    @api.multi
    @api.depends('ebay_payment_option_id','invoice_line_ids')
    def get_payment_option(self):
        for invoice in self:
            sales=invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
            sale = sales and sales[0]
            if not sale:
                invoice.visible_payment_option=False
                continue
            if invoice.type!='out_invoice':
                invoice.visible_payment_option=False
                continue
            if not invoice.ebay_payment_option_id:         
                invoice.visible_payment_option=False
                continue  
            if invoice.ebay_payment_option_id and not invoice.ebay_payment_option_id.update_payment_in_ebay:
                invoice.visible_payment_option=False
                continue
            if invoice.ebay_payment_option_id.name=='PayPal':
                invoice.visible_payment_option=False
                continue
            invoice.visible_payment_option=True
    
    ebay_instance_id = fields.Many2one("ebay.instance.ept",string="eBay Instance")
    ebay_payment_option_id = fields.Many2one('ebay.payment.options',"Payment Option")
    payment_updated_in_ebay = fields.Boolean("Payment Updated In eBay ?",compute='_get_ebay_updated_status',store=True,default=False)
    payment_partially_updated_in_ebay = fields.Boolean("Payment Partially Updated In eBay ?",compute='_get_ebay_updated_status',store=True,default=False)
    is_refund_in_ebay = fields.Boolean("Is refund in eBay ?",default=False)
    visible_payment_option=fields.Boolean("Visible Payment Option",compute="get_payment_option",store=True)
    
    @api.multi
    def call_payment_update_api(self,instance,invoice_lines,para):
        try:
            lang = instance.lang_id and instance.lang_id.code
            if lang:
                para.update({'ErrorLanguage':lang})                    
            api = instance.get_trading_api_object()
            api.execute('ReviseCheckoutStatus',para)
            api.response.dict()
            invoice_lines.write({'payment_updated_in_ebay':True})
            self._cr.commit()               
        except Exception:
            raise Warning(api.response.dict())         
        
    @api.multi
    def get_item_id(self,orderline,instance):
        if orderline.item_id:
            return orderline.item_id
        product=self.env['ebay.product.product.ept'].search([('product_id','=',orderline.product_id.id),('instance_id','=',instance.id)])
        if product and product.ebay_active_listing_id:
            return product.ebay_active_listing_id.item_id
        if product and product.ebay_product_tmpl_id and product.ebay_product_tmpl_id.ebay_active_listing_id:
            return product.ebay_product_tmpl_id.ebay_active_listing_id.item_id
        return False
            
    @api.multi
    def update_payment_in_ebay(self):
        self.ensure_one()        
        sales=self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
        sale = sales and sales[0]
        instance=self.ebay_instance_id
        if not instance.check_instance_confirmed_or_not():
            return True
        if not sale:
            return True
        if self.ebay_payment_option_id.name=='PayPal':
            return True
        if self.ebay_payment_option_id and not self.ebay_payment_option_id.update_payment_in_ebay:
            return True 
        flag=True
        shipping_charge=0.0
        discount=0.0 
        para_last={}
        invoice_line_ids = []
        if instance:  
            for invoice_line in self.invoice_line_ids:
                if invoice_line.payment_updated_in_ebay:
                    continue
                order_line=self.env['sale.order.line'].search([('order_id','=',sale.id),('product_id','=',invoice_line.product_id.id)])
                if not order_line:
                    continue
                item_id=self.get_item_id(order_line,instance)
                if not item_id and invoice_line.product_id.type != 'service' :
                    continue                
                if invoice_line.product_id and order_line and invoice_line.product_id.type == 'product' and flag:
                    invoice_line_ids.append(invoice_line.id)
                    flag=False
                    para_last={
                        'AmountPaid':invoice_line.quantity * invoice_line.price_unit,
                        'ItemID':item_id,
                        'CheckoutStatus':'Complete',
                        'PaymentMethodUsed':self.ebay_payment_option_id.name,
                        'OrderLineItemID':order_line.ebay_order_line_item_id,
                        'OrderID':sale.ebay_order_id, 
                    }
                    
                elif invoice_line.product_id.type == 'service':
                    if invoice_line.price_subtotal > 0.0:
                        invoice_line_ids.append(invoice_line.id)
                        shipping_charge= shipping_charge + (invoice_line.quantity * invoice_line.price_unit)
                    else:
                        invoice_line_ids.append(invoice_line.id)
                        discount= discount + (invoice_line.quantity * invoice_line.price_unit)
                        
                        
                elif invoice_line.product_id and order_line and invoice_line.product_id.type == 'product':
                    para={
                        'AmountPaid':invoice_line.quantity * invoice_line.price_unit,
                        'ItemID':item_id,
                        'CheckoutStatus':'Complete',
                        'OrderLineItemID':order_line.ebay_order_line_item_id,
                        'PaymentMethodUsed':self.ebay_payment_option_id.name,
                        'OrderID':sale.ebay_order_id, 
                    }        
                    self.call_payment_update_api(instance,invoice_line, para)        
        if not flag:            
            if discount!=0.0:
                para_last.update({'AdjustmentAmount':discount})
            if shipping_charge!=0.0:
                para_last.update({'ShippingCost':shipping_charge})
            invoice_lines= self.env['account.invoice.line'].browse(invoice_line_ids)
            self.call_payment_update_api(instance,invoice_lines, para_last)        
        return True     
    
    @api.model   
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):    
        values = super(account_invoice,self)._prepare_refund(invoice,date_invoice=date_invoice,date=date,description=description, journal_id=journal_id)
        if invoice.ebay_instance_id:
            values.update({'ebay_instance_id':invoice.ebay_instance_id.id,
                           'global_channel_id':invoice.ebay_instance_id.global_channel_id and invoice.ebay_instance_id.global_channel_id.id or False})        
        return values    
    
