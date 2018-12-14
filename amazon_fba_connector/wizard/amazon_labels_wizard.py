from odoo import models,fields,api,_
from ..models.api import InboundShipments_Extend
from odoo.exceptions import Warning
import base64
import zipfile
import os
import time

class amazon_shipment_label_wizard(models.TransientModel):
    _name="amazon.shipment.label.wizard"   
    _description = 'amazon.shipment.label.wizard' 
    
    number_of_box = fields.Integer(string='Number of Boxes',default=1)
    number_of_package = fields.Integer(related="number_of_box",string='Number of Labels')
    page_type = fields.Selection([('PackageLabel_Letter_2','PackageLabel_Letter_2'),
                                  ('PackageLabel_Letter_4','PackageLabel_Letter_4'),
                                  ('PackageLabel_Letter_6','PackageLabel_Letter_6'),
                                  ('PackageLabel_A4_2','PackageLabel_A4_2'),
                                  ('PackageLabel_A4_4','PackageLabel_A4_4'),
                                  ('PackageLabel_Plain_Paper','PackageLabel_Plain_Paper')],
                                 required=True,
                                 string='Package Type',
                                 help="""
    * PackageLabel_Letter_2 : Two labels per US Letter label sheet. Supported in Canada and the US. Note that this is the only valid value for Amazon-partnered shipments in the US that use UPS as the carrier.\n
    * PackageLabel_Letter_4 : Four labels per US Letter label sheet. Supported in Canada and the US.\n
    * PackageLabel_Letter_6 : Six labels per US Letter label sheet. Supported in Canada and the US. Note that this is the only valid value for non-Amazon-partnered shipments in the US.\n
    * PackageLabel_A4_2 : Two labels per A4 label sheet. Supported in France, Germany, Italy, Spain, and the UK.\n
    * PackageLabel_A4_4 : Four labels per A4 label sheet. Supported in France, Germany, Italy, Spain, and the UK.\n
    * PackageLabel_Plain_Paper: One label per sheet of US Letter paper. Supported in all marketplaces.\n""")
    
    @api.multi 
    def get_instance(self,shipment):
        return shipment.shipment_plan_id.instance_id
    
    @api.multi
    def get_labels_from_amazon(self,label_type,mws_obj,shipment_rec,number_of_pallet,number_of_package):
        if label_type=='delivery':
            result=mws_obj.GetPalletLabels(shipment_rec.shipment_id,self.page_type,str(number_of_pallet))            
        else:
            result=mws_obj.GetPackageLabels(shipment_rec.shipment_id,self.page_type,str(number_of_package))
        return result
    @api.multi
    def get_unique_labels_from_amazon(self,label_type,mws_obj,shipment_rec):
        list_box_no=[]
        if shipment_rec.partnered_small_parcel_ids:
            for parcel in shipment_rec.partnered_small_parcel_ids:
                list_box_no.append(parcel.box_no)
        else:
            for parcel in shipment_rec.partnered_ltl_ids:
                list_box_no.append(parcel.box_no)
        if not list_box_no:
            raise Warning("No Box inforation found for unique labels")
        result=mws_obj.GetUniquePackageLabels(shipment_rec.shipment_id,self.page_type,list_box_no)
        return result

    @api.multi
    def get_labels(self):
        self.ensure_one()
        ctx = self._context.copy() or {}
        shipment_id = ctx.get('active_id')
        model = ctx.get('active_model')
        if not shipment_id or model!='amazon.inbound.shipment.ept':
            return True
        shipment_rec = self.env['amazon.inbound.shipment.ept'].browse(shipment_id) 
        instance=self.get_instance(shipment_rec)
        country_code = instance.marketplace_id.country_id and instance.marketplace_id.country_id.code or ''
        country = instance.marketplace_id.country_id and instance.marketplace_id.country_id.name or ''
        page_type = self.page_type
        label_type = ctx.get('label_type','')
        number_of_package=1
        number_of_pallet=1
        if label_type=='delivery':
            number_of_pallet = self.number_of_package 
        else:
            number_of_package = self.number_of_package    
        flag = False
        if page_type in ['PackageLabel_Letter_2','PackageLabel_Letter_4','PackageLabel_Letter_6'] and country_code not in ['CA','US']:
            flag = True
        if page_type in ['PackageLabel_A4_2','PackageLabel_A4_4'] and country_code not in ['FR','DE','IT','ES','GB']:
            flag = True
        if page_type == 'PackageLabel_Letter_2' and country_code == 'US' and not shipment_rec.is_partnered:
            flag = True
        if page_type == 'PackageLabel_Letter_6' and country_code == 'US' and shipment_rec.is_partnered:
            flag = True
        if flag:
            raise Warning('Please select correct Page Type, Page type %s not supported for country %s.'%(page_type,country))    
        
        mws_obj = InboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code)
        try:
            if shipment_rec.is_partnered:
                result=self.get_unique_labels_from_amazon(label_type, mws_obj, shipment_rec)
            else:                
                result=self.get_labels_from_amazon(label_type, mws_obj, shipment_rec, number_of_pallet, number_of_package)
        except Exception as e:
            try:
                if not shipment_rec.is_partnered:
                    shipment_rec.update_non_partered_carrier()
                    result=self.get_labels_from_amazon(label_type, mws_obj, shipment_rec, number_of_pallet, number_of_package)
                else:
                    if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                        error = mws_obj.parsed_response_error.parsed or {}
                        error_value = error.get('Message',{}).get('value')
                        error_value = error_value if error_value else str(mws_obj.response.content)  
                    else:
                        error_value = str(e)
                    raise Warning(error_value)
            except Exception as e:            
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)
                raise Warning(error_value)
            
        label_doc = result.parsed.get('TransportDocument',{}).get('PdfDocument',{}).get('value','')
        attachment_obj = self.env['ir.attachment']
        shipment_rec.write({'box_count':self.number_of_box})
        if label_doc:
            label_doc = base64.b64decode(label_doc)
            filename = 'package_label_%s.zip'%(time.strftime('%Y%m%d_%H%M%S'))
            label_zip = open('/tmp/%s'%(filename), 'wb')
            label_zip.write(label_doc)
            label_zip.close()
            zip_file = open('/tmp/%s'%(filename), 'rb')
            z = zipfile.ZipFile(zip_file)
            for name in z.namelist():
                path = z.extract(name, '/tmp/')
                fh = open(path, 'rb')
                datas = base64.b64encode(fh.read())
                fh.close()
                if label_type=='delivery':
                    fname = 'Delivery_'+name
                else:
                    fname = 'Shipment_'+name
                attachments = attachment_obj.search([('datas_fname','=',fname),
                                                     ('res_model','=','amazon.inbound.shipment.ept'),
                                                     ('res_id','=',shipment_rec.id)
                                                     ])
                if attachments:
                    attachments.unlink()
                attachment=attachment_obj.create({
                                       'name': fname,
                                       'datas': datas,
                                       'datas_fname': fname,
                                       'res_model':'mail.compose.message',
                                       'type': 'binary'
                                      })
                shipment_rec.message_post(body=_("<b>Amazon Labels Downloaded</b>"),attachment_ids=attachment.ids)
                try:
                    os.remove(path)
                except Exception as e:
                    pass
            zip_file.close()
            try:
                os.remove('/tmp/%s'%(filename))
            except Exception as e:
                pass
        return True
    