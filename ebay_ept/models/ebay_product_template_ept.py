#!/usr/bin/python3
import cgi, sys, time, imp
from datetime import datetime

from odoo import models,fields,api
from odoo.exceptions import Warning
from odoo.fields import One2many

from odoo.tools.translate import html_translate

imp.reload(sys)
PYTHONIOENCODING="UTF-8"


class product_attribute(models.Model):
    _inherit="product.attribute"
    
    ebay_name=fields.Char("eBay Name")
    

class ebay_product_template_ept(models.Model):
    _name="ebay.product.template.ept"
    _description = "eBay Product Template"
    
    @api.multi
    @api.depends('instance_id','instance_id.site_id')
    def get_site_id(self):
        for record in self:
            record.site_id=record.instance_id.site_id
    
    @api.one
    def get_listing_stock(self):
        product_product_obj = self.env['product.product']

        if self.product_type!='individual':            
            count=0
            for variant in self.ebay_variant_ids:
                stock = product_product_obj.get_stock_ept(variant.product_id,variant.instance_id.warehouse_id.id,variant.ebay_stock_type,variant.ebay_stock_value,variant.instance_id.stock_field.name)            
                if stock <=0.0:
                    count=count+1
            if count == len(self.ebay_variant_ids.ids):
                self.should_cancel_listing=True
        else:
            self.should_cancel_listing=False
    
    should_cancel_listing=fields.Boolean("Should Cancel Listing",compute="get_listing_stock")
    name = fields.Char('Product Name',size=256,required=True)
    instance_id = fields.Many2one('ebay.instance.ept', string='Instance',required=True)
    title=fields.Char("Title")
    bold_title = fields.Boolean('Bold Title',default=False)
    exported_in_ebay = fields.Boolean("Exported Product To eBay",default=False)    
    description = fields.Html("Description",translate=True, sanitize=False)
    ebay_stock_type =  fields.Selection([('fix','Fix'),('percentage','Percentage')], string='Fix Stock Type')
    ebay_stock_value = fields.Float(string='Fix Stock Value')    
    product_tmpl_id=fields.Many2one("product.template",string="ERP Product",required=True)
    ebay_variant_ids=fields.One2many("ebay.product.product.ept","ebay_product_tmpl_id","Variants")
    attribute_id=fields.Many2one("product.attribute","Variation Specific Image Attribute")    
    ebay_fee_ids=fields.One2many("ebay.fee.ept","ebay_product_tmpl_id","eBay Fees")
    product_listing_ids = One2many("ebay.product.listing.ept","ebay_product_tmpl_id","Product Listing")
    condition_id = fields.Many2one('ebay.condition.ept',string='Condition')
    condition_description=fields.Text("Condition Description")
    category_id1 = fields.Many2one('ebay.category.master.ept',string='Primary Category',help="Primary Category")
    category_id2 = fields.Many2one('ebay.category.master.ept',string='Secondary Category',help="Secondary Category")
    store_categ_id1=fields.Many2one('ebay.category.master.ept',string='Store CategoryID',help="Store Category")
    store_categ_id2=fields.Many2one('ebay.category.master.ept',string='Store Category2ID',help="Store Category")
    attribute_ids = fields.One2many('ebay.attribute.matching','product_tmpl_id',string='Attribute Values')    
    ebay_active_listing_id = fields.Many2one('ebay.product.listing.ept',"eBay Active Listing",compute="_get_ebay_active_product",search="_search_ebay_active_product")
    condition_enabled = fields.Boolean("Condition Enabled",default=False,compute="_get_ebay_features",store=True)
    auto_pay_enabled = fields.Boolean("Auto Pay Enable",default=False,compute="_get_ebay_features",store=True)    
    set_return_policy = fields.Boolean("Return Policy",default=False,compute="_get_ebay_features",store=True)
    digital_good_delivery_enabled=fields.Boolean("DigitalGoodDeliveryEnabled",default=False,compute="_get_ebay_features",store=True)
    site_id=fields.Many2one("ebay.site.details","Site",readonly=True,compute="get_site_id",store=True)
    is_immediate_payment=fields.Boolean("Immediate Payment",default=False)
    digital_delivery=fields.Boolean("Digital Delivery",default=False)
    uuid_type=fields.Char("UUIDType",size=32,help="universally unique identifier for an item")
    product_type = fields.Selection([('variation','Variation'),('individual','Individual')],string='Product Type')
    count_total_variants = fields.Integer("Total Variants",compute="_get_count_variants")
    count_exported_variants = fields.Integer("Exported Variants",compute="_get_count_variants")
    count_active_variants = fields.Integer("Active Variants",compute="_get_count_variants")
    related_dynamic_desc = fields.Boolean("Related", related="instance_id.use_dynamic_desc")
    desc_template_id = fields.Many2one("ebay.description.template",string="Description Template", help="Set Custom Description Template")
    
    @api.multi
    def _get_count_variants(self):
        for record in self:
            total_exported = 0
            total_active = 0
            if record.product_type == 'variation' :
                record.count_total_variants = len(record.ebay_variant_ids)
                if record.exported_in_ebay and record.ebay_active_listing_id :
                    record.count_exported_variants = len(record.ebay_variant_ids)
                    for variant in record.ebay_variant_ids:
                        if variant.is_active_variant:
                            total_active+=1
                    record.count_active_variants = total_active
                else:
                    record.count_exported_variants = 0
                    record.count_active_variants = 0
            else:  
                for variant in record.ebay_variant_ids:
                    if variant.exported_in_ebay:
                        total_exported += 1
                    if variant.ebay_active_listing_id and variant.ebay_active_listing_id.state=='Active':
                        total_active += 1
                record.count_total_variants = len(record.ebay_variant_ids)
                record.count_exported_variants = total_exported
                record.count_active_variants = total_active
    
    @api.multi
    @api.depends('category_id1','category_id2')
    def _get_ebay_features(self):
        for record in self :
            if record.category_id1 or record.category_id2 :
                if record.product_type=='variation':
                    record.condition_enabled =(record.category_id1 and record.category_id1.condition_enabled) or (record.category_id2 and record.category_id2.condition_enabled) or False
                else:
                    record.condition_enabled=False
                record.auto_pay_enabled=(record.category_id1 and record.category_id1.auto_pay_enabled) or (record.category_id2 and record.category_id2.auto_pay_enabled) or False
                record.set_return_policy=(record.category_id1 and record.category_id1.set_return_policy) or (record.category_id2 and record.category_id2.set_return_policy) or False
                record.digital_good_delivery_enabled=(record.category_id1 and record.category_id1.digital_good_delivery_enabled) or (record.category_id2 and record.category_id2.digital_good_delivery_enabled) or False
                
    @api.multi
    def _search_ebay_active_product(self, operator, values):
        product_templ_id = []
        if operator == '!=' :
            self._cr.execute("""SELECT ebay_product_tmpl_id from ebay_product_listing_ept WHERE state = 'Active'""")
            vals = self._cr.dictfetchall()
        elif operator == '=' :
            self._cr.execute("""SELECT distinct ebay_product_tmpl_id from ebay_product_listing_ept WHERE state = 'Ended' except
                                (SELECT distinct ebay_product_tmpl_id from ebay_product_listing_ept WHERE state = 'Active')""")
            vals = self._cr.dictfetchall()
        for template in vals :
            product_templ_id.append(template.get('ebay_product_tmpl_id'))
        return [('id','in',list(set(product_templ_id)))]
    
    @api.multi
    def _get_ebay_active_product(self):
        obj_ebay_product_listing_ept = self.env['ebay.product.listing.ept']
        for ebay_variant in self:
            ebay_product_listing = obj_ebay_product_listing_ept.search([('ebay_product_tmpl_id','=',ebay_variant.id),('state','=','Active')],order='id desc',limit=1)
            ebay_variant.ebay_active_listing_id=ebay_product_listing.id if ebay_product_listing else False
    
