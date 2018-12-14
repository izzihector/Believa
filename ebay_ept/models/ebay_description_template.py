#!/usr/bin/python3
from odoo import models,fields

class ebay_description_template(models.Model):
    _name="ebay.description.template"
    _description = "eBay Description Template"
    _order = 'id desc' 
    
    name = fields.Char("Name", required=True, help="Name of your Template")
    line_ids = fields.One2many("ebay.description.template.line","template_id", string="Lines", help="Here you can define what to be replace with specific value")
    description = fields.Text("HTML Content", required=True)
    
class ebay_description_template_line(models.Model):
    _name="ebay.description.template.line"
    _description = "eBay Description Template Line"
    
    text = fields.Char("Text", required=True, help="Text that you want to replace with specific value.")
    field_id = fields.Many2one("ir.model.fields", string="Field", help="Select fields name of product", domain="[('model','=','product.product'),('ttype','in',['char','float','text','binary','datetime','integer'])]", required=True)
    template_id = fields.Many2one("ebay.description.template", string="Template")