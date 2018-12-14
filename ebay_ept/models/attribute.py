#!/usr/bin/python3
from odoo import models, fields, api

class attribute_master(models.Model):
    _name = "ebay.attribute.master"
    _description = "eBay Master Attributes"

    name = fields.Char('Attribute Name',required=True)
    categ_id = fields.Many2one('ebay.category.master.ept', 'Category',required=True)
    value_ids = fields.One2many('ebay.attribute.value','attribute_id','Attribute Values')
    is_brand = fields.Boolean("Is Brand Attribute", help="Let system know that this is Brand attributes of specific category")
    is_mpn = fields.Boolean("Is MPN Attribute", help="Let system know that this is MPN attributes of specific category")

class attribute_matching(models.Model):
    _name = "ebay.attribute.matching"
    _description = "eBay Matching Attributes"
    
    attribute_id = fields.Many2one('ebay.attribute.master','Attribute Name',required=True)
    value_id = fields.Many2one('ebay.attribute.value','Attribute Values',required=True)
    product_tmpl_id = fields.Many2one('ebay.product.template.ept','Template 1')

    @api.onchange("attribute_id")
    def onchange_attribute(self):
        domain={}
        if self.product_tmpl_id:
            attribute_ids=self.product_tmpl_id.category_id1 and self.product_tmpl_id.category_id1.attribute_ids.ids
            attribute_ids+=self.product_tmpl_id.category_id2 and self.product_tmpl_id.category_id2.attribute_ids.ids
            
            domain['attribute_id'] = [('id', 'in', attribute_ids or [])]
        if self.attribute_id:
            value_ids=self.attribute_id.value_ids.ids
            domain['value_id']=[('id','in',value_ids)]
        else:
            domain['value_id']=[('id','in',[])]
            self.value_id=False
        return {'domain':domain}


class attribute_value(models.Model):
    _name = 'ebay.attribute.value'
    _description = "eBay Attribute Values"
    
    name = fields.Char('Attribute Value',required=True)
    attribute_id = fields.Many2one('ebay.attribute.master','Attribute Master',required=True)
               
