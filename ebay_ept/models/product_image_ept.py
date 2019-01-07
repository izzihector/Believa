#!/usr/bin/python3

from odoo import api,models,fields
import requests, base64
try:  
    from io import StringIO, BytesIO
except ImportError:
    from StringIO import StringIO
from odoo.exceptions import Warning

class ebay_product_image_ept(models.Model):
    _name = 'ebay.product.image.ept'
    _description = "eBay product Image"

    @api.multi
    @api.depends('url')
    def get_image(self):
        for image in self:
            try:
                filename= requests.get(image.url,stream=True,verify=False,timeout=10)                
                img = base64.b64encode(filename.content)
                image.url_image_binary=img
            except:
                pass
            
    name = fields.Char(size=60, string='Name')
    is_binary_image=fields.Boolean("Is Binary Image ?",default=False)
    url = fields.Char(size=600, string='Image URL')    
    ept_product_id = fields.Many2one('ebay.product.product.ept', string='eBay Product')    
    value_id=fields.Many2one("product.attribute.value",string="Attribute Value")
    ebay_image_url = fields.Char("eBay Image Url")
    is_galary_image=fields.Boolean("Is Galary Image ?")
    url_image_binary = fields.Binary("URL Image",compute="get_image",store=True)
    storage_image_binary=fields.Binary("Image")
    _sql_constraints = [
        ('name_uniq', 'unique(name)',
            'This Image Name already exist!'),
    ]    
    @api.multi
    def storage_image_in_ebay(self):
        for image in self:
            instance = image.ept_product_id.instance_id
            api = instance.get_trading_api_object()
            response_result = False
            if image.ebay_image_url :
                try:
                    response_result = requests.get(image.ebay_image_url,stream=True,verify=False,timeout=10)             
                except:
                    pass
                if response_result and response_result.status_code == 200 :
                    continue
                else:
                    ebay_image_url = image.create_picture_url()
            else:
                ebay_image_url = image.create_picture_url()
            
            image.ebay_image_url = ebay_image_url or ''
        return True
    
    @api.multi
    def create_picture_url(self):
        instance=self.ept_product_id.instance_id
        api = instance.get_trading_api_object()
        pictureData={
                    "WarningLevel": "High",
                    "ErrorLanguage" : 'en_US',
                    "PictureName": self.name
                    }
        if self.is_binary_image :
            image = BytesIO(base64.standard_b64decode(self.storage_image_binary))
            files = {'file': ('EbayImage', image)}
            response = api.execute('UploadSiteHostedPictures', pictureData, files=files)
        else:
            image = BytesIO(base64.standard_b64decode(self.url_image_binary)) 
            files = {'file': ('EbayImage', image)}
            response = api.execute('UploadSiteHostedPictures',pictureData, files=files)
        
        return response and response.dict() and response.dict().get('SiteHostedPictureDetails',{}).get('FullURL','')
        
    @api.model
    def create(self,vals):
        SeqObj = self.env['ir.sequence']
        if not vals.get('value_id') :
            ebay_product_id = self.env['ebay.product.product.ept'].search([('id','=',vals.get('ept_product_id'))])
            if ebay_product_id.ebay_product_tmpl_id.product_type == 'variation' :
                raise Warning('You must need to define Attribute Image Value of variation type product')
        
        vals['name'] = SeqObj.next_by_code('ebay.product.image.ept') 
        return super(ebay_product_image_ept,self).create(vals)
        