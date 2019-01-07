from odoo import models,fields,api,_
from odoo.exceptions import Warning
from io import StringIO,BytesIO
import base64
import csv

class FileSelectionWizard(models.TransientModel):
    _name="file.selection.wizard"
    _description = 'file.selection.wizard'
    
    seller_id = fields.Many2one('amazon.seller.ept',string="Amazon Seller") 
    choose_file = fields.Binary(string="Choose File",filename="filename")
    delimiter =fields.Selection([('tab','Tab'),('semicolon','Semicolon'),('comma','Comma')],string="Separator",default='comma',required=True)
    
    @api.multi
    def download_sample_attachment(self):
        attachment=self.env['ir.attachment'].search([('name','=','import_product_sample.csv')])
        return {
         'type': 'ir.actions.act_url',
         'url': '/web/content/%s?download=true' %(attachment.id),
        # 'url':'/web/binary/download_document/%s?download=true' %(attachment.id),
         'target': 'new',
         'nodestroy': False,
         } 
        
        
    @api.multi
    def import_csv_file(self):
        if not self.choose_file or not self.seller_id:
            raise Warning('Need to select Seller and File.')
        
        if self.choose_file and self.seller_id:
            instances=self.env['amazon.instance.ept'].search([('seller_id','=',self.seller_id.id)])
            csv_file = StringIO(base64.decodestring(self.choose_file).decode())
            file_write = open('/tmp/products.csv','w+')
            file_write.writelines(csv_file.getvalue())
            file_write.close()
            
            
            product_obj = self.env["product.product"]
            amazon_product_ept_obj = self.env['amazon.product.ept']
            amazon_instance_obj = self.env['amazon.instance.ept']
#             amazon_marketplace_ept_obj = self.env['amazon.marketplace.ept']
            amazon_process_log_obj=self.env['amazon.process.log.book']
            amazon_transaction_log_obj = self.env['amazon.transaction.log']
             
            amazon_process_log = False             
            
            if self.delimiter == "tab":
                reader = csv.DictReader(open('/tmp/products.csv',"rU"), delimiter="\t")
            elif self.delimiter == "semicolon":
                reader = csv.DictReader(open('/tmp/products.csv',"rU"), delimiter=";")
            else:
                reader = csv.DictReader(open('/tmp/products.csv',"rU"), delimiter=",")
            
#             data = []
            if reader:
                if reader.fieldnames and len(reader.fieldnames)==6:
                    for line in reader:
                        default_code = line.get(reader.fieldnames[0])
                        seller_sku = line.get(reader.fieldnames[1])
                        asin = line.get(reader.fieldnames[2])
                        amazon_product_name = line.get(reader.fieldnames[3])
                        fullfillment_by = line.get(reader.fieldnames[4])                        
                        marketplace = line.get(reader.fieldnames[5])
                        
                        
                        amazon_product = False
                        odoo_product = False
                        instance = False
#                         marketplace_id = False
                        
                        fullfillment_by = fullfillment_by and 'MFN' if fullfillment_by == 'FBM' else 'AFN'
                        
                        if marketplace:
                            instance = amazon_instance_obj.search([("seller_id","=",self.seller_id.id),("marketplace_id.name","=",marketplace)],limit=1)
                        
                        if not amazon_process_log:
                            amazon_process_log = amazon_process_log_obj.create({'instance_id':instance and instance.id or False,
                                       'application':'product',
                                       'operation_type':'import',
                                       })                                      
                        
                        if not instance:
                            amazon_process_log and amazon_transaction_log_obj.create({
                                                       'message':"Amazon instance not found for %s marketplace"%(marketplace),
                                                       'log_type':'not_found',
                                                       'job_id':amazon_process_log and amazon_process_log.id,   
                                                       'operation_type':'import'                                                    
                                                       })
                            continue                        
                        if instance and fullfillment_by and seller_sku:
                            amazon_product = amazon_product_ept_obj.search([("seller_sku","=",seller_sku),("fulfillment_by","=",fullfillment_by),("instance_id","=",instance.id)],limit=1)
                        if amazon_product:
                            continue
                        if not fullfillment_by:
                            amazon_process_log and amazon_transaction_log_obj.create({
                                                       'message':"Fullfillment not found in file",
                                                       'log_type':'not_found',
                                                       'job_id':amazon_process_log and amazon_process_log.id,   
                                                       'operation_type':'import'                                                    
                                                       })
                            continue
                        if not seller_sku:
                            amazon_process_log and amazon_transaction_log_obj.create({
                                                       'message':"Seller sku not found in file",
                                                       'log_type':'not_found',
                                                       'job_id':amazon_process_log and amazon_process_log.id,   
                                                       'operation_type':'import'                                                    
                                                       })
                            continue
                        if not asin:
                            amazon_process_log and amazon_transaction_log_obj.create({
                                                       'message':"ASIN not found in file",
                                                       'log_type':'not_found',
                                                       'job_id':amazon_process_log and amazon_process_log.id,   
                                                       'operation_type':'import'                                                    
                                                       })
                            continue
                        if default_code:
                            odoo_product = product_obj.search([("default_code","=",default_code)],limit=1)
                        else:
                            amazon_process_log and amazon_transaction_log_obj.create({
                                                       'message':"Internal referance not found in file",
                                                       'log_type':'not_found',
                                                       'job_id':amazon_process_log and amazon_process_log.id,   
                                                       'operation_type':'import'                                                    
                                                       })
                            continue
                        if odoo_product and instance:                                                                    
                            amazon_product_ept_obj.create(
                                {'title':amazon_product_name or odoo_product.name,
                                 'fulfillment_by':fullfillment_by,
                                 'product_asin':asin,
                                 'product_id':odoo_product.id,
                                 'seller_sku':seller_sku,
                                 'instance_id':instance.id,
                                 'exported_to_amazon':True}
                                                          )
                        else:
                            amazon_process_log and amazon_transaction_log_obj.create({
                                                       'message':"Product with internal referance %s is not found in Odoo"%(default_code),
                                                       'log_type':'not_found',
                                                       'job_id':amazon_process_log and amazon_process_log.id,   
                                                       'operation_type':'import'                                                    
                                                       })
                        
                else:
                    raise Warning("Either file is invalid or proper delimiter/separator is not specified or not found required fields.")                
            else:
                raise Warning("Either file format is not csv or proper delimiter/separator is not specified")
        else:
            raise Warning("Please Select File and/or choose Amazon Seller to Import Product")
        
