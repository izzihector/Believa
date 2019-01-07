#!/usr/bin/python3
# -*- encoding: utf-8 -*- 
import imp, sys
from odoo import models, fields,api
imp.reload(sys)
PYTHONIOENCODING="UTF-8"

class ebay_template_ept(models.Model):
    _name = "ebay.template.ept"
    _description = "eBay Template"
    
    @api.onchange('instance_id')
    def onchange_instance(self):
        if self.instance_id:
            self.site_id=self.instance_id.site_id.id
            self.is_paypal_account=self.instance_id.is_paypal_account
            self.is_primary_shipping_address=self.instance_id.is_primary_shipping_address
            self.start_price_id=self.instance_id.pricelist_id.id
            self.buy_it_nw_price_id=self.instance_id.pricelist_id.id
            self.reserve_price_id=self.instance_id.pricelist_id.id

    @api.onchange('listing_type')
    def onchage_listing_type(self):
        duration=self.env['duration.time'].search([('type','=',self.listing_type)],limit=1)
        self.duration_id=duration and duration.id or False

    name = fields.Char('Template name', size=64,required=True,help="Name of Template")
    instance_id = fields.Many2one('ebay.instance.ept','Instance',required=True)

    payment_option_ids=fields.Many2many('ebay.payment.options','ebay_template_payment_rel','tmpl_id','option_id',"Payments",required=True)       

    hand_time = fields.Selection([('1', '1 Business Day'),('2', '2 Business Days'),('3', '3 Business Days'),('4', '4 Business Days'),('5', '5 Business Days'),('10', '10 Business Days'),('15', '15 Business Days'),('20', '20 Business Days'),('30', '30 Business Days')],string='Handling Tme',required=True,default="1")
       
    is_paypal_account = fields.Boolean('LinkedPayPalAccount',default=False)
    is_primary_shipping_address = fields.Boolean('ShipToRegistrationCountry',default=False)

    unpaid_strike_id=fields.Many2one("ebay.unpaid.item.strike.count",string="UnpaidItemStrikesCount")
    unpaid_strike_duration_id =fields.Many2one("ebay.unpaid.item.strike.duration",string="UnpaidItemStrikesDuration") 

    policy_violation_id=fields.Many2one("ebay.policy.violations",string="NumberOfPolicyViolations")
    policy_violation_duration_id=fields.Many2one("ebay.policy.violations.durations",string="PolicyViolationDuration")

    item_count_id=fields.Many2one("ebay.max.item.counts",string="MaximumItemCount")    
    item_feedback_score_id=fields.Many2one("item.feedback.score",string="MaxItemFeedbackScore")
    min_feed_score_id=fields.Many2one("ebay.feedback.score",string="FeedbackScore")
    

    return_policy = fields.Selection([('ReturnsAccepted', 'Returns Accepted'),('ReturnsNotAccepted', 'Returns Not Accepted')],string='Return Policy',default="ReturnsNotAccepted",required=True,help="Specifies Return Policy Details")
    return_days_id=fields.Many2one("ebay.return.days","ReturnsWithin")
    refund_option_id=fields.Many2one("ebay.refund.options","RefundOption")           
    extended_holiday_returns=fields.Boolean("Extended Holiday Returns",default=False)
    payment_instructions=fields.Text("Payment Instructions")
    refund_shipping_cost_id=fields.Many2one("ebay.refund.shipping.cost.options","ShippingCostPaidBy")
    restock_fee_id=fields.Many2one("ebay.restock.fee.options","RestockingFeeValue")
    return_policy_description = fields.Text('Additional return policy details')
         
    ship_type = fields.Selection([('Flat', 'Flat:same cost to all buyers'),('Calculated', 'Calculated:Cost varies to buyer location')],default='Flat',string='Shipping Type',required=True)
    domestic_shipping_ids = fields.One2many('shipping.service.ept','domestic_template_id',string='Shipping Services')    
    
    #####International shipping fields#########
    int_ship_type = fields.Selection([('Flat', 'Flat:same cost to all buyers'),('Calculated', 'Calculated:Cost varies to buyer location')],string='International Shipping Type')
    inter_shipping_ids = fields.One2many('shipping.service.ept','inter_template_id',string='International Shipping Services')    
    
    handling_cost = fields.Char(string='Handling Cost($)',default='0.00', size=20)
    pack_type = fields.Selection([('Letter', 'Letter'),
                                  ('LargeEnvelope', 'Large Envelope'),
                                  ('PackageThickEnvelope', 'Package(or thick package)'),
                                  ('LargePackage', 'Large Package')],default='Letter',string='Package Type')
    irreg_pack = fields.Boolean('Domestic Irregular Package')
    min_weight = fields.Char('WeightMinor', size=5)
    max_weight = fields.Char('WeightMajor', size=5)
    
    inter_handling_cost = fields.Char(string='International Handling Cost($)',default='0.00', size=20)
    inter_pack_type = fields.Selection([('Letter', 'Letter'),
                                        ('LargeEnvelope', 'Large Envelope'),
                                        ('PackageThickEnvelope', 'Package(or thick package)'),
                                        ('LargePackage', 'Large Package'),
                                        ('PaddedBags','Padded Bags'),
                                        ('ToughBags','Tough Bags'),
                                        ('ExpandableToughBags','Expandable Tough Bags'),
                                        ('MailingBoxes','Mailing Boxes'),
                                        ('Winepak','Winepak')],default=False,string='International Package Type',help="The nature of the package used to ship the item(s).")
    inter_irreg_pack = fields.Boolean('Irregular Package')
    inter_min_weight = fields.Char('WeightMinor (oz)',size=5,help="WeightMinor are used to specify the weight of a shipping package. i.e Here is how you would represent a package weight of 2 oz:\n <WeightMinor unit='oz'>2</WeightMinor>")
    inter_max_weight = fields.Char('WeightMajor (lbs)',size=5,help="WeightMajor are used to specify the weight of a shipping package. i.e Here is how you would represent a package weight of 5 lbs:\n <WeightMajor unit='lbs'>5</WeightMajor>")    
    
    additional_locations=fields.Selection([('unitedstates', 'Will ship to United States and the Following'),('Worldwide', 'Will ship worldwide')],string='Additional ship to locations')
    exclude_ship_location_ids=fields.Many2many('ebay.exclude.shipping.locations','ebay_exclude_loc_rel','tmpl_id','ex_loc_id',string="Exclude Shipping Locations")    
    loc_ids=fields.Many2many('ebay.shipping.locations', 'shp_temp_rel_add','locad_nm_add','locad_id_add',string='Additional shipping locations')                     

    site_id=fields.Many2one("ebay.site.details","Site",readonly=True)
    
    #Listing Configuration fields
    listing_type = fields.Selection([('Chinese','Auction'),('FixedPriceItem','Fixed Price'),('LeadGeneration','Classified Ad')],'Type',default='Chinese',required=True,help="Type in which Products to be listed")
    duration_id = fields.Many2one('duration.time','Duration',help="Duration Of the Product on eBay")
    start_price_id = fields.Many2one('product.pricelist','Start Price',required=False,help="Selected Pricelist will be applied to the Listing Products")
    reserve_price_id = fields.Many2one('product.pricelist','Reserve Price',required=False,help="Selected Pricelist will be applied to the Listing Products")
    buy_it_nw_price_id = fields.Many2one('product.pricelist','Buy It Now Price',required=False,help="Selected Pricelist will be applied to the Listing Products")
    
    #eBay Seller Policy
    ebay_seller_payment_policy_id = fields.Many2one('ebay.site.policy.ept',string="Seller Payment Policy")
    ebay_seller_return_policy_id = fields.Many2one('ebay.site.policy.ept',string="Seller Return Policy")
    ebay_seller_shipping_policy_id = fields.Many2one('ebay.site.policy.ept',string="Seller Shipping Policy")
    
    #vat details
    business_seller = fields.Boolean("Business Seller",default=True)
    restricted_to_business = fields.Boolean("Restricted To Business",default=False)
    state_id = fields.Many2one('res.country.state','Sales Tax State')
    shipping_included_in_tax = fields.Boolean("Apply To Shipping And Handling Costs")
    
    related_dynamic_desc = fields.Boolean("Related", related="instance_id.use_dynamic_desc", store=False)
    desc_template_id = fields.Many2one("ebay.description.template", string="Description Template", help="Set Custom Description Template")

