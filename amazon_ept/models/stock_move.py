from odoo import models,fields,api
from ..amazon_emipro_api.mws import Feeds
from odoo.exceptions import Warning

class stock_move(models.Model):    
    _name = "stock.move"
    _inherit = "stock.move"
    _description = "Stock Move"
    
    updated_in_amazon=fields.Boolean("Update Status in Amazon",default=False,help="Use only for phantom products")
    
    #added by Dhruvi
    seller_id = fields.Many2one("amazon.seller.ept","Seller")
    
    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        res= super(stock_move,self)._create_account_move_line(credit_account_id, debit_account_id, journal_id)
        for move in self.account_move_ids:
            if not move.seller_id:
                move.seller_id=self.picking_id.seller_id and self.picking_id.seller_id.id or False
            if not move.amazon_instance_id:
                move.amazon_instance_id=self.picking_id.amazon_instance_id and self.picking_id.amazon_instance_id.id or False
                
        return res
    
    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        res = super(stock_move,self)._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
        for row in res:
            row[2].update({'seller_id':self.picking_id.seller_id and self.picking_id.seller_id.id or False,
                        'amazon_instance_id':self.picking_id.amazon_instance_id and self.picking_id.amazon_instance_id.id or False})
        return res
    
    @api.multi
    def write(self, vals):
        res = super(stock_move,self).write(vals)
        if vals.get('state',False) and vals.get('state','')=='done':
            product_instance_dict = {}
            location_obj = self.env['stock.location']
            amazon_product_obj = self.env['amazon.product.ept']
            for instance in self.env['amazon.instance.ept'].search([('update_stock_on_fly','=',True)]):
                for move in self:
                    if move.state != 'done' or not move.product_id:
                        continue
                    amazon_location_id = instance.warehouse_id.lot_stock_id.id or False
                    amazon_location_ids = location_obj.search([('child_ids','child_of',[amazon_location_id])])
                    if move.location_id.id in amazon_location_ids.ids or move.location_dest_id.id in amazon_location_ids.ids :
                        ctx=self.env.context.copy()
                        ctx.update({'location': amazon_location_id})
                        product_obj = move.product_id.with_context(ctx)
                        amazon_product = amazon_product_obj.search([('product_id','=',product_obj.id),('exported_to_amazon','=',True),('instance_id','=',instance.id),('fulfillment_by','=','MFN')])
                        if not amazon_product:
                            continue
                        if hasattr(product_obj, instance.stock_field.name):
                            product_qty_available = getattr(product_obj, instance.stock_field.name)
                        else:
                            product_qty_available = product_obj.qty_available    
                        sku = amazon_product.seller_sku or product_obj.default_code
                        if instance in product_instance_dict:
                            product_instance_dict[instance].update({sku:product_qty_available})
                        else:
                            product_instance_dict.update({instance : {sku:product_qty_available}})
            if product_instance_dict:
                self.export_stock_to_amazon(product_instance_dict)
        return res
    @api.multi
    def export_stock_to_amazon(self,product_instance_dict):
        for instance in product_instance_dict:
            message_information = ''
            message_id = 1
            merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance.merchant_id)            
            for sku,qty in product_instance_dict[instance].items():
                message_information += """<Message><MessageID>%s</MessageID><OperationType>Update</OperationType><Inventory><SKU>%s</SKU><Quantity>%d</Quantity></Inventory></Message>""" % (message_id,sku,int(qty))
                message_id = message_id + 1
            if message_information:
                data = """<?xml version="1.0" encoding="utf-8"?><AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"><Header><DocumentVersion>1.01</DocumentVersion>"""+ merchant_string +"""</Header><MessageType>Inventory</MessageType>""" + message_information + """</AmazonEnvelope>"""
                proxy_data=instance.seller_id.get_proxy_server()
                mws_obj=Feeds(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code,proxies=proxy_data)        
                try:
                    mws_obj.submit_feed(data.encode('utf-8'),'_POST_INVENTORY_AVAILABILITY_DATA_',marketplaceids=[instance.market_place_id],instance_id=instance.id)
                except Exception as e:
                    raise Warning(str(e))                
        return True    
    
    
    def _get_new_picking_values(self):
        """We need this method to set Amazon Instance in Stock Picking"""
        res = super(stock_move,self)._get_new_picking_values()
        order_id=self.sale_line_id.order_id
        if order_id.amazon_reference!=False:
            order_id and res.update({'amazon_instance_id': order_id.amz_instance_id.id,
                                     'is_amazon_delivery_order':True,
                                     'seller_id':order_id.seller_id.id,
                                     #'global_channel_id':order_id.global_channel_id.id                                     
                                     })
        return res    
