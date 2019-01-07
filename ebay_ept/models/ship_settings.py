#!/usr/bin/python3
from odoo import models, fields,api

class shipping_master(models.Model):
    _name = "ebay.shipping.service"
    _description = "eBay Shipping Service"
    
    name = fields.Char('Shipping Description',required=True)
    ship_time = fields.Char('Shipping time')
    inter_ship = fields.Boolean('International shipping')
    ship_carrier = fields.Char('Shipping Carrier')
    ship_service = fields.Char('Shipping Service')
    ship_service_id = fields.Char('Shipping Service ID')
    ship_type1 = fields.Char('Shipping Type')
    ship_type2 = fields.Char('International Shipping Type')
    ship_detail_version = fields.Char('Shipping Detail Version')
    ship_category = fields.Char('Shipping Category')
    validate_for_sale_flow = fields.Boolean('Validate for Saling Flow')
    sur_chg_applicable = fields.Boolean('Surcharge Applicable')
    dimension_required = fields.Boolean('Dimensions Required')
    cost = fields.Float('Cost($)')
    additional= fields.Float('Each Additional($)')
    site_ids=fields.Many2many("ebay.site.details",'ebay_shipping_service_rel','shipping_id','site_id',required=True)
                 
    @api.model
    def shipping_service_create(self,details,instance):
        site_id=instance.site_id.id
        for info in details:
            serv_desc = info.get('Description',False)
            serv_time = info.get('ShippingTimeMax',False)
            
            serv_carr = info.get('ShippingCarrier',False)
            inter_ship = info.get('InternationalService',False)
            ship_serv = info.get('ShippingService',False)
                
            ship_type1 = info.get('ServiceType1',False)
            surch = info.get('SurchargeApplicable',False)
            dimen = info.get('DimensionsRequired',False)
            ship_ser_id = info.get('ShippingServiceID',False)
            ship_detail_version = info.get('DetailVersion',False)
            validate_for_sale_flow = info.get('ValidForSellingFlow',False)
            ship_category = info.get('ShippingCategory',False)
            
            ship_type = info.get('ServiceType',False)
            ship_type1 = ship_type2 =False
            if type(ship_type) == list and ship_type:
                ship_type1 = ship_type[0]
                ship_type2 = ship_type[1] if len(ship_type)>1 else False
            elif type(ship_type) == str:
                ship_type1 = ship_type
                
            if dimen and (dimen == 'true' or dimen == True):
                dimen_req = True
            else:
                dimen_req = False
                
            if surch and (surch == 'true' or surch == True):
                surch_app = True
            else:
                surch_app = False
            
            if validate_for_sale_flow and (validate_for_sale_flow == 'true' or validate_for_sale_flow == True):
                validate_for_sale_flow = True
            else:
                validate_for_sale_flow = False
                
                
            if inter_ship and (inter_ship == 'true' or inter_ship == True):
                foll = True
                ships = {
                        'name':serv_desc,
                        'ship_time':serv_time,
                        'inter_ship':foll,
                        'ship_carrier':serv_carr,
                        'ship_service':ship_serv,
                        'ship_type1':ship_type1,
                        'ship_type2':ship_type2,
                        'sur_chg_applicable':surch_app,
                        'dimension_required':dimen_req,
                        'ship_service_id' :ship_ser_id,
                        'ship_detail_version' : ship_detail_version,
                        'ship_category' :ship_category,
                        'validate_for_sale_flow' : validate_for_sale_flow,
                        }
            else:
                ships = {
                        'name':serv_desc,
                        'ship_time':serv_time,
                        'ship_carrier':serv_carr,
                        'ship_service':ship_serv,
                        'ship_type1':ship_type1,
                        'ship_type2':ship_type2,
                        'sur_chg_applicable':surch_app,
                        'dimension_required':dimen_req,
                        'ship_service_id' :ship_ser_id,
                        'ship_detail_version' : ship_detail_version,
                        'ship_category' :ship_category,
                        'validate_for_sale_flow' : validate_for_sale_flow,
                        }
            shipping_service = self.env['ebay.shipping.service'].search([('ship_service_id','=',ship_ser_id)])
            if not shipping_service:
                ships.update({'site_ids':[(6,0,[site_id])]})
                self.create(ships)
            else:
                site_ids=list(set(shipping_service.site_ids.ids+[site_id]))
                ships.update({'site_ids':[(6,0,site_ids)]})
                shipping_service.write(ships)      
        return True
class site_details(models.Model):
    _name = "ebay.site.details"
    _description = "eBay Site Details"

    name = fields.Char('Site Name',size=256,required=True)
    site_id = fields.Char('Site ID',size=256,required=True)

    @api.model
    def get_site_details(self,instance,details):
        for record in details:
            site_name = record.get('Site')
            site_id = record.get('SiteID')
            search_site = self.search([('site_id','=',site_id),('name','=',site_name)])
            if not search_site:
                self.create({'name':site_name,'site_id':site_id})
        return True

class loc_master(models.Model):
    _name = "ebay.exclude.shipping.locations"
    _description = "eBay Exclude Shipping Locations"

    name = fields.Char('Location Name')
    loc_code = fields.Char('Location Code')
    region = fields.Char('Region')
    site_ids=fields.Many2many("ebay.site.details",'ebay_shipping_ex_locations_rel','shipping_id','site_id',required=True)
    
    @api.model
    def create_exclude_shipping_locations(self,details,instance):
        site_id=instance.site_id.id
        for info in details:
            loc_name = info.get('Description',False)
            loc_code = info.get('Location',False)
            region = info.get('Region',False)
            location = {
                        'name':loc_name,
                        'loc_code':loc_code,
                        'region':region
                        }
            record = self.search([('name','=',loc_name),('loc_code','=',loc_code)])
            if not record:
                location.update({'site_ids':[(6,0,[site_id])]})
                create_loc = self.create(location)
            else:
                site_ids=list(set(record.site_ids.ids+[site_id]))
                record.update({'site_ids':[(6,0,site_ids)]})                
        return True

class ship_loc_master(models.Model):
    _name = "ebay.shipping.locations"
    _description = "eBay Shipping Locations"

    name = fields.Char('Shipping Location')
    ship_code = fields.Char('Location Code')
    detail_version = fields.Char('Detail Version')
    site_ids=fields.Many2many("ebay.site.details",'ebay_shipping_locations_rel','shipping_id','site_id',required=True)

    @api.model
    def create_shipping_locations(self,details,instance):
        site_id=instance.site_id.id
        for info in details:
            ship_code = info.get('ShippingLocation',False)
            name = info.get('Description',False)
            detail_version = info.get('DetailVersion',False)
            ship_loc = {
                        'name':name,
                        'ship_code':ship_code,
                        'detail_version' :detail_version,
                        }
            record = self.search([('name','=',name),('ship_code','=',ship_code)])
            if not record:
                ship_loc.update({'site_ids':[(6,0,[site_id])]})
                create_loc = self.create(ship_loc)
            else:
                site_ids=list(set(record.site_ids.ids+[site_id]))
                record.update({'site_ids':[(6,0,site_ids)]})                

        return True