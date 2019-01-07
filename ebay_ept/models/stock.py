#!/usr/bin/python3
from odoo import models,fields,api,_

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    canceled_in_ebay = fields.Boolean("Cancelled in eBay",default=False)

    def _get_new_picking_values(self):
        """We need this method to set eBay Instance in Stock Picking"""
        res = super(stock_move,self)._get_new_picking_values()
        if self.sale_line_id and self.sale_line_id.order_id and self.sale_line_id.order_id.ebay_instance_id :
            sale_order = self.sale_line_id.order_id
            if sale_order.ebay_instance_id:
                res.update({'ebay_instance_id': sale_order.ebay_instance_id.id,'is_ebay_delivery_order':True,
                            'global_channel_id':sale_order.ebay_instance_id.global_channel_id and sale_order.ebay_instance_id.global_channel_id.id or False})
        return res
    
class stock_picking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    @api.depends("move_lines.canceled_in_ebay")
    def _get_ebay_cancel_status(self):
        for picking in self:
            if picking.ebay_instance_id:
                if not picking.partially_canceled_in_ebay:
                    picking.partially_canceled_in_ebay = any(move.state == 'cancel' and move.canceled_in_ebay == True for move in picking.move_lines)
                if picking.partially_canceled_in_ebay:
                    picking.partially_canceled_in_ebay = not all(move.state == 'cancel' and move.canceled_in_ebay == True for move in picking.move_lines)
                    if not picking.partially_canceled_in_ebay:
                        picking.canceled_in_ebay = True
    
    shipping_id = fields.Many2one('ebay.shipping.service',string="Shipping",default=False,copy=False)
    ebay_instance_id=fields.Many2one("ebay.instance.ept",string="eBay Instance",default=False,copy=False)
    is_ebay_delivery_order=fields.Boolean("eBay Delivery Order",default=False,copy=False)
    updated_in_ebay=fields.Boolean("Updated In eBay",default=False,copy=False)    
    canceled_in_ebay = fields.Boolean("Cancelled in eBay ?",compute='_get_ebay_cancel_status',store=True)
    partially_canceled_in_ebay = fields.Boolean("Partially Cancelled in eBay ?",compute='_get_ebay_cancel_status',store=True)

    @api.multi
    def cancel_in_ebay(self):
        view=self.env.ref('ebay_ept.view_ebay_cancel_order_wizard')
        return {
            'name': _('Cancel Order In eBay'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebay.cancel.order.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': self._context
        }

    @api.multi
    def mark_sent_ebay(self):
        for picking in self:
            picking.write({'updated_in_ebay':False})
        return True
   
    @api.multi
    def mark_not_sent_ebay(self):
        for picking in self:
            picking.write({'updated_in_ebay':True})
        return True            


class stock_quant_package(models.Model):
    _inherit='stock.quant.package'
    
    tracking_no=fields.Char("Additional Reference",help="This Field Is Used For The Store Tracking No")
    
    
    