class shipping_service_ept(models.Model):
    _name = "shipping.service.ept"
    _description = "eBay Shipping Service"
    
    @api.onchange("is_free_shipping")
    def onchange_shipping(self):
        if self.is_free_shipping:
            self.cost=0.0
            self.additional_cost=0.0    

    @api.one
    @api.depends('domestic_template_id.ship_type','inter_template_id.int_ship_type')
    def _get_ship_type(self):
        self.ship_type = self.domestic_template_id.ship_type
        self.int_ship_type = self.inter_template_id.int_ship_type
            
    service_id = fields.Many2one('ebay.shipping.service',string='Shipping service',required=True)
    cost = fields.Char('Cost($)', size=20)
    additional_cost = fields.Char('Each Additional($)', size=20)
    is_free_shipping = fields.Boolean('Free Shipping')
    domestic_template_id = fields.Many2one('ebay.template.ept',string='Domestic Template')
    inter_template_id = fields.Many2one('ebay.template.ept',string='International Template')
    custom_loc=fields.Selection([('Worldwide', 'Worldwide'),('customloc', 'Choose Custom Location'),('Canada', 'Canada')],string='Ship to')
    loc_ids=fields.Many2many('ebay.shipping.locations', 'shp_temp_rel','locad_nm','locad_id', string='Additional shipping locations')
    ship_type = fields.Char(compute="_get_ship_type",store=True, string='Shipping Type')
    int_ship_type = fields.Char(compute="_get_ship_type",store=True, string='International Shipping Type')
    priority=fields.Integer("ShippingServicePriority",default=1,required=True)
  
