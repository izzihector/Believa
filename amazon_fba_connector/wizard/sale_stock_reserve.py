# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta

class SaleStockReserve(models.TransientModel):
    _inherit = 'sale.stock.reserve'
    
    @api.model
    def default_get(self, fields):
        env = self.env
        res = super(SaleStockReserve, self).default_get(fields)
        if not fields:
            return res
        context = env.context
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        if not (active_model and active_ids):
            return res
        lines = False
        if active_model == 'sale.order':
            sales = env['sale.order'].browse(active_ids)
            for sale in sales:
                if not lines:
                    lines = sale.ept_order_line
                else:
                    lines = lines + sale.ept_order_line    
        
        if active_model == 'sale.order.line':
            lines = env['sale.order.line'].browse(active_ids)
        if not lines:
            return res
        default_value = []
        for line in lines:
            if not line.is_stock_reservable:
                continue
            warehouse = line.warehouse_id or line.order_id.warehouse_id
            location_id = warehouse.lot_stock_id.id or self.env['stock.reservation']._default_location_id()
            location_dest_id = warehouse.reservation_stock_id and warehouse.reservation_stock_id.id or self.env['stock.reservation']._default_location_dest_id()  
            date_validity = False
            if warehouse.validity_days:
                if line.order_id.date_order:
                    date_validity = datetime.strptime(line.order_id.date_order,'%Y-%m-%d %H:%M:%S') + timedelta(days=warehouse.validity_days)
                    date_validity = datetime.strftime(date_validity,"%Y-%m-%d") 
            default_value.append({
                                  'product_id': line.product_id.id,
                                  'quantity': line.product_uom_qty,
                                  'date_validity': date_validity,
                                  'location_id': location_id,
                                  'location_dest_id': location_dest_id,
                                  'sale_line_id' :line.sale_order_line_id.id,
                                  })  
        if default_value:
            res.update({'reserve_lines' : default_value})              
        return res
    