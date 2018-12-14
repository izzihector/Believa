#!/usr/bin/python3
from odoo import models, fields,api
from odoo.exceptions import Warning
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading

class ebay_promotion_ept(models.Model):
    _name = "ebay.promotion.ept"
    _rec_name = "promotion_name"
    _description = "eBay Promotion"
    
    promotion_name = fields.Char(string='Promotion Name', size=100)
    instance_id = fields.Many2one('ebay.instance.ept',string='Instance',required=True)
    discount_type = fields.Selection([('Percentage', 'Percentage'),('Price', 'Price')],default='Price',string='Discount Type',help="Type of a promotional sale discount for items (for example, percentage). Applies to price discount sales only.")
    discount_value = fields.Float(string='Discount Value')
    promotion_type = fields.Selection([('FreeShippingOnly', 'FreeShippingOnly'),
                                       ('PriceDiscountAndFreeShipping', 'PriceDiscountAndFreeShipping'),
                                       ('PriceDiscountOnly','PriceDiscountOnly')
                                       ],
                                      default='PriceDiscountOnly',string='Promotion Sale Type',
                                      help="Type of promotional sale: price discount, free shipping, or both.")
    promotion_start_date = fields.Datetime('Promotion Start Date',help="Start date of a promotional sale for items on eBay.")
    promotion_end_date = fields.Datetime('Promotion End Date',help="End date of a promotional sale discount for items on eBay.")
    promotion_sale_id =  fields.Integer(string='Promotion Sale ID', readonly=True)
    created_in_ebay = fields.Boolean('Created In eBay',default=False)
    status = fields.Selection([('Active', 'Active'),('Inactive', 'Inactive'),('Processing','Processing'),('Scheduled','Scheduled'),('Deleted','Deleted')],string='Status',readonly=True, help="Status of a promotional sale. .") 
    promotion_item_ids = fields.Many2many('ebay.product.listing.ept','rel_promotion_sale_listing','promo_sale_id','listing_id','Promotion Items') 
    
    @api.multi
    def create_update_delete_promotion_on_ebay(self):
        context = dict(self._context)
        instance = self.instance_id
        api = instance.get_trading_api_object()
        action= context.get('action',False)
        ebay_action = ''
        PromotionalSaleDetails = {}
        promotion_id = self.promotion_sale_id
        if action=='delete':
            PromotionalSaleDetails.update({'PromotionalSaleID':promotion_id})
            print 'delete'
            ebay_action = 'Delete'
            return True
        elif action == 'add':
            ebay_action = 'Add'
        elif action == 'update':
            PromotionalSaleDetails.update({'PromotionalSaleID':promotion_id})
            ebay_action = 'Update'
        if action in ['update','delete'] and not promotion_id:
            raise Warning("First you need to create Promotion, You cannot update / delete promotion without creating Promotion on eBay")
        
        if action != 'delete':
            PromotionalSaleDetails.update({'PromotionalSaleName' : self.promotion_name,
                                      'DiscountType':self.discount_type,
                                      'DiscountValue' : self.discount_value,
                                      'PromotionalSaleStartTime' : self.promotion_start_date,
                                      'PromotionalSaleEndTime' : self.promotion_end_date,
                                      'PromotionalSaleType' : self.promotion_type
                                      })        
        para = {'Action' : ebay_action,
                'PromotionalSaleDetails':PromotionalSaleDetails,
                'WarningLevel' : 'High'
                }
        try:
            api.execute('SetPromotionalSale',para)
            results = api.response.dict()
            if action != 'delete':
                promo_sale_id = results.get('PromotionalSaleID',False)
                status = results.get('Status',False)
                self.write({'status':status,'promotion_sale_id':promo_sale_id,'created_in_ebay':True})
        except Exception as e:
            raise Warning(str(e))
        return True
    
    @api.multi
    def add_delete_item_from_promotion(self):
        context = dict(self._context)
        
        #api = self.env['ebay.instance.ept'].get_trading_api_object(instance)
        action= context.get('action',False)
        ebay_action = ''
        if action=='delete':
            ebay_action = 'Delete'
            return True
        elif action == 'add':
            ebay_action = 'Add'

        if action == 'delete' and not self.promotion_sale_id:
            raise Warning("First you need to create Promotion, then you will add products in this Promotion")
                  
        listing_form = self.env.ref('ebay_ept.view_ebay_promotion_sale_listing_ept', False)
        ctx = dict(
            default_promotional_sale_id=self.id,
            action=ebay_action,
        )
        return {
            'name': _('Promotion Listing'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebay.promotion.listing',
            'views': [(listing_form.id, 'form')],
            'view_id': listing_form.id,
            'target': 'new',
            'context': ctx,
        }         