#     @api.onchange('product_tmpl_id.attribute_line_ids')
#     def onchange_attribute(self):
#         if self.product_tmpl_id:
#             attribute_ids=[]
#             domain={}
#             for line in self.product_tmpl_id.attribute_line_ids:
#                 attribute_ids.append(line.attribute_id.id)
#             domain.update({'attribute_id':[('id','in',attribute_ids)]})
#             return {'domain':domain}

    @api.multi
    def get_buyer_requirement(self,ebay_config_template):
        buyer_requirement_details = {'BuyerRequirementDetails':{}}
        buyer_requirement_details.get('BuyerRequirementDetails').update({'LinkedPayPalAccount': True if ebay_config_template.is_paypal_account else False})
        buyer_requirement_details.get('BuyerRequirementDetails').update({'ShipToRegistrationCountry': True if ebay_config_template.is_primary_shipping_address else False})
        
        if ebay_config_template.policy_violation_id and ebay_config_template.policy_violation_duration_id:
            buyer_requirement_details.get('BuyerRequirementDetails').update({'MaximumBuyerPolicyViolations':{}})
            buyer_requirement_details.get('BuyerRequirementDetails').get('MaximumBuyerPolicyViolations').update({'Count':ebay_config_template.policy_violation_id.name})
            buyer_requirement_details.get('BuyerRequirementDetails').get('MaximumBuyerPolicyViolations').update({'Period':ebay_config_template.policy_violation_duration_id.name})

        if ebay_config_template.item_count_id and ebay_config_template.item_feedback_score_id:
            buyer_requirement_details.get('BuyerRequirementDetails').update({
                                                                       'MaximumItemRequirements': {'MaximumItemCount':ebay_config_template.item_count_id.name,'MinimumFeedbackScore':ebay_config_template.item_feedback_score_id.name}
                                                                       })
        if ebay_config_template.unpaid_strike_id and ebay_config_template.unpaid_strike_duration_id:
            buyer_requirement_details.get('BuyerRequirementDetails').update({
                                                                       'MaximumUnpaidItemStrikesInfo': {'Count':ebay_config_template.unpaid_strike_id.name,'Period':ebay_config_template.unpaid_strike_duration_id.name}
                                                                       })
        if ebay_config_template.min_feed_score_id:
            buyer_requirement_details.get('BuyerRequirementDetails').update({'MinimumFeedbackScore':ebay_config_template.min_feed_score_id.name})        
        return buyer_requirement_details
    
    @api.multi
    def get_shipping_details(self,ebay_config_template):
        sub_dict={}
        sub_dict.update({'ShippingDetails':{}})
        shipping_service=[]
        calculate_rate=[]
        sub_dict.get('ShippingDetails',{}).update({'ShippingType':ebay_config_template.ship_type})

        for service in ebay_config_template.domestic_shipping_ids:
            if ebay_config_template.ship_type=='Flat':
                shipping_service.append({'ShippingServicePriority':service.priority,
                                         'ShippingService':service.service_id.ship_service ,
                                         'ShippingServiceCost':service.cost or 0.0,
                                         'ShippingServiceAdditionalCost':service.additional_cost or 0.0,
                                         'FreeShipping':service.is_free_shipping
                                        })
            else:
                shipping_service.append({'ShippingServicePriority':service.priority,
                                         'ShippingService':service.service_id.ship_service ,
                                         'FreeShipping':service.is_free_shipping
                                        })
#         if ebay_config_template.ship_type=='Calculated':
#             for service in ebay_config_template.domestic_shipping_ids:
#                 calculate_rate.append({'PackagingHandlingCosts':ebay_config_template.handling_cost or 0.0,
#                                                             'ShippingIrregular' : ebay_config_template.irreg_pack,
#                                                             'ShippingPackage' : ebay_config_template.pack_type,
#                                                             'WeightMajor' : ebay_config_template.max_weight,
#                                                             'WeightMinor' : ebay_config_template.min_weight
#                                                             })
        inter_ship_services=[]
        if ebay_config_template.int_ship_type:
            for service in ebay_config_template.inter_shipping_ids:
                ship_loc = service.custom_loc
                inter_ship_to_loc = []
                is_intr_ship = service.service_id.inter_ship
                additional_cost = service.additional_cost
                
                if ship_loc == 'Worldwide':
                    inter_ship_to_loc.append(ship_loc)
                elif ship_loc == 'Canada':
                    inter_ship_to_loc.append('CA')                        
                elif ship_loc == 'customloc':
                    for cust_locs in service.loc_ids:
                        intr_loc_code = cust_locs.ship_code
                        inter_ship_to_loc.append(intr_loc_code)
                if ebay_config_template.int_ship_type == 'Flat':
                    inter_ship_services.append({
                                                  'ShippingService' : service.service_id.ship_service,
                                                  'ShippingServiceAdditionalCost' : additional_cost,
                                                  'ShippingServiceCost': service.cost,
                                                  'ShippingServicePriority' :service.priority,
                                                  'ShipToLocation' : inter_ship_to_loc
                                              })
                else:
                    inter_ship_services.append({
                                                  'ShippingService' : is_intr_ship,
                                                  'ShippingServicePriority' :service.priority,
                                                  'ShipToLocation' : inter_ship_to_loc
                                              })
