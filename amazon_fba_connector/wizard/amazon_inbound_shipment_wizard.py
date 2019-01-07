from odoo import models,fields,api
from ..models.api import InboundShipments_Extend
from odoo.exceptions import Warning

class amazon_inbound_shipment_wizard(models.TransientModel):
    _name = "amazon.inbound.shipment.wizard"
    
    update_shipment_status = fields.Selection([('WORKING','WORKING'),('CANCELLED','CANCELLED')],string="Shipment Status",default='WORKING')
    choose_inbound_shipment_file = fields.Binary(string="Choose File",filters="*.csv",help="Select amazon inbound shipment file.")
    file_name = fields.Char("Filename",help="File Name")

    @api.multi
    def update_inbound_shipment(self):
        plan_line_obj=self.env['inbound.shipment.plan.line']
        active_id = self._context.get('active_id')
        stock_picking_obj = self.env['stock.picking']
        active_model = self._context.get('active_model','')
        if active_model != 'stock.picking':
            raise Warning('You cannot update Shipment, because there is no any related Amazon shipment with this record.')
        picking = stock_picking_obj.browse(active_id)

        odoo_shipment = picking.odoo_shipment_id
        ship_plan = picking.ship_plan_id
        instance = ship_plan.instance_id 
        address = picking.partner_id or ship_plan.ship_from_address_id        
        name, add1, add2, city, postcode = address.name, address.street or '',address.street2 or '',address.city or '', address.zip or ''
        country = address.country_id and address.country_id.code or ''
        state = address.state_id and address.state_id.code or ''
        shipment_status = self.update_shipment_status or 'WORKING'
        amazon_product_obj=self.env['amazon.product.ept']
        if not odoo_shipment.shipment_id or not odoo_shipment.fulfill_center_id:
            raise Warning('You must have to first create Inbound Shipment Plan.')
        mws_obj = InboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code)
        for x in range(0, len(picking.move_lines),20):
            move_lines = picking.move_lines[x:x +20]
            sku_qty_dict = {}        
            for move in move_lines:
                amazon_product = amazon_product_obj.search([('product_id','=',move.product_id.id),('instance_id','=',instance.id),('fulfillment_by','=','AFN')])
                if not amazon_product:
                    raise Warning("Amazon Product is not available for this %s product code"%(move.product_id.default_code))
                line=plan_line_obj.search([('odoo_shipment_id','=',odoo_shipment.id),('amazon_product_id','in',amazon_product.ids)])
                sku_qty_dict.update({str(line and line.seller_sku or amazon_product[0].seller_sku):str(int(move.reserved_availability))})            
            try:
                mws_obj.update_inbound_shipment(odoo_shipment.name,odoo_shipment.shipment_id,odoo_shipment.fulfill_center_id,
                                                           name,add1,add2,city,state,postcode,country,
                                                           labelpreppreference = odoo_shipment.label_prep_type,shipment_status=shipment_status,
                                                           inbound_box_content_status=odoo_shipment.intended_boxcontents_source,sku_qty_dict=sku_qty_dict)                
            except Exception as e:
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)
                raise Warning(error_value)
        
        picking.write({'inbound_ship_updated':True,'shipment_status':self.update_shipment_status})

        if self.update_shipment_status == 'CANCELLED':
            picking.action_cancel()
            odoo_shipment.write({'state':'CANCELLED'})
        return True
    
    @api.multi
    def import_inbound_shipment_report(self):
        return True
