from odoo import models,fields,api
from . import api as Amazon_api #import OutboundShipments_Extend
from dateutil import parser

class stock_quant_package(models.Model):
    _inherit='stock.quant.package'
    @api.one
    def get_products(self):
        product_ids=[]
        for line in self.partnered_small_parcel_shipment_id.odoo_shipment_line_ids:
            product_ids.append(line.amazon_product_id.id) 
        for line in self.partnered_ltl_shipment_id.odoo_shipment_line_ids:
            product_ids.append(line.amazon_product_id.id) 
        self.amazon_product_ids=product_ids
    amazon_product_ids=fields.One2many("amazon.product.ept",compute="get_products")
    carton_info_ids=fields.One2many("amazon.carton.content.info.ept","package_id",string="Carton Info")
    is_update_inbound_carton_contents=fields.Boolean("Is Update Inbound Carton Contents",default=False,copy=False)
    ul_id=fields.Many2one('product.ul.ept',string="Logistic Unit")
    instance_id=fields.Many2one("amazon.instance.ept","Instance")
    box_no=fields.Char("Box No")
    weight_unit = fields.Selection([('pounds','Pounds'),('kilograms', 'Kilograms'),], string='Weight Unit')
    weight_value = fields.Float('Weight Value')
    is_stacked = fields.Boolean('Is Stacked')
    package_status = fields.Selection([('SHIPPED','SHIPPED'),
                                       ('IN_TRANSIT','IN_TRANSIT'),
                                       ('DELIVERED','DELIVERED'),
                                       ('CHECKED_IN','CHECKED_IN'),
                                       ('RECEIVING','RECEIVING'),
                                       ('CLOSED','CLOSED')],string='Package Status')    
    
    partnered_small_parcel_shipment_id = fields.Many2one("amazon.inbound.shipment.ept","Small Parcel Shipment")
    partnered_ltl_shipment_id = fields.Many2one("amazon.inbound.shipment.ept","LTL Shipment")
    
    amazon_package_no=fields.Char("Amazon Package No.",help="This Field Is Used For The Store Amazon Package No")    
    carrier_phone_no=fields.Char("Carrier Phone No")
    carrier_url=fields.Char("Carrier Url")
    ship_date=fields.Date("Ship Date")
    current_status=fields.Selection([('IN_TRANSIT','In transit to the destination address'),
                                     ('DELIVERED','Delivered to the destination address'),
                                     ('RETURNING','In the process of being returned to the Amazon Fulfillment Network'),
                                     ('RETURNED','Returned to the Amazon Fulfillment Network'),
                                     ('UNDELIVERABLE','Undeliverable because package was lost or destroyed'),
                                     ('DELAYED','DELAYED'),
                                     ('AVAILABLE_FOR_PICKUP','Available for pickup'),
                                     ('CUSTOMER_ACTION','Requires customer action')
                                     ])
    signature=fields.Char("Signed By")
    estimated_arrival_date=fields.Date("Estimated Arrival Date")
    additional_location_info=fields.Selection([('AS_INSTRUCTED',' As instructed'),('CARPORT','Carport'),('CUSTOMER_PICKUP','Picked up by customer'),
                                               ('DECK','Deck'),('DOOR_PERSON','Resident'),('FRONT_DESK','Front desk'),('FRONT_DOOR','Front door'),
                                               ('GARAGE','Garage'),('GUARD','Residential guard'),('MAIL_ROOM','Mail room'),('MAIL_SLOT','Mail slot'),
                                               ('MAILBOX','Mailbox'),('MC_BOY','Delivered to male child'),('MC_GIRL','Delivered to female child'),
                                               ('MC_MAN','Delivered to male adult'),('MC_WOMAN','Delivered to female adult'),('NEIGHBOR','Delivered to neighbour'),
                                               ('OFFICE','Office'),('OUTBUILDING','Outbuilding'),('PATIO','Patio'),('PORCH','Porch'),('REAR_DOOR','Rear door'),
                                               ('RECEPTIONIST','Receptionist'),('RECEIVER','Resident'),('SECURE_LOCATION','Secure location'),('SIDE_DOOR','Side door')
                                               ],string="Additional Info")
    
    @api.multi
    def check_tracking_status(self):
        if self.amazon_package_no and self.current_status not in ['DELIVERED','RETURNED']:
            self.update_tracking_status(self.ids)
        return True
    
    @api.multi
    def update_tracking_status(self,package_ids=[]):
        packages=[]
        if not package_ids:
            packages=self.search([('amazon_package_no','!=',False),('current_status','not in',['DELIVERED','RETURNED'])])
        else:
            packages=self.browse(package_ids)
        for package in packages:
            instance=package.instance_id
            if not instance:
                continue
            proxy_data=instance.seller_id.get_proxy_server()
            mws_obj=Amazon_api.OutboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.code,proxies=proxy_data)
            result=mws_obj.GetPackageTrackingDetails(package.amazon_package_no)
            package_info=result.parsed.get('GetPackageTrackingDetailsResult',{})
            tracking_no=package_info.get('TrackingNumber',{}).get('value')
            carrier_phone_no=package_info.get('CarrierPhoneNumber',{}).get('value')
            carrier_url=package_info.get('CarrierURL',{}).get('value')
            ship_date=package_info.get('ShipDate',{}).get('value')
            current_status=package_info.get('CurrentStatus',{}).get('value')
            signed_by=package_info.get('SignedForBy',{}).get('value')
            estimated_arrival_date=package_info.get('EstimatedArrivalDate',{}).get('value')
            additional_location_info=package_info.get('AdditionalLocationInfo',{}).get('value')
            ship_date = parser.parse(ship_date).strftime('%Y-%m-%d %H:%M:%S') 
            estimated_arrival_date = parser.parse(estimated_arrival_date).strftime('%Y-%m-%d %H:%M:%S') 
            
            package.write({'tracking_no':tracking_no,
                           'carrier_phone_no':carrier_phone_no,
                           'carrier_url':carrier_url,
                           'ship_date':ship_date,
                           'current_status':current_status,
                           'signature':signed_by,
                           'estimated_arrival_date':estimated_arrival_date,
                           'additional_location_info':additional_location_info                           
                           })