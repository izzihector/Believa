#!/usr/bin/python3

from odoo import models,fields,api
from odoo.exceptions import Warning

class ebay_cancel_order_wizard(models.TransientModel):
    _name="ebay.cancel.order.wizard"
    _description = "eBay Cancel Order Wizard"

    dispute_reason_code = fields.Selection([('BuyerHasNotPaid','BuyerHasNotPaid'),                                            
                                            ('TransactionMutuallyCanceled','TransactionMutuallyCanceled')],
                                           string="Dispute Reason",default='TransactionMutuallyCanceled')
    
    dispute_explanation_code_for_bhnp = fields.Selection([('BuyerHasNotResponded','BuyerHasNotResponded'),                                                 
                                                 ('BuyerNotClearedToPay','BuyerNotClearedToPay'),
                                                 ('BuyerRefusedToPay','BuyerRefusedToPay'),
                                                 ('ShippingAddressNotConfirmed','ShippingAddressNotConfirmed'),
                                                 ('OtherExplanation','OtherExplanation'),
                                                 ('BuyerNotPaid','BuyerNotPaid'),
                                                 ('BuyerPaymentNotReceivedOrCleared','BuyerPaymentNotReceivedOrCleared'),
                                                 ('BuyerPurchasingMistake','BuyerPurchasingMistake'),                                                 
                                                 ('BuyerReturnedItemForRefund','BuyerReturnedItemForRefund'),                                                                                                                                                                                                    
                                                 ('PaymentMethodNotSupported','PaymentMethodNotSupported'),                                                                                                 
                                                 ('ShipCountryNotSupported','ShipCountryNotSupported')],
                                                string="BHNP Dispute Explanation")

    dispute_explanation_code_for_tmc = fields.Selection([('BuyerNoLongerWantsItem','BuyerNoLongerWantsItem'),                                                 
                                                 ('BuyerPurchasingMistake','BuyerPurchasingMistake'),
                                                 ('ShippingAddressNotConfirmed','ShippingAddressNotConfirmed'),
                                                 ('BuyerReturnedItemForRefund','BuyerReturnedItemForRefund'),
                                                 ('UnableToResolveTerms','UnableToResolveTerms'),                                                                                                                                                                                           
                                                 ('PaymentMethodNotSupported','PaymentMethodNotSupported')],
                                                string="TMC sDispute Explanation")    
                    
    
    @api.multi
    def cancel_in_ebay(self):
        """
            Cancel Order In eBay using AddDispute API.
        """            
        active_id = self._context.get('picking_id')
        picking = self.env['stock.picking'].browse(active_id)
        instance = picking.ebay_instance_id
        
        if not instance.check_instance_confirmed_or_not():
            return False
        
        dispute_explanation_code = ''
        for move in picking.move_lines:                        
            sale_line_id = move.sale_line_id or False
            if not sale_line_id or move.canceled_in_ebay:
                continue
            if not sale_line_id.ebay_order_line_item_id or not sale_line_id.item_id:
                continue
            
            dispute_reason = self.dispute_reason_code
            if dispute_reason == 'BuyerHasNotPaid':
                dispute_explanation_code = self.dispute_explanation_code_for_bhnp
            else:
                dispute_explanation_code = self.dispute_explanation_code_for_tmc
            
            dispute_data = {
                'DisputeExplanation':dispute_explanation_code,
                'DisputeReason':dispute_reason,
                'OrderLineItemID':sale_line_id.ebay_order_line_item_id,
                'ItemID':sale_line_id.item_id,
                'TransactionID':sale_line_id.order_id.ebay_order_id
            }                                                                                 
            
            try:
                lang = instance.lang_id and instance.lang_id.code
                lang and dispute_data.update({'ErrorLanguage':lang})  
                api = instance.get_trading_api_object()
                api.execute('AddDispute',dispute_data)
                api.response.dict()
                move.write({'canceled_in_ebay':True})
                self._cr.commit()
            except Exception as e:
                raise Warning(e)                
        return True