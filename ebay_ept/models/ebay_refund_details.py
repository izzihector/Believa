#!/usr/bin/python3
from odoo import models,fields

class refund_option_ept(models.Model):
    _name="ebay.refund.options"
    _description = "eBay Refund Options"
    
    name=fields.Char("Option",required=True)
    description=fields.Char("Description",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_refund_site_rel','refund_id','site_id',required=True)
    
    def create_refund_details(self,instance,details):
        refund_days_obj=self.env['ebay.return.days']
        shipping_cost_obj=self.env['ebay.refund.shipping.cost.options']
        restock_fee_obj=self.env['ebay.restock.fee.options']
        refund_details=details.get('Refund',[])
        if not isinstance(refund_details,list):
            refund_details=[refund_details]
        for option in refund_details:
            exist_option=self.search([('name','=',option.get('RefundOption')),('site_ids','in',instance.site_id.ids)])
            if not exist_option:
                exist_option=self.search([('name','=',option.get('RefundOption'))])
                if not exist_option:
                    self.create({'name':option.get('RefundOption'),'description':option.get('Description'),'site_ids':[(6,0,instance.site_id.ids)]})
                else:
                    site_ids=list(set(exist_option.site_ids.ids+instance.site_id.ids))
                    exist_option.write({'site_ids':[(6,0,site_ids)]})
        returns_with_in=details.get('ReturnsWithin',[])
        if not isinstance(returns_with_in,list):
            returns_with_in=[returns_with_in]
        for option in returns_with_in:
            exist_option=refund_days_obj.search([('name','=',option.get('ReturnsWithinOption')),('site_ids','in',instance.site_id.ids)])
            if not exist_option:
                exist_option=refund_days_obj.search([('name','=',option.get('ReturnsWithinOption'))])
                if not exist_option:
                    refund_days_obj.create({'name':option.get('ReturnsWithinOption'),'description':option.get('Description'),'site_ids':[(6,0,instance.site_id.ids)]})
                else:
                    site_ids=list(set(exist_option.site_ids.ids+instance.site_id.ids))
                    exist_option.write({'site_ids':[(6,0,site_ids)]})
        shipping_cost_paid_by=details.get('ShippingCostPaidBy',[])
        if not isinstance(shipping_cost_paid_by,list):
            shipping_cost_paid_by=[shipping_cost_paid_by]
        for option in shipping_cost_paid_by:
            exist_option=shipping_cost_obj.search([('name','=',option.get('ShippingCostPaidByOption')),('site_ids','in',instance.site_id.ids)])
            if not exist_option:
                exist_option=shipping_cost_obj.search([('name','=',option.get('ShippingCostPaidByOption'))])
                if not exist_option:
                    shipping_cost_obj.create({'name':option.get('ShippingCostPaidByOption'),'description':option.get('Description'),'site_ids':[(6,0,instance.site_id.ids)]})
                else:
                    site_ids=list(set(exist_option.site_ids.ids+instance.site_id.ids))
                    exist_option.write({'site_ids':[(6,0,site_ids)]})
        restock_fee_value=details.get('RestockingFeeValue',[])
        if not isinstance(restock_fee_value,list):
            restock_fee_value=[restock_fee_value]
        for option in restock_fee_value:
            exist_option=restock_fee_obj.search([('name','=',option.get('RestockingFeeValueOption')),('site_ids','in',instance.site_id.ids)])
            if not exist_option:
                exist_option=restock_fee_obj.search([('name','=',option.get('RestockingFeeValueOption'))])
                if not exist_option:
                    restock_fee_obj.create({'name':option.get('RestockingFeeValueOption'),'description':option.get('Description'),'site_ids':[(6,0,instance.site_id.ids)]})
                else:
                    site_ids=list(set(exist_option.site_ids.ids+instance.site_id.ids))
                    exist_option.write({'site_ids':[(6,0,site_ids)]})
        return True

class return_days(models.Model):
    _name="ebay.return.days"
    _description = "eBay Return Days"
    
    name=fields.Char("ReturnsWithinOption",required=True)
    description=fields.Char("Description",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_return_days_rel','refund_id','site_id',required=True)


class refund_shipping_cost_paid_by_options(models.Model):    
    _name="ebay.refund.shipping.cost.options"
    _description = "eBay Refund Shipping Cost Options"
    
    name=fields.Char("ShippingCostPaidByOption",required=True)
    description=fields.Char("Description",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_refund_shipping_cost_rel','refund_id','site_id',required=True)

class restock_fee_options(models.Model):
    _name="ebay.restock.fee.options"
    _description = "eBay Restock Fee Options"
    
    name=fields.Char("RestockingFeeValueOption",required=True)
    description=fields.Char("Description",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_refund_restock_fee_rel','refund_id','site_id',required=True)
    