#                     calculate_rate.append({'InternationalPackagingHandlingCosts':ebay_config_template.inter_handling_cost or 0.0,
#                                                                 'ShippingIrregular' : ebay_config_template.inter_irreg_pack,
#                                                                 'ShippingPackage' : ebay_config_template.inter_pack_type,
#                                                                 'WeightMajor' : ebay_config_template.inter_max_weight,
#                                                                 'WeightMinor' : ebay_config_template.inter_min_weight
#                                                                 })
        
        if ebay_config_template.inter_max_weight and ebay_config_template.inter_min_weight:
            calculate_rate.append({
                                    'ShippingIrregular' : ebay_config_template.inter_irreg_pack,
                                    'ShippingPackage' : ebay_config_template.inter_pack_type,
                                    'WeightMajor' :{'#text':ebay_config_template.inter_max_weight,'@attrs': {'unit':'lbs'}},
                                    'WeightMinor' :{'#text':ebay_config_template.inter_min_weight,'@attrs': {'unit':'oz'}}
                                })         
        if ebay_config_template.ship_type == 'Calculated' and ebay_config_template.int_ship_type == 'Flat':
            ship_type = 'CalculatedDomesticFlatInternational'
        elif ebay_config_template.ship_type == 'Flat' and ebay_config_template.int_ship_type == 'Calculated':
            ship_type = 'FlatDomesticCalculatedInternational'
        else:
            ship_type=ebay_config_template.ship_type
            
        sub_dict.get('ShippingDetails').update({'ShippingType' : ship_type})
        calculate_rate and sub_dict.update({'ShippingPackageDetails':calculate_rate})
        #sub_dict.get('ShippingDetails',{}).update({'CalculatedShippingRate':calculate_rate})
        sub_dict.get('ShippingDetails',{}).update({'InternationalShippingServiceOption':inter_ship_services})
        sub_dict.get('ShippingDetails',{}).update({'ShippingServiceOptions':shipping_service})                  
        ship_to_locations={}
        if ebay_config_template.additional_locations == 'Worldwide':
            ship_to_locations.update({'ShipToLocations':[]})
            ship_to_locations['ShipToLocations'].append(ebay_config_template.additional_locations)
        elif ebay_config_template.additional_locations == 'unitedstates':
            ship_to_locations.update({'ShipToLocations':[]})
            for cust_locs_cm in ebay_config_template.loc_ids:
                ship_to_locations.get('ShipToLocations',[]).append(cust_locs_cm.ship_code)
        ship_to_locations and sub_dict.update(ship_to_locations)
        exclude_ship_locations=[]
        for loc in ebay_config_template.exclude_ship_location_ids:
            exclude_ship_locations.append(loc.loc_code)
        exclude_ship_locations and sub_dict.get('ShippingDetails',{}).update({'ExcludeShipToLocation':exclude_ship_locations}) 
        return sub_dict

    @api.multi
    def prepare_product_dict(self,ebay_product_template,ebay_config_template,instance,product_type,publish_in_ebay,schedule_time,listing_type=False):
        product_image_obj=self.env['ebay.product.image.ept']
        listing_duration=ebay_config_template.duration_id.name

        cat1_id = ebay_product_template.category_id1.ebay_category_id        
        cat2_id = ebay_product_template.category_id2.ebay_category_id
        if cat1_id and not ebay_product_template.category_id1.ebay_condition_ids:
            ebay_product_template.category_id1.get_item_conditions()
                 
        store_categ1 = ebay_product_template.store_categ_id1
        store_categ2 = ebay_product_template.store_categ_id2
        post_code = instance and instance.post_code
        condition = False
        condition_description = False
        
        if ebay_product_template.condition_id:            
            condition =  ebay_product_template.condition_id.condition_id
            if ebay_product_template.condition_description:
                condition_description=ebay_product_template.condition_description
            elif ebay_product_template.condition_id.description:
                condition_description=ebay_product_template.condition_id.description
            else:
                condition_description=ebay_product_template.condition_id.name
        elif not ebay_product_template.condition_id and ebay_product_template.category_id1 and ebay_product_template.category_id1.ebay_condition_ids:
            ebay_product_template.condition_id = ebay_product_template.category_id1.ebay_condition_ids[0].id
            condition = ebay_product_template.condition_id.condition_id

        prod_desc = (cgi.escape(ebay_product_template.description or ebay_product_template.name).encode("utf-8")).decode('iso-8859-1')
        prod_name = (cgi.escape(ebay_product_template.name).encode("utf-8")).decode('iso-8859-1')
        
        sub_dict={}
        if ebay_product_template.is_immediate_payment:
            sub_dict = {'AutoPay':ebay_product_template.is_immediate_payment,}
        sub_dict.update(self.get_buyer_requirement(ebay_config_template))
        shipping_details = self.get_shipping_details(ebay_config_template)
        sales_tax = False
        if ebay_config_template.state_id :
            if ebay_product_template.product_tmpl_id.taxes_id : 
                sales_tax = self.env['account.tax'].search([('id','in',ebay_product_template.product_tmpl_id.taxes_id.ids),('export_in_ebay','=',True)],limit=1,order='sequence asc')
            elif instance.tax_id and instance.tax_id.export_in_ebay:
                sales_tax = instance.tax_id
        sales_tax and shipping_details.get('ShippingDetails').update({'SalesTax' : {'SalesTaxPercent': float(sales_tax.amount),
                                                                                    'SalesTaxState' : ebay_config_template.state_id.code,
                                                                                    'ShippingIncludedInTax' : ebay_config_template.shipping_included_in_tax}})
        sub_dict.update(shipping_details)
        sub_dict.update({'CategoryBasedAttributesPrefill':True,'CategoryMappingAllowed':True,})
        if instance.ebay_plus:
            sub_dict.update({'eBayPlus':True,})
        condition and sub_dict.update({'ConditionDescription':condition_description,'ConditionID' : condition})
        if product_type != 'individual':
            sub_dict.update({'Description': prod_desc})
        sub_dict.update({'Country' :instance.country_id.code,'Currency' :ebay_config_template.start_price_id.currency_id.name,})
        if ebay_product_template.digital_good_delivery_enabled:
            sub_dict.get('DigitalGoodInfo',{}).update({'DigitalDelivery':ebay_product_template.digital_delivery})
        sub_dict.update({'DispatchTimeMax' :ebay_config_template.hand_time,})
        if post_code :
            sub_dict.update({'PostalCode' : post_code})
        else :
            sub_dict.update({'Location' : instance.country_id.name})
        sub_dict.update({                    
                    'Title':prod_name,
                    'ListingDuration' : listing_duration,
                    'ListingType' :listing_type or ebay_config_template.listing_type,
                    })
        payment_methods=[]
        for payment in ebay_config_template.payment_option_ids:
            payment_methods.append(payment.name)
        sub_dict.update({'PaymentMethods':payment_methods})
        sub_dict.update({'PayPalEmailAddress':instance.email_add})        

        cat1_id and sub_dict.update({'PrimaryCategory' : {"CategoryID":[cat1_id]}})
        brand_name=''
        mpn_name=''
        ItemSpecificsList = []
        for attribute in ebay_product_template.attribute_ids:
            attribute_name = attribute.attribute_id.name
            attribute_value = attribute.value_id.name
            if attribute.attribute_id.is_brand :
                brand_name = attribute_value
                continue
            if attribute.attribute_id.is_mpn :
                mpn_name = attribute_value
                continue
            ItemSpecificsData = {'Name':attribute_name,'Value':attribute_value}
            ItemSpecificsList.append(ItemSpecificsData)
        if brand_name and mpn_name:
            brand_mpn = [
                {'Name': 'Brand','Value': brand_name,},
                {'Name': 'MPN','Value': mpn_name}
            ]      
            ItemSpecificsList+=brand_mpn
        sub_dict.update({'ProductListingDetails':{}})
        ItemSpecificsList and sub_dict.update({'ItemSpecifics':{'NameValueList':ItemSpecificsList}})
        
        if brand_name and mpn_name:
            sub_dict.get('ProductListingDetails',{}).update({'BrandMPN':{'Brand':brand_name,'MPN':mpn_name}})
        else:
            sub_dict.get('ProductListingDetails',{}).update({'BrandMPN':{'Brand':'Unbranded','MPN':'Does not Apply'}})
        
        sub_dict.update({'PictureDetails':{}})
        image_value_ids=[]
        list_image_url=[]
        image_ids=[]
        for variant in ebay_product_template.ebay_variant_ids:
            variant.ebay_image_ids.storage_image_in_ebay()
            image_ids=image_ids + variant.ebay_image_ids.ids
            for image in variant.ebay_image_ids:
                if image.ebay_image_url :
                    list_image_url.append(image.ebay_image_url)
                image.value_id and image_value_ids.append(image.value_id.id)

        galary_image=product_image_obj.search([('id','in',image_ids),('is_galary_image','=',True)],limit=1)
        if galary_image:
            sub_dict.get('PictureDetails').update({'GalleryURL':galary_image.ebay_image_url})
        self.env['ebay.product.image.ept']
        
        if ebay_config_template.ebay_seller_payment_policy_id or ebay_config_template.ebay_seller_return_policy_id \
            or ebay_config_template.ebay_seller_shipping_policy_id:            
            sub_dict.update({'SellerProfiles':{}})
            if ebay_config_template.ebay_seller_payment_policy_id:
                sub_dict.get('SellerProfiles').update({'SellerPaymentProfile':{'PaymentProfileID':ebay_config_template.ebay_seller_payment_policy_id.policy_id}})
            if ebay_config_template.ebay_seller_return_policy_id:
                sub_dict.get('SellerProfiles').update({'SellerReturnProfile':{'ReturnProfileID':ebay_config_template.ebay_seller_return_policy_id.policy_id}})
            if ebay_config_template.ebay_seller_shipping_policy_id:
                sub_dict.get('SellerProfiles').update({'SellerShippingProfile':{'ShippingProfileID':ebay_config_template.ebay_seller_shipping_policy_id.policy_id}})

        if store_categ1 or store_categ2:
            sub_dict.update({'Storefront':{}})
            if store_categ1:
                sub_dict.get('Storefront').update({"StoreCategoryID":store_categ1.ebay_category_id,'StoreCategoryName':(cgi.escape(store_categ1.name).encode("utf-8")).decode("iso-8859-1")})
            if store_categ2:
                sub_dict.get('Storefront').update({"StoreCategory2ID":store_categ1.ebay_category_id,'StoreCategory2Name':(cgi.escape(store_categ1.name).encode("utf-8")).decode("iso-8859-1")})
    
        if ebay_config_template.payment_instructions:
            sub_dict.update({'PaymentInstructions': (cgi.escape(ebay_config_template.payment_instructions).encode("utf-8")).decode("iso-8859-1")})
        if ebay_product_template.uuid_type:
            sub_dict.update({'UUID':ebay_product_template.uuid_type})
        sub_dict.update({'ReturnPolicy':{}})        
        sub_dict.get('ReturnPolicy').update({'ReturnsAcceptedOption':ebay_config_template.return_policy})
        if ebay_config_template.return_policy=='ReturnsAccepted':
            sub_dict.get('ReturnPolicy').update({'RefundOption':ebay_config_template.refund_option_id.name,'ReturnsWithinOption':ebay_config_template.return_days_id.name,
                                                 'Description':cgi.escape(ebay_config_template.return_policy_description or '') ,'ShippingCostPaidByOption':ebay_config_template.refund_shipping_cost_id.name
                                                 })
            
        cat2_id and sub_dict.update({'SecondaryCategory' : {"CategoryID":[cat2_id]}})

        if not publish_in_ebay:
            schedule_time = time.strftime("%Y-%m-%dT%H:%M:%S")
            schedule_time = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(schedule_time,"%Y-%m-%dT%H:%M:%S"))))
            schedule_time = str(schedule_time)+'.000Z'
            sub_dict.update({"ScheduleTime":schedule_time})
        
        tax = False
        if ebay_config_template.business_seller or ebay_config_template.restricted_to_business :
            if ebay_product_template.product_tmpl_id.taxes_id : 
                tax = self.env['account.tax'].search([('id','in',ebay_product_template.product_tmpl_id.taxes_id.ids),('export_in_ebay','=',True)],limit=1,order='sequence asc')
            elif instance.tax_id and instance.tax_id.export_in_ebay:
                tax = instance.tax_id
            
        tax and sub_dict.update({'VATDetails':{'BusinessSeller' : ebay_config_template.business_seller, 'RestrictedToBusiness' : ebay_config_template.restricted_to_business,'VATPercent' : float(tax.amount)}})           
        return sub_dict,image_value_ids
    
    @api.multi
    def prepare_variation_product_dict(self,ebay_product_template,ebay_config_template,instance,product_type,publish_in_ebay,schedule_time):
        product_product_obj = self.env['product.product']
        
        start_price=1.0
        sub_dict,image_value_ids=self.prepare_product_dict(ebay_product_template, ebay_config_template,instance,product_type,publish_in_ebay,schedule_time,'FixedPriceItem')
        sub_dict.update({'Variations':{}})
        list_of_name_value_list=[]
        name_value_list=[]
        for line in ebay_product_template.product_tmpl_id.attribute_line_ids:
            attribute=line.attribute_id
            values=[value.name for value in line.value_ids]
            name_value_list.append({'Name':attribute.ebay_name or attribute.name,'Value':values})
        list_of_name_value_list.append({'NameValueList':name_value_list})
        sub_dict.get('Variations').update({'VariationSpecificsSet':list_of_name_value_list})

        list_of_variation=[]
        for variant in ebay_product_template.ebay_variant_ids:
            stock = product_product_obj.get_stock_ept(variant.product_id,instance.warehouse_id.id,variant.ebay_stock_type,variant.ebay_stock_value,instance.stock_field.name)
            variation={}
            start_price=variant.product_id.with_context({'pricelist':ebay_config_template.start_price_id.id,'quantity':1}).price
            variation.update({'SKU':variant.ebay_sku})
            variation.update({'StartPrice' :start_price })
            variation.update({'Quantity' :int(stock)})
            if variant.ean13 or variant.isbn_number or variant.upc_number:
                variation.update({'VariationProductListingDetails':{}})
                variant.ean13 and variation.get('VariationProductListingDetails').update({'EAN':variant.ean13})
                variant.isbn_number and variation.get('VariationProductListingDetails').update({'ISBN':variant.isbn_number})
                variant.upc_number and variation.get('VariationProductListingDetails').update({'UPC':variant.upc_number})
            else:
                variation.update({'VariationProductListingDetails':{
                                                          'UPC':'Does not Apply',
                                                          'ISBN':'Does not Apply',
                                                          'EAN':'Does not Apply'
                                                          }
                                 })            
                
            list_of_variation_specific=[]
            name_value_list=[]
            for value in variant.product_id.attribute_value_ids:
                name_value_list.append({'Name':value.attribute_id.ebay_name or value.attribute_id.name,'Value':value.name})
            list_of_variation_specific.append({'NameValueList':name_value_list})
            variation.update({'VariationSpecifics':list_of_variation_specific})
            list_of_variation.append(variation)
        sub_dict.get('Variations').update({'variation':list_of_variation})
        list_of_variation_pictures=[]
        image_value_ids=list(set(image_value_ids))
        picture_set=[]
        for value_id in image_value_ids:     
            image_urls=[]
            variation_image={}        
            for variant in ebay_product_template.ebay_variant_ids:
                variant.ebay_image_ids.storage_image_in_ebay()
                for image in variant.ebay_image_ids:                           
                    if image.value_id.id==value_id:
                        if 'VariationSpecificValue' not in variation_image:
                            variation_image.update({'VariationSpecificValue':image.value_id.name})
                        if image.ebay_image_url :
                            image_urls.append(image.ebay_image_url)
            variation_image.update({'PictureURL':list(set(image_urls))})   
            picture_set.append(variation_image)                
        list_of_variation_pictures.append({'VariationSpecificPictureSet':picture_set,'VariationSpecificName':ebay_product_template.attribute_id.name})
        sub_dict.get('Variations').update({'Pictures':list_of_variation_pictures})
        
        site_id = instance.site_id
        site_id and sub_dict.update({'Site':site_id.name})
        
        return {'Item':sub_dict}
        
    @api.multi
    def prepare_individual_item_dict(self,ebay_product_template,variant,ebay_config_template,instance,product_type,publish_in_ebay,schedule_time):
        product_product_obj = self.env['product.product']
        
        sub_dict,image_value_ids=self.prepare_product_dict(ebay_product_template, ebay_config_template,instance,product_type,publish_in_ebay,schedule_time)
        default_code = variant.ebay_sku or variant.product_id.default_code
        default_code and sub_dict.update({'SKU' : default_code})
        list_image_url=[]
        for image in variant.ebay_image_ids:
            if image.ebay_image_url :
                list_image_url.append(image.ebay_image_url)
        sub_dict.get('PictureDetails').update({'PictureURL':list_image_url})

        #set the individual product description according to the dynamic description template
        prod_desc = (cgi.escape(variant.description or variant.name).encode("utf-8")).decode("iso-8859-1")
        desc_template_id = ebay_product_template.desc_template_id or ebay_config_template.desc_template_id or False
        if product_type == 'individual' and instance.use_dynamic_desc and desc_template_id :
            prod_desc = "<![CDATA[%s]]>" %desc_template_id.description
            for attribute in desc_template_id.line_ids:
                if attribute.text in prod_desc:
                    if hasattr(variant.product_id, attribute.field_id.name):
                        if getattr(variant.product_id, attribute.field_id.name):
                            value = getattr(variant.product_id, attribute.field_id.name)
                            prod_desc = prod_desc.replace(attribute.text,value)
                        else:
                            prod_desc = prod_desc.replace(attribute.text,'')
        sub_dict.update({'Description' : prod_desc})

        condition = False
        condition_description = False
        if variant.condition_id:            
            condition =  variant.condition_id.condition_id
            if variant.condition_description:
                condition_description=variant.condition_description
            elif variant.condition_id.description:
                condition_description=variant.condition_id.description
            else:
                condition_description=variant.condition_id.name  
        elif not variant.condition_id and ebay_product_template.category_id1 and ebay_product_template.category_id1.ebay_condition_ids:
            variant.condition_id = ebay_product_template.category_id1.ebay_condition_ids[0].id
            condition = variant.condition_id.condition_id
            
        if variant.ean13 or variant.isbn_number or variant.upc_number:
            variant.ean13 and sub_dict.get('ProductListingDetails').update({'EAN':variant.ean13})
            variant.isbn_number and sub_dict.get('ProductListingDetails').update({'ISBN':variant.isbn_number})
            variant.upc_number and sub_dict.get('ProductListingDetails').update({'UPC':variant.upc_number})
        else:
            sub_dict.update({'ProductListingDetails':{'UPC':'Does not Apply',
                                                      'ISBN':'Does not Apply',
                                                      'EAN':'Does not Apply'}})            
            
        if ebay_config_template.reserve_price_id and ebay_config_template.listing_type =='Chinese':            
            reserve_price_ept=variant.product_id.with_context({'pricelist':ebay_config_template.reserve_price_id.id,'quantity':1}).price
            sub_dict.update({'ReservePrice' :{'#text': reserve_price_ept,'@attrs': {'currencyID': ebay_config_template.reserve_price_id.currency_id.name}}})
            
        if ebay_config_template.buy_it_nw_price_id and ebay_config_template.listing_type =='Chinese':
            buy_it_now_price_ept=variant.product_id.with_context({'pricelist':ebay_config_template.buy_it_nw_price_id.id,'quantity':1}).price
            sub_dict.update({'BuyItNowPrice' : {'#text': buy_it_now_price_ept,'@attrs': {'currencyID':ebay_config_template.buy_it_nw_price_id.currency_id.name}}})            

        site_id = instance.site_id
        stock = product_product_obj.get_stock_ept(variant.product_id,instance.warehouse_id.id,variant.ebay_stock_type,variant.ebay_stock_value,instance.stock_field.name)
        start_price=variant.product_id.with_context({'pricelist':ebay_config_template.start_price_id.id,'quantity':1}).price
        condition and sub_dict.update({'ConditionDescription':condition_description,'ConditionID' : condition})
        site_id and sub_dict.update({'Site':site_id.name,'Quantity':int(stock), 'StartPrice' : {'#text': start_price,'@attrs': {'currencyID': ebay_config_template.start_price_id.currency_id.name}}})
        return {'Item':sub_dict}
    
    @api.multi
    def create_individual_item(self,ebay_config_template,ebay_product_template,instance,publish_in_ebay,schedule_time):
        ebay_product_variant_obj=self.env['ebay.product.product.ept']
        ebay_variants=ebay_product_template.ebay_variant_ids
        product_listing_obj=self.env['ebay.product.listing.ept']

        msg_id = 1
        add_items = {'AddItemRequestContainer':[]}
        variant_ids_dict = {}
        results = False
        ebay_error_sku_list = []
        
        for variant in ebay_variants:
            if product_listing_obj.search([('ebay_variant_id','=',variant.id),('instance_id','=',instance.id),('state','=','Active')]):
                continue
            
            product_dict = self.prepare_individual_item_dict(ebay_product_template,variant,ebay_config_template,instance,'individual',publish_in_ebay,schedule_time)
            product_dict.update({'MessageID':msg_id})
            add_items['AddItemRequestContainer'].append(product_dict)
            variant_ids_dict.update({msg_id:variant.id})
           
            try:
                lang = instance.lang_id and instance.lang_id.code
                if lang:
                    add_items.update({'ErrorLanguage':lang})
                if instance.environment == 'is_sandbox' :
                    api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
                else:
                    api = instance.get_trading_api_object()
                api.execute('AddItems', add_items)
                results = api.response.dict() 
                add_items = {'AddItemRequestContainer':[]}
                product_ids_dict2 = variant_ids_dict
                msg_id = 0 
            except Exception:
                ebay_error_sku = str(variant and variant.ebay_sku or variant.product_id.default_code)
                ebay_error_sku_list += [{ebay_error_sku: api.response.dict()}]
                continue
            
            msg_id += 1
            if not results:
                results={}
            ack = results.get('Ack',False)
            if ack in ["Success","Warning"]:
                AddItemResponse = results.get('AddItemResponseContainer',[])
                AddItemResponse = [AddItemResponse] if type(AddItemResponse) == dict else AddItemResponse 
                for result in AddItemResponse:
                    item_id = result.get('ItemID',False)
                    if item_id:
                        message_id = result.get('CorrelationID',1)
                        variant_id=product_ids_dict2.get(int(message_id))
                        variant=ebay_product_variant_obj.browse(variant_id)
                        product_listing_obj.create({
                            'name':item_id,
                            'instance_id':instance.id,
                            'ebay_template_id':ebay_config_template.id,
                            'ebay_product_tmpl_id':variant.ebay_product_tmpl_id.id,
                            'ebay_variant_id':variant.id,
                            'start_time':result.get('StartTime'),
                            'end_time':result.get("EndTime"),  
                            'state':'Active',
                            'listing_type': ebay_config_template.listing_type,
                            'listing_duration': ebay_config_template.duration_id and ebay_config_template.duration_id.name,
                            'product_type': 'Individual'                                    
                        })
                    variant.ebay_product_tmpl_id.write({'exported_in_ebay':True})
                    variant.write({'exported_in_ebay':True})
                    fees=result.get('Fees',{}).get('Fee')
                    self.update_fees_ept(fees, variant.ebay_product_tmpl_id,variant)
                    self._cr.commit()         
        return True,ebay_error_sku_list
   
    @api.multi
    def create_variation_item(self,ebay_config_template,ebay_product_template,instance,publish_in_ebay,schedule_time):
        product_listing_obj=self.env['ebay.product.listing.ept']
        product_product_obj = self.env['product.product']
        
        if product_listing_obj.search([('ebay_product_tmpl_id','=',ebay_product_template.id),('state','=','Active'),('instance_id','=',instance.id)]):
            ebay_product_template.write({'exported_in_ebay':True})
            return True
        product_dict=self.prepare_variation_product_dict(ebay_product_template,ebay_config_template,instance,'variation',publish_in_ebay,schedule_time)
        product_dict.update({'WarningLevel':'High',})
        ebay_error_sku_list = []
          
        if instance.environment == 'is_sandbox' :
            api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
        else:
            api = instance.get_trading_api_object()
        try:
            result=api.execute('AddFixedPriceItem',product_dict)     
            result_of_dict=result.dict()
            if result_of_dict.get('Ack') in ["Success","Warning"]:
                item_id=result_of_dict.get('ItemID')
                product_listing_obj.create({'name':item_id,
                                            'instance_id':instance.id,
                                            'ebay_template_id':ebay_config_template.id,
                                            'ebay_product_tmpl_id':ebay_product_template.id,
                                            'start_time':result_of_dict.get('StartTime'),
                                            'end_time':result_of_dict.get("EndTime"),  
                                            'state':'Active',                                         
                                            'listing_type':'FixedPriceItem',
                                            'product_type':'Variations'                                    
                                            })
                ebay_product_template.write({'exported_in_ebay':True})
                for variant in ebay_product_template.ebay_variant_ids:
                    stock = product_product_obj.get_stock_ept(variant.product_id,instance.warehouse_id.id,variant.ebay_stock_type,variant.ebay_stock_value,instance.stock_field.name)
                    if stock > 0.0 :
                        variant.write({'exported_in_ebay':True,'is_active_variant':True})
                fees=result_of_dict.get('Fees',{}).get('Fee')
                self.update_fees_ept(fees, ebay_product_template)
                self._cr.commit()
        except Exception:
            ebay_error_sku = ','.join(str(x.ebay_sku or x.product_id.default_code) for x in ebay_product_template.ebay_variant_ids)
            ebay_error_sku_list += [{ebay_error_sku: api.response.dict()}]
        return True,ebay_error_sku_list
    
    @api.multi
    def update_individual_item(self,ebay_config_template,ebay_product_template,instance,publish_in_ebay,schedule_time):
        product_listing_obj=self.env['ebay.product.listing.ept']
        ebay_variants=ebay_product_template.ebay_variant_ids
        results=False
        ebay_error_sku_list = []
        
        for variant in ebay_variants:    
            product_listing_record = product_listing_obj.search([('ebay_variant_id','=',variant.id),('instance_id','=',instance.id),('state','=','Active')])
            if not product_listing_record :
                continue
            product_dict = self.prepare_individual_item_dict(ebay_product_template,variant,ebay_config_template,instance,'individual',publish_in_ebay,schedule_time)
            product_dict.update({'WarningLevel':'High'})
            product_dict.get('Item',{}).update({'ItemID' : product_listing_record.name or ''})
            try:
                lang = instance.lang_id and instance.lang_id.code
                if lang:
                    product_dict.update({'ErrorLanguage':lang})
                if instance.environment == 'is_sandbox' :
                    api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
                else:
                    api = instance.get_trading_api_object()
                api.execute('ReviseItem', product_dict)
                results = api.response.dict()
            except Exception:
                #raise Warning(api.response.json())
                ebay_error_sku = str(variant and variant.ebay_sku or variant.product_id.default_code)
                ebay_error_sku_list += [{ebay_error_sku: api.response.json()}]
                continue
            
            if not results: results={}
            ack = results.get('Ack',False)
            if ack in ["Success","Warning"]:
                AddItemResponse = results.get('AddItemResponseContainer',[])
                AddItemResponse = [AddItemResponse] if type(AddItemResponse) == dict else AddItemResponse 
                for result in AddItemResponse:
                    item_id = result.get('ItemID',False)
                    if item_id:
                        product_listing_record.write({'name':item_id,
                                                    'instance_id':instance.id,
                                                    'ebay_template_id':ebay_config_template.id,
                                                    'ebay_product_tmpl_id':variant.ebay_product_tmpl_id.id,
                                                    'ebay_variant_id':variant.id,
                                                    'start_time':result.get('StartTime'),
                                                    'end_time':result.get("EndTime"),  
                                                    'state':'Active',
                                                    'listing_type':ebay_config_template.listing_type,
                                                    'product_type':'Individual'                                    
                                                    })
                    fees=result.get('Fees',{}).get('Fee')
                    self.update_fees_ept(fees, variant.ebay_product_tmpl_id,variant)                    
                    self._cr.commit()         
        return True,ebay_error_sku_list

    @api.multi
    def update_variation_item(self,ebay_config_template,ebay_product_template,instance,publish_in_ebay,schedule_time):
        product_listing_obj=self.env['ebay.product.listing.ept']
        product_product_obj = self.env['product.product']
        
        ebay_error_sku_list = []
        product_listing_record = product_listing_obj.search([('ebay_product_tmpl_id','=',ebay_product_template.id),('state','=','Active'),('instance_id','=',instance.id)])
        if not product_listing_record :
            return True,ebay_error_sku_list
        
        product_dict=self.prepare_variation_product_dict(ebay_product_template,ebay_config_template,instance,'variation',publish_in_ebay,schedule_time)
        product_dict.get('Item',{}).update({'ItemID' : product_listing_record.name or ''})
        product_dict.update({'WarningLevel':'High'})
        
        if instance.environment == 'is_sandbox' :
            api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
        else:
            api = instance.get_trading_api_object()
        try:
            result=api.execute('ReviseFixedPriceItem',product_dict)     
            result_of_dict=result.dict()
            if result_of_dict.get('Ack') in ["Success","Warning"]:
                item_id=result_of_dict.get('ItemID')
                product_listing_record.write({'name':item_id,
                                            'instance_id':instance.id,
                                            'ebay_template_id':ebay_config_template.id,
                                            'ebay_product_tmpl_id':ebay_product_template.id,
                                            'start_time':result_of_dict.get('StartTime'),
                                            'end_time':result_of_dict.get("EndTime"),  
                                            'state':'Active',                                         
                                            'listing_type':'FixedPriceItem',
                                            'product_type':'Variations'                                    
                                            })
                fees=result_of_dict.get('Fees',{}).get('Fee')
                self.update_fees_ept(fees, ebay_product_template)
                for variant in ebay_product_template.ebay_variant_ids:
                    stock = product_product_obj.get_stock_ept(variant.product_id,instance.warehouse_id.id,variant.ebay_stock_type,variant.ebay_stock_value,instance.stock_field.name)
                    if stock <= 0.0 :
                        variant.write({'is_active_variant':False})
                    else:
                        variant.write({'is_active_variant':True})
                self._cr.commit()
        except Exception:
            #raise Warning(e)
            ebay_error_sku = ','.join(str(x.ebay_sku or x.product_id.default_code) for x in ebay_product_template.ebay_variant_ids)
            ebay_error_sku_list += [{ebay_error_sku: api.response.dict()}]
        return True,ebay_error_sku_list
    
    
    @api.multi
    def update_fees_ept(self,fees,ebay_product_template,variant=False):
        currency_obj=self.env['res.currency']
        fee_obj=self.env['ebay.fee.ept']
        for fee in fees:
            currency=fee.get('Fee',{}).get('_currencyID')
            currency=currency_obj.search([('name','=',currency)])
            value=fee.get('Fee',{}).get('value')
            name=fee.get('Name')
            domain=[('name','=',name),('value','=',value),('currency_id','=',currency.id),('ebay_product_tmpl_id','=',ebay_product_template.id)]
            variant and domain.append(('ebay_variant_id','=',variant.id))
            exist_fee=fee_obj.search(domain)
            if not exist_fee:
                fee_obj.create({'name':name,'value':value,'currency_id':currency.id,'ebay_product_tmpl_id':ebay_product_template.id,'ebay_variant_id':variant and variant.id or False})
        return True

    @api.multi
    def relist_individual_products(self,listing_type,ebay_product_template,instance,product_listing,ebay_config_template=False):
        product_listing_obj = self.env['ebay.product.listing.ept']
        product_dict={}            
        item_id=product_listing.name
        ebay_error_sku_list = []
        
        try:
            if instance.environment == 'is_sandbox' :
                api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
            else:
                api = instance.get_trading_api_object()
            product_dict.update({'Item' : {'ItemID': str(item_id)}})
            if listing_type == 'Chinese' :
                api.execute('RelistItem', product_dict)
            else :
                api.execute('RelistFixedPriceItem', product_dict)
            results = api.response.dict()
        except Exception:
            #raise Warning(e)
            ebay_error_sku = ','.join(str(x.ebay_sku or x.product_id.default_code) for x in ebay_product_template.ebay_variant_ids)
            ebay_error_sku_list += [{ebay_error_sku: api.response.dict()}]
            return True,ebay_error_sku_list 
        
        if results.get('Ack')=='Success':
            item_id = results.get('ItemID',False)
            item_id=results.get('ItemID')
            product_listing_obj.create({'name':item_id,
                                        'instance_id':instance.id,
                                        'ebay_template_id':ebay_config_template.id,
                                        'ebay_variant_id' : product_listing.ebay_variant_id.id,
                                        'ebay_product_tmpl_id':product_listing.ebay_product_tmpl_id.id,
                                        'start_time':results.get('StartTime'),
                                        'end_time':results.get("EndTime"),  
                                        'state':'Active',
                                        'listing_type':ebay_config_template.listing_type,                                          
                                        })
            product_listing.ebay_product_tmpl_id.write({'exported_in_ebay':True})
            fees=results.get('Fees',{}).get('Fee')
            self.update_fees_ept(fees, product_listing.ebay_product_tmpl_id)
            self._cr.commit()
        return True,ebay_error_sku_list

    @api.multi
    def relist_products(self,listing_type,ebay_product_template,instance,product_listing,ebay_config_template=False):
        product_listing_obj = self.env['ebay.product.listing.ept']
        product_dict={}            
        item_id=product_listing.name
        ebay_error_sku_list = []
        
        try:
            if instance.environment == 'is_sandbox' :
                api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
            else:
                api = instance.get_trading_api_object()
            product_dict.update({'Item' : {'ItemID': str(item_id)}})
            if listing_type == 'Chinese' :
                api.execute('RelistItem', product_dict)
            else :
                api.execute('RelistFixedPriceItem', product_dict)
            results = api.response.dict()
        except Exception:
            #raise Warning(e)
            ebay_error_sku = ','.join(str(x.ebay_sku or x.product_id.default_code) for x in ebay_product_template.ebay_variant_ids)
            ebay_error_sku_list += [{ebay_error_sku: api.response.dict()}]
            return True,ebay_error_sku_list
        
        if results.get('Ack')=='Success':
            item_id = results.get('ItemID',False)
            item_id=results.get('ItemID')
            product_listing_obj.create({'name':item_id,
                                        'instance_id':instance.id,
                                        'ebay_template_id':ebay_config_template.id,
                                        'ebay_product_tmpl_id':product_listing.ebay_product_tmpl_id.id,
                                        'start_time':results.get('StartTime'),
                                        'end_time':results.get("EndTime"),  
                                        'state':'Active',
                                        'listing_type':ebay_config_template.listing_type,                                          
                                        })
            product_listing.ebay_product_tmpl_id.write({'exported_in_ebay':True})
            fees=results.get('Fees',{}).get('Fee')
            self.update_fees_ept(fees, product_listing.ebay_product_tmpl_id)
            self._cr.commit()
        return True,ebay_error_sku_list
    
    @api.multi
    def cancel_products_listing(self,ebay_product_template,instance,ebay_active_listing,ending_reason):
        instance = ebay_active_listing.instance_id
        item_id = ebay_active_listing.name
        difft_time = datetime.utcnow() - datetime.now()
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
            ebay_active_listing.write({'is_cancel':True,'cancel_listing':True,'ending_reason':ending_reason,'end_time':ebay_end_tm})
            ebay_active_listing.time_remain_function
        except Exception as e:
            raise Warning(str(e))
        return True
            
    @api.multi
    def cancel_individual_products_listing(self,ebay_product_template,instance,ending_reason):
        for variant in ebay_product_template.ebay_variant_ids :
            instance = variant.instance_id
            item_id = variant.ebay_active_listing_id and variant.ebay_active_listing_id.name or False
            if not item_id :
                continue
            difft_time = datetime.utcnow() - datetime.now()
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
                variant.ebay_active_listing_id.write({'is_cancel':True,'cancel_listing':True,'ending_reason':ending_reason,'end_time':ebay_end_tm})
                variant.ebay_active_listing_id.time_remain_function
            except Exception as e:
                raise Warning(str(e))
        return True            
            
    @api.multi
    def get_vals_for_product_listing(self,instance,item,product):
        list_details=item.get('ListingDetails')
                            
        value={
                'name':item.get('ItemID'),
                'instance_id':instance.id,
                'start_time':list_details.get('StartTime'),
                'end_time':list_details.get('EndTime'),
                'listing_type':item.get('ListingType'),
                'ebay_product_tmpl_id':product.ebay_product_tmpl_id.id,
                'ebay_variant_id':product.id
            }
        return value     
        
    @api.multi
    def update_item(self,instance,item,job):
        ebay_transaction_line_obj=self.env['ebay.transaction.line']
        item_id=item.name
        results={} 
        try:
            api = instance.get_trading_api_object()
            product_dict={'ItemID':item_id}
            api.execute('GetItem', product_dict)
            results = api.response.dict()             
        except Exception as e:
            ebay_transaction_line_obj.create({
                                              'model_id' : ebay_transaction_line_obj.get_model_id('ebay.product.listing.ept'),
                                              'res_id':item.id,
                                              'job_id':job.id,
                                              'message': e
                                              }
                                             )
            pass 
        if results.get('Ack')=='Success':
            start_time=results.get('Item',{}).get('ListingDetails',{}).get('StartTime')
            end_time=results.get('Item',{}).get('ListingDetails',{}).get('EndTime')
            item.write({'start_time':start_time,'end_time':end_time})
            item._get_time_remain_funtion()
        return results
        
    @api.multi
    def get_item(self,instance,item_id):
        ebay_product_product_obj = self.env['ebay.product.product.ept']
        product_product_obj = self.env['product.product']
        product_listing_obj=self.env['ebay.product.listing.ept']
        ebay_product_template_obj = self.env['ebay.product.template.ept']
        results = {} 
        try:
            api = instance.get_trading_api_object()
            product_dict={'ItemID':item_id}
            api.execute('GetItem', product_dict)
            results = api.response.dict()             
        except Exception:
            pass 
        if results.get('Ack')=='Success':
            item=results.get('Item')
            listing_record=product_listing_obj.search([('name','=',item.get('ItemID'))])
            if listing_record:
                return listing_record[0].ebay_variant_id and listing_record[0].ebay_variant_id.ebay_sku or False
            if item.get('SKU',False):
                if ebay_product_product_obj.search([('ebay_sku','=',item.get('SKU'))]):
                    ebay_product_result=ebay_product_product_obj.search([('instance_id','=',instance.id),('ebay_sku','=',item.get('SKU'))])
                    value = self.get_vals_for_product_listing(instance,item,ebay_product_result)
                    product_listing_obj.create(value)
                elif product_product_obj.search([('default_code','=',item.get('SKU'))]):
                    product_result=product_product_obj.search([('default_code','=',item.get('SKU'))])
                    ebay_tmp_record=ebay_product_template_obj.search([('product_tmpl_id','=',product_result.product_tmpl_id.id)])
                    if not ebay_tmp_record: 
                        value={
                                'name':item.get('Title'),
                                'instance_id':instance.id,
                                'exported_in_ebay':True,
                                'description':item.get('Description'),
                                'product_tmpl_id':product_result.product_tmpl_id.id
                                }    
                        ebay_tmp_record=ebay_product_template_obj.create(value)
                    for variant in product_result.product_tmpl_id.product_variant_ids:
                        if ebay_product_product_obj.search([('product_id','=',variant.id),('instance_id','=',instance.id)]):
                            continue
                        value={
                                    'product_id':variant.id,
                                    'ebay_sku':variant.default_code,
                                    'ebay_product_tmpl_id':ebay_tmp_record.id,
                                    'instance_id':instance.id,
                                    'name': variant.product_tmpl_id.name,
                                    }
                        ebay_product_record=ebay_product_product_obj.create(value) 
                        if variant.default_code==item.get('SKU',False):
                            ebay_product_record.write({'exported_in_ebay':True})
                            value=self.get_vals_for_product_listing(instance, item, ebay_product_record)
                            product_listing_obj.create(value)                                
            return item.get('SKU')
        else:
            return ''

    @api.multi
    def unlink(self):
        for record in self:
            if record.ebay_variant_ids :
                record.ebay_variant_ids.unlink()        
        return super(ebay_product_template_ept,self).unlink()
    
