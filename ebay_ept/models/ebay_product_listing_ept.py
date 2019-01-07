#!/usr/bin/python3

import time
from datetime import datetime
from time import gmtime

from odoo import models, fields,api
from odoo.exceptions import Warning


class product_listing(models.Model):
    _name = "ebay.product.listing.ept"
    _description = "eBay Product Listing"
    
    @api.one
    def _get_time_remain_funtion(self):
        time_remain1=False
        time_remain=False
        timeremain_str=False
        time_split=False
        locate=False
        locate_first=False
        cur_record_end_time=False
        difft_time = datetime.utcnow() - datetime.now()
        for cur_record in self:
            cur_id = cur_record.id
            cur_record_end_time = cur_record.end_time
            gmt_tm = time.strftime("%Y-%m-%d %H:%M:%S", gmtime())
            new_gmt_time = datetime.strptime(gmt_tm, "%Y-%m-%d %H:%M:%S" )
            trunc_time = str(new_gmt_time)[:19]
            if cur_record_end_time:
                time_remain1 = cur_record_end_time - datetime.strptime(trunc_time, "%Y-%m-%d %H:%M:%S" )
                time_remain = time_remain1 + difft_time
                timeremain_str = str(time_remain)
                time_split = timeremain_str.split('.')
                if time_split:
                    timeremain = time_split[0]
                locate = timeremain
                locate_first = locate[0]
            if  locate_first == '-':
                locate_val = 'Ended'
                cur_record.state='Ended'
                self._cr.execute("UPDATE ebay_product_listing_ept SET state='%s' where id=%d"%(locate_val,cur_id))
                self._cr.commit()
            cur_record.time_remain_function = locate

    name = fields.Char('Item ID', size=64,required=True)
    ebay_feedback_ids=fields.One2many("ebay.feedback.ept","listing_id",'FeedBack') 
    ebay_product_tmpl_id = fields.Many2one('ebay.product.template.ept', string='Product Name', ondelete="cascade", readonly=True)
    ebay_variant_id = fields.Many2one('ebay.product.product.ept', string='Variant Name',readonly= True)

    instance_id = fields.Many2one('ebay.instance.ept', string='Instance Name')
    end_time = fields.Datetime('End Time',size=64)
    start_time = fields.Datetime('Start Time',size=64)
    is_cancel = fields.Boolean('Is Cancelled',readonly=True)
    cancel_listing = fields.Boolean('Cancel Listing')
    ending_reason = fields.Selection([('Incorrect','The start price or reserve price is incorrect'),('LostOrBroken','The item was lost or broken'),('NotAvailable','The item is no longer available for sale'),('OtherListingError','The listing contained an error'),('SellToHighBidder','The listing has qualifying bids')],'Ending Reason')
    ebay_template_id = fields.Many2one('ebay.template.ept','Listing Template')
    time_remain_function = fields.Char(compute="_get_time_remain_funtion",string='Remaining Time')
    state = fields.Selection([('Active','Active'),('Completed','Completed'),('Custom','Custom'),('CustomCode','CustomCode'),('Ended','Ended')],'Status',default="Active")

    listing_type = fields.Selection([('Chinese','Auction'),('FixedPriceItem','Fixed Price'),('LeadGeneration','Classified Ad')],'Listing Type',default='Chinese',required=True,help="Type in which Products to be listed")
    product_type=fields.Selection([('Individual','Individual'),('Variations','Variations')],default="Individual")
    listing_duration = fields.Selection([
        ('Days_3', '3 Days'),
        ('Days_5', '5 Days'),
        ('Days_7', '7 Days'),
        ('Days_10', '10 Days'),
        ('Days_30', '30 Days (only for fixed price)'),
        ('GTC', 'Good \'Til Cancelled (only for fixed price)')],
        string='Listing Duration', default='Days_7')
    ebay_stock = fields.Integer(string="Remaining Stock",help="Remaining stock of the active eBay product")
    ebay_total_sold_qty = fields.Integer(string="Total Sold Qty",help="Total sold quantity in eBay")
    ebay_url = fields.Char(string="Product URL",help="Active eBay product URL.")
    ebay_site_id = fields.Many2one('ebay.site.details','eBay Site')
    
    @api.multi    
    def update_listing(self):
        increment = 0
        for product_listing_record in self:
            product=product_listing_record.prod_list
            product_name = product.name
            ebay_item_id =product_listing_record.name
            instance = product_listing_record.instance_id
            related_template =product_listing_record.related_template
            listing_type = product_listing_record.type
            if related_template and product_listing_record.state!='Ended':
                listing_duration = product_listing_record.listing_duration or 'GTC'
                try:
                    product_dict = self.env['product.listing.templates'].prepare_product_dict(product,related_template,instance,listing_type,listing_duration)
                    
                    if not product_dict.get('Item',False):
                        continue
                    api = instance.get_trading_api_object()
                                        
                    product_dict['Item'].update({'ItemID':ebay_item_id})
                    product_dict = product_dict.copy()
                    api.execute('ReviseItem', product_dict)
                    results = api.response.dict()
                except Exception as e:
                    raise Warning(e)
                api.response.text #api.request.body
    #             results = connection_obj.call(cr, uid,instance_id, 'ReviseItem', ids,product.id,ebay_item_id,title,description_final,subtitle_final,shop.post_code,increment,shop.site_id.site_id)
                #results ={}
                ack = results.get('Ack',False)
                if ack =='Failure':
                    if results.get('LongMessage',False):
                        long_message = results['LongMessage']
                        for each_messsge in long_message:
                            severity_code = each_messsge[0]['SeverityCode']
                            if severity_code == 'Error':
                                Longmessage = each_messsge[0]['LongMessage']
                                product_long_message = ('Error : This %s product cannot be Updated because:') % (product_name)+ ' ' + Longmessage
                                increment += 1
                                product_listing_record.log(increment, product_long_message)
                elif ack =='Warning':
                    if results.get('LongMessage',False):
                        long_message = results['LongMessage']
                        for each_messsge in long_message:
                            severity_code = each_messsge[0]['SeverityCode']
                            if severity_code == 'Warning':
                                Longmessage = each_messsge[0]['LongMessage']
                                product_long_message = ('Warning : %s:') % (product_name)+ ' ' + Longmessage
                                increment += 1
                                product_listing_record.log(increment, product_long_message)
        return True
    
    @api.multi
    def cancel_listing_in_ebay(self):        
        for record in self:
            instance = record.instance_id
            if not instance.check_instance_confirmed_or_not():
                return False
            item_id = record.name
            cancel_listing = record.cancel_listing
            difft_time = datetime.utcnow() - datetime.now()
            if cancel_listing == True:
                ending_reason = record.ending_reason
                results ={}
                try:
                    api = instance.get_trading_api_object()
                    api.execute('EndItem', {'ItemID':item_id,'EndingReason':ending_reason})
                    results = api.response.dict()
                    FMT = '%Y-%m-%d %H:%M:%S'
                    endtime = results.get('EndTime',False)
                    end_tm = self.env['ebay.instance.ept'].openerp_format_date(endtime)
                    endtime = datetime.strptime(end_tm, FMT) - difft_time
                    ebay_end_tm2 = str(endtime)[:19]
                    ebay_end_tm = ebay_end_tm2
                    record.write({'is_cancel':True,'end_time':ebay_end_tm})
                except Exception as e:
                    raise Warning(str(e))
        return True

    @api.multi
    def get_vals_for_product_listing(self,instance,item,product):
        ebay_site_details_obj = self.env['ebay.site.details']
        ebay_site_ids = ebay_site_details_obj.search([('name', '=', item.get('Site'))])
        list_details=item.get('ListingDetails')
        value={
                'name':item.get('ItemID'),
                'instance_id':instance.id,
                'start_time':list_details.get('StartTime'),
                'end_time':list_details.get('EndTime'),
                'listing_type':item.get('ListingType'),
                'listing_duration':item.get('ListingDuration'),
                'ebay_product_tmpl_id':product.ebay_product_tmpl_id.id,
                'ebay_variant_id':product.id,
                'ebay_total_sold_qty':item.get('SellingStatus')['QuantitySold'],
                'ebay_stock':item.get('Quantity'),
                'ebay_url':item.get('ListingDetails')['ViewItemURL'],
                'ebay_site_id': ebay_site_ids and ebay_site_ids.id or False,
                'state':item.get('SellingStatus')['ListingStatus']
            }
        return value
    
    @api.multi
    def update_active_listing(self, instance, item, prod_listing_id):
        ebay_category_master_obj = self.env['ebay.category.master.ept']
        if prod_listing_id:
            ebay_categ1 = False
            ebay_categ2 = False
            categ1 = item.get('PrimaryCategory',{}).get('CategoryID')
            categ2 = item.get('SecondaryCategory',{}).get('CategoryID')
            if categ1:
                ebay_categ1 = ebay_category_master_obj.search([('ebay_category_id','=',categ1)],limit=1)
                if not ebay_categ1:
                    ebay_categ1 = ebay_category_master_obj.create({
                        'name': item.get('PrimaryCategory').get('CategoryName'),
                        'ebay_category_id': categ1
                    })
            if categ2:
                ebay_categ2 = ebay_category_master_obj.search([('ebay_category_id','=',categ2)],limit=1)
                if not ebay_categ2:
                    ebay_categ2 = ebay_category_master_obj.create({
                        'name': item.get('SecondaryCategory').get('CategoryName'),
                        'ebay_category_id': categ2 
                    })
            prod_listing_id.ebay_product_tmpl_id.write({'category_id1':ebay_categ1 and ebay_categ1.id,'category_id2':ebay_categ2 and ebay_categ2.id})
        return True
    
    @api.multi
    def create_variant_ebay_product_images(self, sku, item, ebay_product):
        product_product_obj = self.env['product.product']
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        ebay_product_image_ept_obj = self.env['ebay.product.image.ept']
        
        ebay_pictures = item.get('Variations',{}) and item.get('Variations',{}).get('Pictures',{})
        if ebay_pictures:
            ebay_variation_specific_name = ebay_pictures.get('VariationSpecificName')
            product_attribute = product_attribute_obj.search([('name','=ilike',ebay_variation_specific_name)],limit=1)
            ebay_variation_specific_picture_set = ebay_pictures.get('VariationSpecificPictureSet')    
        
            if not isinstance(ebay_variation_specific_picture_set, list):
                ebay_variation_specific_picture_set = [ebay_variation_specific_picture_set]
            
            for ebay_var_spec_pic_set in ebay_variation_specific_picture_set:
                ebay_variation_specific_value = ebay_var_spec_pic_set.get('VariationSpecificValue')
                product_attribute_value = product_attribute_value_obj.search([('attribute_id','=',product_attribute.id),('name','=',ebay_variation_specific_value)],limit=1)
                odoo_product_id = product_product_obj.search([('default_code','=',sku),('attribute_value_ids','=',product_attribute_value.id)],limit=1)
                
                if odoo_product_id:
                    ebay_picture_urls = ebay_var_spec_pic_set.get('PictureURL')
                    if not isinstance(ebay_picture_urls, list):
                        ebay_picture_urls = [ebay_picture_urls]
                    
                    for ebay_picture_url in ebay_picture_urls:
                        if ebay_product_image_ept_obj.search([('ept_product_id','=',ebay_product.id),('ebay_image_url','=',ebay_picture_url)]):
                            continue
                        else:
                            vals = {
                                'url': ebay_picture_url or '',
                                'ept_product_id': ebay_product and ebay_product.id or False,
                                'ebay_image_url': ebay_picture_url or '',
                                'value_id': product_attribute_value and product_attribute_value.id or False
                            }
                            ebay_product_image_ept_obj.create(vals)
                else:
                    continue
        else:
            return False
        return True
    
    
    @api.multi
    def create_individual_ebay_product_images(self, item, ebay_product):
        if item.get('PictureDetails'):
            ebay_product_image_ept_obj = self.env['ebay.product.image.ept']
            PictureDetails = item.get('PictureDetails') 
            GalleryURL = PictureDetails.get('GalleryURL')
            PictureURLs = PictureDetails.get('PictureURL')
            if PictureDetails and PictureURLs:   
                if not isinstance(PictureURLs,list):
                    PictureURLs = [PictureURLs]
                for PictureURL in PictureURLs:
                    if ebay_product_image_ept_obj.search([('ept_product_id','=',ebay_product.id),('ebay_image_url','=',PictureURL)]):
                        continue
                    else:
                        vals = {
                            'url': PictureURL or '',
                            'ept_product_id': ebay_product and ebay_product.id or False,
                            'ebay_image_url': PictureURL or '',
                            'is_galary_image': True if (GalleryURL==PictureURL) else False 
                        }
                        ebay_product_image_ept_obj.create(vals)
        else:
            return False
        return True
    
     
    @api.multi
    def get_item_listning(self, instance, item, item_id):
        results = {} 
        item = {}
        try:
            api = instance.get_trading_api_object()
            product_dict = {'ItemID':item_id,'DetailLevel':'ItemReturnDescription'}
            api.execute('GetItem', product_dict)
            results = api.response.dict()             
            if results.get('Ack') == 'Success':
                item = results.get('Item')
        except Exception as e:
            raise Warning(('%s') % (str(e)))
        return item if item else {}  
    
    @api.multi
    def set_variant_sku(self,instance,item,variations,product_template):
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        odoo_product_obj = self.env['product.product']

        for variation in variations:
            sku = variation.get('SKU')
            variation_specifics = variation.get('VariationSpecifics')
            name_value_list = variation_specifics.get('NameValueList')
            attribute_value_ids = []
            domain = []
            odoo_product = False
            if not isinstance(name_value_list,list): 
                name_value_list = [name_value_list]
            for name_value in name_value_list:
                attrib_name = name_value.get('Name')    
                attrib_values = [name_value.get('Value')] if not isinstance(name_value.get('Value'),list) else name_value.get('Value')
                product_attribute = product_attribute_obj.search([('name','=ilike',attrib_name)],limit=1)
                if product_attribute:
                    product_attribute_value = product_attribute_value_obj.search([('attribute_id','=',product_attribute.id),('name','in',attrib_values)],limit=1)
                    product_attribute_value and attribute_value_ids.append(product_attribute_value.id)
            for attribute_value_id in attribute_value_ids:
                tpl = ('attribute_value_ids','=',attribute_value_id)
                domain.append(tpl)
            domain and domain.append(('product_tmpl_id','=',product_template.id))
            if domain:    
                odoo_product = odoo_product_obj.search(domain) 
            odoo_product and odoo_product.write({'default_code':sku})
        return True

    @api.multi
    def create_variant_product(self,instance,item,variations):
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        product_template_obj = self.env['product.template']
        prod_attrib_line_obj = self.env['product.attribute.line']
        attrib_line_vals = []
        prod_template_title = item.get('Title') if item.get('Title') else '' 
        product_description = item.get('Description') if item.get('Description') else ''
        start_price = item.get('StartPrice').get('value') or 0.0
        for variation in variations:
            variation_specifics = variation.get('VariationSpecifics')
            name_value_list = variation_specifics.get('NameValueList')
            if not isinstance(name_value_list,list): 
                name_value_list = [name_value_list]
            for name_value in name_value_list:
                attrib_name = name_value.get('Name')    
                attrib_values = [name_value.get('Value')] if not isinstance(name_value.get('Value'),list) else name_value.get('Value')
                attribute = product_attribute_obj.search([('name','=ilike',attrib_name)],limit=1)
                if not attribute:
                    attribute = product_attribute_obj.create({'name':attrib_name})
                attr_val_ids = []
                for attrib_vals in attrib_values:
                    attrib_value = product_attribute_value_obj.search([('attribute_id','=',attribute.id),('name','=',attrib_vals)],limit=1)
                    if not attrib_value:
                        attrib_value = product_attribute_value_obj.create({'attribute_id':attribute.id,'name':attrib_vals})   
                    attr_val_ids.append(attrib_value.id)
                if attr_val_ids:
                    if attrib_line_vals:
                        for attrib_line_val in attrib_line_vals:
                            if attribute.id == attrib_line_val[2].get('attribute_id'):
                                attrib_line_val[2].get('value_ids').extend(attr_val_ids) 
                                break
                            else:
                                continue
                        else:
                            attribute_line_ids_data = (0, 0,{'attribute_id': attribute.id,'value_ids':attr_val_ids})
                            attrib_line_vals.append(attribute_line_ids_data)   
                    else:    
                        attribute_line_ids_data = (0, 0,{'attribute_id': attribute.id,'value_ids':attr_val_ids})
                        attrib_line_vals.append(attribute_line_ids_data)   
        
        if attrib_line_vals:
            vals = {
                'name':prod_template_title,
                'list_price':start_price,
                'type':'product',
                #'attribute_line_ids':attrib_line_vals,
                'description_sale':product_description,
                'sale_ok':True,
                'purchase_ok':True 
            }
            product_template = product_template_obj.create(vals)
            for attrib_line in attrib_line_vals:
                vals = {
                    'product_tmpl_id': product_template.id,
                    'attribute_id': attrib_line[2].get('attribute_id'),
                    'value_ids': [(6, 0, attrib_line[2].get('value_ids'))]
                }
                prod_attrib_line_obj.create(vals)
            product_template.create_variant_ids()
            self.set_variant_sku(instance,item,variations,product_template)
        else:
            return False
        return True

    @api.multi
    def sync_variation_product_listings(self,instance,item,job,variations,is_create_auto_odoo_product):
        product_product_obj = self.env['product.product']
        product_listing_obj=self.env['ebay.product.listing.ept']
        ebay_product_template_obj = self.env['ebay.product.template.ept']
        ebay_log_book_obj=self.env['ebay.log.book']
        ebay_product_product_obj = self.env['ebay.product.product.ept']        
        ebay_log_line_obj=self.env['ebay.transaction.line']
        job=False
        listing = False
                
        for variation in variations:
            sku = variation.get('SKU')        
            if not sku:
                continue
            ebay_product=ebay_product_product_obj.search([('ebay_sku','=',sku),('instance_id','=',instance.id)])
            if ebay_product:           
                value = self.get_vals_for_product_listing(instance,item,ebay_product)
                listing = product_listing_obj.create(value)
                if listing:
                    self.update_active_listing(instance, item, listing)                                       
                break
        
        item_id = item.get('ItemID')
        item_dict = self.get_item_listning(instance, item, item_id)
        for variation in variations:
            sku = variation.get('SKU')   
            if not sku:
                continue
            ebay_product=ebay_product_product_obj.search([('ebay_sku','=',sku),('instance_id','=',instance.id)])
            if ebay_product:
                try:
                    self.create_variant_ebay_product_images(sku, item_dict, ebay_product)
                except Exception:
                    pass
                continue
            
            odoo_product = product_product_obj.search([('default_code','=',sku)])
            if not odoo_product and is_create_auto_odoo_product:
                try:
                    self.create_variant_product(instance,item,variations)
                except Exception:
                    pass
            odoo_product=product_product_obj.search([('default_code','=',sku)])
            if odoo_product:
                ebay_tmp_record=ebay_product_template_obj.search([('product_tmpl_id','=',odoo_product.product_tmpl_id.id),('instance_id','=',instance.id)])
                if not ebay_tmp_record: 
                    value={
                            'name':item.get('Title'),
                            'instance_id':instance.id,
                            'exported_in_ebay':True,
                            'description':item.get('Description'),
                            'product_tmpl_id':odoo_product.product_tmpl_id.id
                            }    
                    ebay_tmp_record=ebay_product_template_obj.create(value)
                for variant in odoo_product.product_tmpl_id.product_variant_ids:
                    if ebay_product_product_obj.search([('product_id','=',variant.id),('instance_id','=',instance.id)]):
                        continue
                    if variant.default_code==sku:
                        value={
                                    'product_id':variant.id,
                                    'ebay_sku':variant.default_code,
                                    'ebay_product_tmpl_id':ebay_tmp_record.id,
                                    'instance_id':instance.id,
                                    'name':variant.product_tmpl_id.name,
                                    'exported_in_ebay':True                                            
                                    }
                        ebay_product_record=ebay_product_product_obj.create(value)
                        if not listing: 
                            value = self.get_vals_for_product_listing(instance, item, ebay_product_record)
                            listing = product_listing_obj.create(value)
            else:
                if not job:
                    value={'instance_id':instance.id,
                            'message':'eBay Sync Products',
                            'application':'sync_products',
                            'operation_type':'import',
                            'skip_process':True
                           }             
                    job= ebay_log_book_obj.create(value)
                job_line_val={'ebay_order_ref':item.get('ItemID'),
                                        'job_id':job.id,
                                        'log_type':'not_found',
                                        'action_type':'skip_line',
                                        'operation_type':'import',
                                        'message':'Product Not found for SKU %s'%(sku),
                                    }
                ebay_log_line_obj.create(job_line_val)                                    
        return True
    
    @api.multi
    def sync_product_listings(self,instance,from_date,to_date,is_create_auto_odoo_product=False):
        product_product_obj = self.env['product.product']
        product_listing_obj=self.env['ebay.product.listing.ept']
        ebay_product_template_obj = self.env['ebay.product.template.ept']
        ebay_log_book_obj=self.env['ebay.log.book']
        ebay_product_product_obj = self.env['ebay.product.product.ept']        
        ebay_log_line_obj=self.env['ebay.transaction.line']
        ebay_site_details_obj = self.env['ebay.site.details']
        
        job=False
        from_date="%sT00:00:00.000Z"%(from_date)
        to_date="%sT00:00:00.000Z"%(to_date)
        page_number = 1
        resultfinal = []
        
        while True:
            products = {}
            try:
                results = {}
                api = instance.get_trading_api_object()
                para = {'DetailLevel':'ItemReturnDescription', 'StartTimeFrom':from_date, 'StartTimeTo':to_date, 'IncludeVariations':True, 'Pagination':{'EntriesPerPage':200, 'PageNumber':page_number}, 'IncludeWatchCount':True}
                api.execute('GetSellerList', para)
                results = api.response.dict()
                if results and results.get('Ack',False) == 'Success':
                    products = results.get('ItemArray', {}) and results['ItemArray'].get('Item', []) or []
            except Exception as e:
                raise Warning(('%s') % (str(e)))
            has_more_trans = results.get('HasMoreItems', 'false')
            if isinstance(products, dict):
                products = [products]
            for result in products:
                resultfinal = resultfinal + [result]
            if has_more_trans == 'false':
                break
            page_number = page_number + 1

        for item in resultfinal:
            product_list = product_listing_obj.search([('name','=',item.get('ItemID'))],limit=1)
            # If Listing Found Process
            if product_list:
                if item.get('Variations',{}):
                    product_list.ebay_product_tmpl_id.write({'product_type':'variation'})
                elif item.get('SKU',False):
                    try:
                        ebay_product = product_list.ebay_product_tmpl_id.ebay_variant_ids[0]
                        self.create_individual_ebay_product_images(item, ebay_product)
                    except Exception:
                        pass
                
                ebay_site_ids = ebay_site_details_obj.search([('name','=',item.get('Site'))],limit=1)
                values = {
                    'start_time': item.get('ListingDetails')['StartTime'],
                    'end_time': item.get('ListingDetails')['EndTime'],
                    'ebay_total_sold_qty': item.get('SellingStatus')['QuantitySold'],
                    'state':item.get('SellingStatus')['ListingStatus'],
                    'ebay_stock': item.get('Quantity'),
                    'ebay_url': item.get('ListingDetails')['ViewItemURL'],
                    'listing_duration': item.get('ListingDuration'),
                    'listing_type': item.get('ListingType'),
                    'ebay_site_id': ebay_site_ids and ebay_site_ids.id or False
                }
                product_list.write(values)
                self.update_active_listing(instance, item, product_list)
                continue
            
            # Variation Listing Process
            variations=item.get('Variations',{}).get('Variation') 
            if variations:
                if not isinstance(variations,list):
                    variations=[variations]
                self.sync_variation_product_listings(instance, item, job, variations, is_create_auto_odoo_product)                    
                continue
            
            # Individual Listing Process
            if item.get('SKU',False):
                ebay_product=ebay_product_product_obj.search([('ebay_sku','=',item.get('SKU')),('instance_id','=',instance.id)])
                if ebay_product:
                    try:
                        self.create_individual_ebay_product_images(item, ebay_product)
                    except Exception:
                        pass 
                    value = self.get_vals_for_product_listing(instance,item,ebay_product)
                    product_listing_id = product_listing_obj.create(value)
                    self.update_active_listing(instance, item, product_listing_id)
                else:
                    if not product_product_obj.search([('default_code','=',item.get('SKU'))]) and is_create_auto_odoo_product:
                        vals = {
                            'name': item.get('Title'),
                            'default_code': item.get('SKU'),
                            'type': 'product',
                            'purchase_ok': True,
                            'sale_ok': True,
                        }
                        product_product_obj.create(vals)
                    
                    odoo_product=product_product_obj.search([('default_code','=',item.get('SKU'))])   
                    if odoo_product:
                        ebay_tmp_record=ebay_product_template_obj.search([('product_tmpl_id','=',odoo_product.product_tmpl_id.id),('instance_id','=',instance.id)])
                        if not ebay_tmp_record: 
                            value={
                                    'name':item.get('Title'),
                                    'instance_id':instance.id,
                                    'exported_in_ebay':True,
                                    'description':item.get('Description'),
                                    'product_tmpl_id':odoo_product.product_tmpl_id.id,
                                    'product_type' : 'individual' if len(odoo_product.product_tmpl_id.product_variant_ids.ids) == 1 else 'variation'                                    
                                    }    
                            ebay_tmp_record=ebay_product_template_obj.create(value)
                        for variant in odoo_product.product_tmpl_id.product_variant_ids:
                            if ebay_product_product_obj.search([('product_id','=',variant.id),('instance_id','=',instance.id)]):
                                continue
                            if variant.default_code==item.get('SKU'):
                                value={
                                            'product_id':variant.id,
                                            'ebay_sku':variant.default_code,
                                            'ebay_product_tmpl_id':ebay_tmp_record.id,
                                            'instance_id':instance.id,
                                            'name':variant.product_tmpl_id.name,
                                            'exported_in_ebay':True                                            
                                            }
                                ebay_product_record=ebay_product_product_obj.create(value) 
                                value=self.get_vals_for_product_listing(instance, item, ebay_product_record)
                                product_listing_obj.create(value)
                    else:
                        if not job:
                            value={'instance_id':instance.id,
                                    'message':'eBay Sync Products',
                                    'application':'sync_products',
                                    'operation_type':'import',
                                    'skip_process':True
                                   }             
                            job= ebay_log_book_obj.create(value)
                        job_line_val={'ebay_order_ref':item.get('ItemID'),
                                                'job_id':job.id,
                                                'log_type':'not_found',
                                                'action_type':'skip_line',
                                                'operation_type':'import',
                                                'message':'Product Not found for SKU %s'%(item.get('SKU')),
                                            }
                        ebay_log_line_obj.create(job_line_val)                                    
            else:
                if not job:
                    value={'instance_id':instance.id,
                            'message':'eBay Sync Products',
                            'application':'sync_products',
                            'operation_type':'import',
                            'skip_process':True
                           }             
                    job= ebay_log_book_obj.create(value)
                job_line_val={'ebay_order_ref':item.get('ItemID'),
                                        'job_id':job.id,
                                        'log_type':'not_found',
                                        'action_type':'skip_line',
                                        'operation_type':'import',
                                        'message':'Product Have no SKU',
                                    }
                ebay_log_line_obj.create(job_line_val)                                    
        return True    