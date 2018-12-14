#!/usr/bin/python3
from odoo import models, fields, api

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    ebay_order_line_item_id = fields.Char(string="eBay Order Item Id")
    ebay_instance_id=fields.Many2one("ebay.instance.ept",string="Instance",related="order_id.ebay_instance_id",readonly=True)
    ebay_order_qty=fields.Float("eBay Order Qty")
    item_id=fields.Char("Item Id")
    seller_dicount_campaign_display_name=fields.Char('Campaign Display Name')
    seller_dicount_campaign_id=fields.Integer('Campaign Id')
    
    @api.multi
    def create_product_vals(self,ebay_sku,title,instance):
        vals={
              'name':title,
              'default_code':ebay_sku,
              'type':'product', 
              'purchase_ok' :True,
              'sale_ok' :True,    
              }
        odoo_product_obj=self.env['product.product']
        odoo_product=odoo_product_obj.create(vals)
        ebay_product=self.create_ebay_products(odoo_product, instance)
        return ebay_product 
    
    @api.multi
    def create_ebay_products(self,odoo_product,instance):
        ebay_template_obj=self.env['ebay.product.template.ept']
        ebay_product_obj=self.env['ebay.product.product.ept']
        product_template=odoo_product.product_tmpl_id
        ebay_template=ebay_template_obj.search([('instance_id','=',instance.id),('product_tmpl_id','=',product_template.id)])
        order_line_product=False
        if not ebay_template:
            if len(product_template.product_variant_ids.ids) == 1 :
                ebay_template=ebay_template_obj.create({'instance_id':instance.id,'product_tmpl_id':product_template.id,
                                                        'name':product_template.name,'description':product_template.description_sale,'product_type' : 'individual','exported_in_ebay':True})
            else:
                ebay_template=ebay_template_obj.create({'instance_id':instance.id,'product_tmpl_id':product_template.id,
                                                        'name':product_template.name,'description':product_template.description_sale,'product_type' : 'variation','exported_in_ebay':True})                
        for variant in product_template.product_variant_ids:
            ebay_variant=ebay_product_obj.search([('instance_id','=',instance.id),('product_id','=',variant.id)])
            if not ebay_variant:
                ebay_variant=ebay_product_obj.create({'instance_id':instance.id,'product_id':variant.id,'ebay_product_tmpl_id':ebay_template.id,'ebay_sku':variant.default_code,'name':variant.name,'exported_in_ebay':True})
                if not order_line_product and odoo_product.default_code==variant.default_code:
                    order_line_product=ebay_variant
        return order_line_product

    @api.multi
    def create_ebay_sale_order_line(self,resultval,instance,ebay_order,is_already_shipment_line):
        ebay_product_obj=self.env['ebay.product.product.ept']
        ebay_product_listing_obj=self.env['ebay.product.listing.ept']
        ebay_product_tmpl_obj=self.env['ebay.product.template.ept']
        order_lines = resultval.get('TransactionArray',False) and resultval['TransactionArray'].get('Transaction',[])
        if type(order_lines) == dict:
            order_lines = [order_lines]
        for order_line_dict in order_lines:
            sku=order_line_dict.get('Variation',{}).get('SKU',False)
            if not sku:
                sku = order_line_dict.get('Item',{}).get('SKU',False) 
            item_id=order_line_dict.get('Item',{}).get('ItemID',{})
            if not sku:
                listing_record=ebay_product_listing_obj.search([('name','=',item_id)],limit=1)
                if not listing_record:
                    sku=ebay_product_tmpl_obj.get_item(instance,item_id)
                else:
                    sku=listing_record.ebay_variant_id and listing_record.ebay_variant_id.ebay_sku
            ebay_product=ebay_product_obj.search([('ebay_sku','=',sku),('instance_id','=',instance.id)],limit=1)
            title=order_line_dict.get('VariationTitle')
            if not title:
                title=order_line_dict.get('Item',{}).get('Title',False)            
            odoo_product = False
            if not ebay_product:
                if not instance.create_new_product and instance.create_quotation_without_product:
                    title = "%s - %s"%(order_line_dict.get('Item',{}).get('Title',''),sku)
            else:
                odoo_product=ebay_product.product_id
            price_unit=order_line_dict.get('TransactionPrice',False) and order_line_dict['TransactionPrice'].get('value',False)
            order_line_vals=self.create_sale_order_line_vals(order_line_dict,price_unit,ebay_product, odoo_product, ebay_order, instance,odoo_product and odoo_product.name or title)
            self.create(order_line_vals)
            if not is_already_shipment_line:
                shipping_cost = float(order_line_dict.get('ActualShippingCost',{}).get('value',0.0))
                if shipping_cost > 0.0:
                    shipment_charge_product=instance.shipment_charge_product_id
                    order_line_vals=self.create_sale_order_line_vals(order_line_dict,shipping_cost,False,shipment_charge_product, ebay_order, instance,shipment_charge_product.name or 'ActualShippingCost')
                    order_line_vals.update({'is_delivery':True})
                    self.create(order_line_vals)                
        return True

    @api.multi
    def create_sale_order_line_vals(self,order_line_dict,price_unit,ebay_product=False,odoo_product=False,ebay_order=False,instance=False,title=False):
        order_qty = float(order_line_dict.get('QuantityPurchased',1.0))
        product_name = (title and title) or (ebay_order and ebay_order.name)
        uom_id = odoo_product and odoo_product.uom_id.id or False
        
        sequence=1
        if not odoo_product:
            sequence=100
        elif odoo_product and odoo_product.type=='service':
            sequence=100
        
        order_line_vals = {
            'order_id': ebay_order.id,
            'product_id': odoo_product and odoo_product.id or False,
            'company_id': ebay_order.company_id.id,
            'description': product_name,
            'product_uom': uom_id,
            'order_qty': order_qty,
            'price_unit': price_unit, 
        }
        order_line_vals = self.create_sale_order_line_ept(order_line_vals)
        
        """If In ebay Response we got 0.0 ebay in tax then search from the product if we got tax in product then we 
          set default tax based on instance configuration"""
        tax_id=[]
        if not order_line_vals.get('tax_id',[]) and instance.tax_id:
            tax_id=[(6,0,[instance.tax_id.id])]
            order_line_vals.update({'tax_id':tax_id})

        order_line_vals.update({
            'ebay_instance_id': instance.id,
            'ebay_order_qty': order_qty,
            'ebay_order_line_item_id': order_line_dict.get('OrderLineItemID',{}),
            'item_id': order_line_dict.get('Item',{}).get('ItemID',False),
            'sequence': sequence,
        })
        
        if ebay_product and ebay_product.ebay_active_listing_id:
            order_line_vals.update({'producturl':"%s%s"%(instance.product_url,ebay_product.ebay_active_listing_id.name)})
        return order_line_vals
        
    @api.model
    def create_account_tax(self,value,price_included,company):
        accounttax_obj = self.env['account.tax']
        if price_included:
            name='%s_(%s %s)_%s'%('Sales Tax Price Included',str(value*100),'%',company.name)
        else:
            name='%s_(%s %s)_%s'%('Sales Tax Price Excluded',str(value*100),'%',company.name)            
        accounttax_id = accounttax_obj.create({'name':name,'amount':float(value),'type_tax_use':'sale','price_include':price_included,'company_id':company.id})
        return accounttax_id

    @api.model
    def calculate_tax_per_item(self,amount,instance):
        tax_id=[]
        if instance.price_tax_included:
            if amount!=0.0:
                acctax_id = self.env['account.tax'].search([('price_include','=',True),('type_tax_use', '=', 'sale'), ('amount', '=', amount),('company_id','=',instance.warehouse_id.company_id.id)])
                if not acctax_id:
                    acctax_id = self.createAccountTax(amount,True,instance.warehouse_id.company_id)
                if acctax_id:
                    tax_id = [(6, 0, acctax_id.ids)]
            else:
                tax_id=[]
        else:
            if amount!=0.0:
                acctax_id = self.env['account.tax'].search([('price_include','=',False),('type_tax_use', '=', 'sale'), ('amount', '=', amount),('company_id','=',instance.warehouse_id.company_id.id)])
                if not acctax_id:
                    acctax_id = self.createAccountTax(amount,False,instance.warehouse_id.company_id)
                if acctax_id:
                    tax_id=[(6,0,acctax_id.ids)]
            else:
                tax_id=[]
        return tax_id        
