from odoo import models, fields, api

class amazon_prepare_product_wizard(models.TransientModel):
    _inherit = 'amazon.product.wizard'

    fulfillment_by = fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')
   
    """This method prepare amazon product by product category for the export in amazon"""
    @api.multi
    def create_or_update_amazon_product(self,odoo_product,template,default_code,description,parentage):
        amazon_product_ept_obj=self.env['amazon.product.ept']
        amazon_attribute_line_obj=self.env['amazon.attribute.line.ept']
        amazon_attribute_value_obj=self.env['amazon.attribute.value.ept']
        amazon_attribute_obj=self.env['amazon.attribute.ept']
        browse_node_obj=self.env['amazon.browse.node.ept']  
        domain=[('country_id','=',self.instance_id.country_id.id)]
        odoo_product and domain.append(('odoo_category_id','=',odoo_product.categ_id.id))
        browse_node=browse_node_obj.search(domain,limit=1)
        """Changes by Dhruvi condition is being fetched according to seller wise."""
        vals={
              'instance_id':self.instance_id.id,
              'seller_sku':default_code or False,
#               'amazon_browse_node_id':browse_node and browse_node.id or False,
              'condition':self.instance_id.seller_id.condition or 'New',
              'tax_code_id':self.instance_id.default_amazon_tax_code_id and self.instance_id.default_amazon_tax_code_id.id or False,
              'long_description':description or False,
              'fulfillment_by':self.fulfillment_by or 'MFN',
              'variation_data': parentage
              }                    
        if not odoo_product:
            vals.update({'name':template.name,'product_tmpl_id':template.id,'default_code':default_code,'is_amazon_virtual_variant':True})
        else:
            vals.update({'product_id':odoo_product.id})
        if parentage=='parent':
            amazon_product=amazon_product_ept_obj.search([('seller_sku','=',default_code),('instance_id','=',self.instance_id.id),('fulfillment_by','=',self.fulfillment_by)])
        else:
            amazon_product=odoo_product and amazon_product_ept_obj.search([('instance_id','=',self.instance_id.id),('product_id','=',odoo_product.id),('fulfillment_by','=',self.fulfillment_by)]) or False               
        if amazon_product:
            amazon_product.write(vals)
        else:
            amazon_product=amazon_product_ept_obj.create(vals)              
        if odoo_product:
            for attribute_value in odoo_product.attribute_value_ids:
                if attribute_value.attribute_id.amazon_attribute_id:
                    amazon_attribute_line=amazon_attribute_line_obj.search([('product_id','=',amazon_product.id),('attribute_id','=',attribute_value.attribute_id.amazon_attribute_id.id)])
                    value=amazon_attribute_value_obj.search([('attribute_id','=',attribute_value.attribute_id.amazon_attribute_id.id),('name','=',attribute_value.name)],limit=1)
                    if not value:
                        value=amazon_attribute_value_obj.create({'attribute_id':attribute_value.attribute_id.amazon_attribute_id.id,'name':attribute_value.name})
                    if amazon_attribute_line:
                        amazon_attribute_line.write({'value_ids':[(6,0,value.ids)]})
                    else:
                        amazon_attribute_line_obj.create({'product_id':amazon_product.id,'attribute_id':attribute_value.attribute_id.amazon_attribute_id.id,'value_ids':[(6,0,value.ids)]})
                        
        """Commenetd by Dhruvi [13-11-2018] as variation_theme_id field is made invisble in template"""
#         if template.variation_theme_id:
#                 categ_ids=template.amazon_categ_id.ids+template.child_categ_id.ids
#                 attributes=amazon_attribute_obj.search([('amazon_categ_id','in',categ_ids),('name','=','Parentage')])
#                 amazon_attribute_line=amazon_attribute_line_obj.search([('product_id','=',amazon_product.id),('attribute_id','in',attributes.ids)],limit=1)                        
#                 value=amazon_attribute_value_obj.search([('attribute_id','in',attributes.ids),('name','=',parentage)],limit=1)
#                 if not value:
#                     value=amazon_attribute_value_obj.create({'attribute_id':attributes.ids[0],'name':parentage})
#                 if amazon_attribute_line:
#                     amazon_attribute_line.write({'value_ids':[(6,0,value.ids)]}) 
#                 else:
#                     amazon_attribute_line_obj.create({'product_id':amazon_product.id,'attribute_id':attributes.ids[0],'value_ids':[(6,0,value.ids)]})                                
# 
#                 attributes=amazon_attribute_obj.search([('amazon_categ_id','in',categ_ids),('name','=','VariationTheme')])
#                 amazon_attribute_line=amazon_attribute_line_obj.search([('product_id','=',amazon_product.id),('attribute_id','in',attributes.ids)],limit=1)                        
#                 value=amazon_attribute_value_obj.search([('attribute_id','in',attributes.ids),('name','=',template.variation_theme_id.name)],limit=1)
#                 if not value:
#                     value=amazon_attribute_value_obj.create({'attribute_id':attributes.ids[0],'name':template.variation_theme_id.name})
#                 if amazon_attribute_line:
#                     amazon_attribute_line.write({'value_ids':[(6,0,value.ids)]}) 
#                 else:
#                     amazon_attribute_line_obj.create({'product_id':amazon_product.id,'attribute_id':attributes.ids[0],'value_ids':[(6,0,value.ids)]})
        return True

    @api.multi
    def get_product_prep_instructions(self):
        amazon_instance_obj = self.env['amazon.instance.ept']
        amazon_product_obj = self.env['amazon.product.ept']
            
        if self._context.get('key') == 'get_product_prep_instructions':
            amazon_instances = amazon_instance_obj.search([])
            active_ids = self._context.get('active_ids',[])
            
            for instance in amazon_instances:
                amazon_products = amazon_product_obj.search([('id','in',active_ids),('instance_id','=',instance.id),('fulfillment_by','=','AFN'),('exported_to_amazon','=',True)])
                amazon_products and amazon_product_obj.get_product_prep_instructions(instance,amazon_products)
        return True
    
    
    
    
    
    