class ebay_product_product_ept(models.Model):
    _name="ebay.product.product.ept"
    _description = "eBay Product Product"
    
    @api.multi
    def _get_ebay_active_product(self):
        obj_ebay_product_listing_ept = self.env['ebay.product.listing.ept']
        for ebay_variant in self:
            ebay_product_listing = obj_ebay_product_listing_ept.search([('ebay_variant_id','=',ebay_variant.id),('state','=','Active')],order='id desc',limit=1)
            ebay_variant.ebay_active_listing_id=ebay_product_listing.id if ebay_product_listing else False
    
    @api.multi
    @api.depends("ebay_product_tmpl_id.attribute_id")
    def get_parent_attribute(self):
        for record in self:
            record.attribute_id=record.ebay_product_tmpl_id.attribute_id and record.ebay_product_tmpl_id.attribute_id.id 
    
    name = fields.Char('Product Name',size=256,required=True)    
    ebay_feedback_ids=fields.One2many("ebay.feedback.ept","ebay_product_id",'ebay Feedback')
    instance_id = fields.Many2one('ebay.instance.ept', string='Instance',  required=True)
    ebay_sku = fields.Char('Product Sku',size=64)
    ebay_variant_id=fields.Char("Variant ID") 
    
    product_id=fields.Many2one("product.product","Product",required=True)
    ebay_product_tmpl_id=fields.Many2one("ebay.product.template.ept","Product template",required=True,ondelete="cascade")
    exported_in_ebay = fields.Boolean("Exported Product To eBay",default=False)
    ebay_image_ids=fields.One2many("ebay.product.image.ept","ept_product_id",'Product Images')
    ebay_stock_type =  fields.Selection([('fix','Fix'),('percentage','Percentage')], string='Fix Stock Type')
    ebay_stock_value = fields.Float(string='Fix Stock Value')    
    code_type = fields.Selection([('EAN','EAN'),('ISBN','ISBN'),('UPC','UPC')],string='Code Type',default=False)
    ean13=fields.Char(related="product_id.barcode",string="Ean13",store=False,readonly=True)
    upc_number=fields.Char("UPC Number")
    isbn_number=fields.Char("ISBN number")
    is_active_variant=fields.Boolean("Is Active Variant",copy=False,default=False)
    ebay_active_listing_id = fields.Many2one('ebay.product.listing.ept',"eBay Active Listing",compute="_get_ebay_active_product")
    condition_enabled = fields.Boolean("Condition Enabled",default=False,compute="_get_product_ebay_features",store=True)
    condition_id = fields.Many2one('ebay.condition.ept',string='Condition') 
    condition_description=fields.Text("Condition Description")
    category_id1 = fields.Many2one('ebay.category.master.ept',related="ebay_product_tmpl_id.category_id1",string='Primary Category',help="Primary Category")
    category_id2 = fields.Many2one('ebay.category.master.ept',related="ebay_product_tmpl_id.category_id2",string='Secondary Category',help="Secondary Category")
    attribute_id=fields.Many2one("product.attribute","Variation Specific Image Attribute",compute="get_parent_attribute",store=True)     
    description = fields.Html("Description",translate=html_translate, sanitize_attributes=False)
    product_type = fields.Selection([('variation','Variation'),('individual','Individual')],string='Product Type',related="ebay_product_tmpl_id.product_type")
    
    @api.multi
    @api.depends('ebay_product_tmpl_id.category_id1','ebay_product_tmpl_id.category_id2')
    def _get_product_ebay_features(self):
        for record in self :
            if record.ebay_product_tmpl_id.product_type=='individual':
                if record.ebay_product_tmpl_id.category_id1 or record.ebay_product_tmpl_id.category_id2 :
                    record.condition_enabled =(record.ebay_product_tmpl_id.category_id1 and record.ebay_product_tmpl_id.category_id1.condition_enabled) or (record.ebay_product_tmpl_id.category_id2 and record.ebay_product_tmpl_id.category_id2.condition_enabled) or False
            else:
                record.condition_enabled=False

    @api.multi
    def update_price(self,instance,ebay_products=False):
        listing_obj = self.env['ebay.product.listing.ept']
        if not ebay_products:
            ebay_products = self.search([('instance_id','=',instance.id),('exported_in_ebay','=',True)])        
        if not ebay_products:
            return True
        price_list = []
        ebay_products_len=len(ebay_products)
        for ebay_product in ebay_products:
            price=instance.pricelist_id.get_product_price(ebay_product.product_id,1.0,partner=False,uom_id=ebay_product.product_id.uom_id.id)
            
            listing = False
            if ebay_product.ebay_product_tmpl_id and ebay_product.ebay_product_tmpl_id.product_type == "individual":
                listing = listing_obj.search([('name','!=',''),('instance_id','=',instance.id),('ebay_variant_id','=',ebay_product.id),('state', '=', 'Active')], order='id desc', limit=1)
            elif ebay_product.ebay_product_tmpl_id and ebay_product.ebay_product_tmpl_id.product_type == "variation":
                listing = listing_obj.search([('name','!=',''),('instance_id','=',instance.id),('ebay_product_tmpl_id','=',ebay_product.ebay_product_tmpl_id.id),('state','=','Active')],order='id desc',limit=1)
                                         
            sku = ebay_product.ebay_sku or ebay_product.product_id.default_code
            price_list = price_list + [{'ItemID':listing.name,'StartPrice':price,'SKU':sku}]
            if len(price_list) == 4 or ebay_products_len==len(price_list):            
                para = {'InventoryStatus': price_list}
                lang = instance.lang_id and instance.lang_id.code
                
                if lang:
                    para.update({'ErrorLanguage':lang}) 
                try:
                    api = instance.get_trading_api_object()
                    api.execute('ReviseInventoryStatus', para)
                    price_list=[]
                except Exception:
                    pass
        if price_list:            
            para = {'InventoryStatus': price_list}
            lang = instance.lang_id and instance.lang_id.code
            
            if lang:
                para.update({'ErrorLanguage':lang}) 
            try:
                api = instance.get_trading_api_object()
                api.execute('ReviseInventoryStatus', para)
                price_list=[]
            except Exception:
                pass
        return True    

    
    @api.multi
    def update_image(self,instance,ebay_products=False):
        listing_obj = self.env['ebay.product.listing.ept']
        if not ebay_products:
            ebay_products = self.search([('instance_id','=',instance.id),('exported_in_ebay','=',True),('state','=','Active')])        
        if not ebay_products:
            return True
        
        image_list={}
        
        for ebay_product in ebay_products:
            listing = listing_obj.search([('name','!=',False),('instance_id','=',instance.id),('ebay_product_tmpl_id','=',ebay_product.ebay_product_tmpl_id.id),('state','=','Active')],order='id desc',limit=1)
            image_urls=[]
           
            for image in ebay_product.ebay_image_ids:
                image_urls.append(image.url)
                
            image_list.update({'Item':{'ItemID':listing.name,'PictureDetails':[{'PictureURL':image_urls}]}})
        
        if image_list:
            para = image_list
            lang = instance.lang_id and instance.lang_id.code
            
            if lang:
                para.update({'ErrorLanguage':lang})  
            
            try:
                api = instance.get_trading_api_object()
                api.execute('ReviseItem', para)
            except Exception:
                pass
        return True

    @api.multi
    def export_stock_levels_ebay(self, instance, ebay_products=False):
        ebay_process_job_log_obj = self.env['ebay.log.book']
        listing_obj = self.env['ebay.product.listing.ept']
        ebay_product_tmpl_obj=self.env['ebay.product.template.ept']
        stock_update_history_obj=self.env['ebay.stock.update.history']
        product_product_obj = self.env['product.product']
        
        job_log_vals = {
            'skip_process' : True,
            'application' : 'sales',
            'operation_type' : 'import',
            'instance_id':instance.id
        }
        job = ebay_process_job_log_obj.create(job_log_vals) 
        
        if not ebay_products:
            ebay_products = self.search([('instance_id','=',instance.id),('exported_in_ebay','=',True)])        
        if not ebay_products:
            return True
                 
        inventory_list = []
        ebay_products_len = len(ebay_products)
        history_records = {}
        already_updated_list = []
        for ebay_product in ebay_products:            
            listing = listing_obj.search([('name','!=',False),('instance_id','=',instance.id),('ebay_variant_id','=',ebay_product.id),('state','=','Active'),('is_cancel','=',False)],order='id desc',limit=1)                    
            if not listing:
                listing = listing_obj.search([('name', '!=', False), ('instance_id', '=', instance.id), ('ebay_variant_id', '=', False), ('ebay_product_tmpl_id', '=', ebay_product.ebay_product_tmpl_id.id), ('state', '=', 'Active'), ('is_cancel', '=', False)], order='id desc', limit=1)
            if not listing:
                continue
            if not instance.allow_out_of_stock_product and ebay_product.ebay_product_tmpl_id.should_cancel_listing:
                ebay_product_tmpl_obj.update_item(instance,listing,job)
                if listing.state == 'Active':
                    ebay_product_tmpl_obj.cancel_products_listing(ebay_product.ebay_product_tmpl_id,instance,listing,'NotAvailable')
                continue
            
            stock=0
            if instance.stock_field:
                stock = product_product_obj.get_stock_ept(ebay_product.product_id,instance.warehouse_id.id,ebay_product.ebay_stock_type,ebay_product.ebay_stock_value,instance.stock_field.name)
            else:
                stock = product_product_obj.get_stock_ept(ebay_product.product_id,instance.warehouse_id.id,ebay_product.ebay_stock_type,ebay_product.ebay_stock_value)
            
            if not instance.allow_out_of_stock_product and int(stock)<=0.0 and ebay_product.ebay_product_tmpl_id.product_type=='individual':
                ebay_product_tmpl_obj.update_item(instance,listing,job)
                if listing.state=='Active':
                    listing.cancel_listing=True
                    listing.ending_reason='NotAvailable'
                    listing.cancel_listing_in_ebay()
                continue
            elif listing.listing_duration!='GTC' and instance.allow_out_of_stock_product and int(stock)<=0.0 and ebay_product.ebay_product_tmpl_id.product_type=='individual':
                ebay_product_tmpl_obj.update_item(instance,listing,job)
                if listing.state=='Active':
                    listing.cancel_listing=True
                    listing.ending_reason='NotAvailable'
                    listing.cancel_listing_in_ebay()
                continue
            
            if int(stock)<=0.0 and ebay_product.ebay_product_tmpl_id.product_type!='individual':
                ebay_product.write({'is_active_variant':False})
            history_record=stock_update_history_obj.search([('ebay_product_id','=',ebay_product.id)])
            if history_record and history_record.last_updated_qty==int(stock):  
                continue
            ##check here if eBay already canceled listing in ERP system
            if listing.id not in already_updated_list:
                ebay_product_tmpl_obj.update_item(instance,listing,job)
            already_updated_list.append(listing.id)
            if listing.state!='Active':
                if ebay_product.ebay_product_tmpl_id.product_type!='individual':
                    ebay_product_tmpl_obj.relist_products(listing.listing_type,ebay_product.ebay_product_tmpl_id,instance,listing,listing.ebay_template_id)                
                else:
                    ebay_product_tmpl_obj.relist_individual_products(listing.listing_type,ebay_product.ebay_product_tmpl_id,instance,listing,listing.ebay_template_id)                

                listing = listing_obj.search([('name', '!=', False), ('instance_id', '=', instance.id), ('ebay_variant_id', '=', ebay_product.id), ('state', '=', 'Active'), ('is_cancel', '=', False)], order='id desc', limit=1)                    
                if not listing:
                    listing = listing_obj.search([('name', '!=', False), ('instance_id', '=', instance.id), ('ebay_variant_id', '=', False), ('ebay_product_tmpl_id', '=', ebay_product.ebay_product_tmpl_id.id), ('state', '=', 'Active'), ('is_cancel', '=', False)], order='id desc', limit=1)            
            if not listing:
                continue
            already_updated_list.append(listing.id)
            if not history_record:
                history_record=stock_update_history_obj.create({'ebay_product_id':ebay_product.id})
            history_records.update({history_record:int(stock)})
            sku = ebay_product.ebay_sku or ebay_product.product_id.default_code            
            if ebay_product.ebay_product_tmpl_id.product_type=='individual':            
                inventory_list = inventory_list + [{'ItemID':listing.name,'Quantity':int(stock) if int(stock) >= 0 else 0}]
            else:
                inventory_list = inventory_list + [{'ItemID':listing.name,'Quantity':int(stock) if int(stock) >= 0 else 0,'SKU':sku}]
            if len(inventory_list) == 4 or ebay_products_len==len(inventory_list):
                para = {'InventoryStatus': inventory_list}
                lang = instance.lang_id and instance.lang_id.code
                if lang:
                    para.update({'ErrorLanguage':lang})
                try:
                    api = instance.get_trading_api_object()
                    api.execute('ReviseInventoryStatus', para)
                    api.response.dict()
                    for record,stock in history_records.items():
                        record.write({'last_updated_qty':stock})
                    history_records={}
                    inventory_list=[]
                except Exception:
                    pass
        if inventory_list:  
            para = {'InventoryStatus': inventory_list}
            lang = instance.lang_id and instance.lang_id.code
            if lang:
                para.update({'ErrorLanguage':lang}) 
            try:
                api = instance.get_trading_api_object()
                api.execute('ReviseInventoryStatus', para)
                api.response.dict()
                for record,stock in history_records.items():
                    record.write({'last_updated_qty':stock})
                history_records={}
                inventory_list=[]
            except Exception:
                pass
        if not job.transaction_log_ids:
            job.unlink()
        return True
            
            
    @api.multi
    def get_stock_ebay(self, ebay_product, location_id, stock_type='virtual_available'):
        actual_stock = 0.0
        product = self.env['product.product'].with_context(location=location_id).browse(ebay_product.product_id.id)
        if hasattr(ebay_product.product_id, stock_type):
            actual_stock = getattr(ebay_product.product_id, stock_type)
        else:
            actual_stock = product.qty_available
        if actual_stock >= 1.00:
            if ebay_product.ebay_stock_type == 'fix':
                if ebay_product.ebay_stock_value >= actual_stock:
                    return actual_stock
                else:
                    return ebay_product.ebay_stock_value

            elif ebay_product.ebay_stock_type == 'percentage':
                quantity = int((actual_stock * ebay_product.ebay_stock_value)/100)
                if quantity >= actual_stock:
                    return actual_stock
                else:
                    return quantity
        return actual_stock
    
    @api.multi
    def open_product_in_ebay(self):
        self.ensure_one()
        product_url = self.ebay_active_listing_id and self.ebay_active_listing_id.ebay_url or ''
        if product_url:
            return {
                'type': 'ir.actions.act_url',
                'url': product_url,
                'nodestroy': True,
                'target': 'new'
            }
        return True
