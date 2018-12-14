from odoo import models,fields,api
from odoo.tools.float_utils import float_round, float_compare, float_is_zero

class stock_move(models.Model):
    _inherit="stock.move"

    def _get_new_picking_values(self):
        """We need this method to set Amazon Instance in Stock Picking"""
        res = super(stock_move,self)._get_new_picking_values()
        if self.sale_line_id and self.sale_line_id.order_id:
            sale_order = self.sale_line_id.order_id
            if sale_order.amazon_reference!=False:
                res.update({'fulfillment_by':sale_order.amz_fulfillment_by})
        return res    

class stock_move_line(models.Model):
    _inherit='stock.move.line'
    
    def _free_reservation_ept(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, ml_to_ignore=None):

        """ When editing a done move line or validating one with some forced quantities, it is
        possible to impact quants that were not reserved. It is therefore necessary to edit or
        unlink the move lines that reserved a quantity now unavailable.
        """
        self.ensure_one()

        if ml_to_ignore is None:
            ml_to_ignore = self.env['stock.move.line']
        ml_to_ignore |= self

        # Check the available quantity, with the `strict` kw set to `True`. If the available
        # quantity is greather than the quantity now unavailable, there is nothing to do.
        available_quantity = self.env['stock.quant']._get_available_quantity(
            product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True
        )
        if quantity > available_quantity:
            # We now have to find the move lines that reserved our now unavailable quantity. We
            # take care to exclude ourselves and the move lines were work had already been done.
            oudated_move_lines_domain = [
                ('move_id.state', 'not in', ['done', 'cancel']),
                ('product_id', '=', product_id.id),
                ('lot_id', '=', lot_id.id if lot_id else False),
                ('location_id', '=', location_id.id),
                ('owner_id', '=', owner_id.id if owner_id else False),
                ('package_id', '=', package_id.id if package_id else False),
                ('product_qty', '>', 0.0),
                ('id', 'not in',self.move_id.move_line_ids.ids),
            ]
            oudated_candidates = self.env['stock.move.line'].search(oudated_move_lines_domain)

            # As the move's state is not computed over the move lines, we'll have to manually
            # recompute the moves which we adapted their lines.
            move_to_recompute_state = self.env['stock.move']

            rounding = self.product_uom_id.rounding
            for candidate in oudated_candidates:
                if float_compare(candidate.product_qty, quantity, precision_rounding=rounding) <= 0:
                    quantity -= candidate.product_qty
                    move_to_recompute_state |= candidate.move_id
                    if candidate.qty_done:
                        candidate.product_uom_qty = 0.0
                    else:
                        candidate.unlink()
                else:
                    # split this move line and assign the new part to our extra move
                    quantity_split = float_round(
                        candidate.product_qty - quantity,
                        precision_rounding=self.product_uom_id.rounding,
                        rounding_method='UP')
                    candidate.product_uom_qty = self.product_id.uom_id._compute_quantity(quantity_split, self.product_uom_id, rounding_method='HALF-UP')
                    quantity -= quantity_split
                    move_to_recompute_state |= candidate.move_id
                if quantity <= 0.0:
                    break
            move_to_recompute_state._recompute_state()
    