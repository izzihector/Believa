from odoo import models, fields, api

class ebay_feedback_wizard(models.TransientModel):
    _name = "ebay.feedback.wizard"
    _description = "eBay Feedback Wizard"
    
    response_text=fields.Text("Comment",required=True)
    response_type=fields.Selection([('CustomCode','CustomCode'),('FollowUp','FollowUp'),('Reply','Reply')],string="Response Type",default="Reply",required=True,
                                help="CustomCode:-Reserved for future use.FollowUp:-This enumeration value is used in the ResponseType field of a RespondToFeedback call if the user is following up on a Feedback entry comment left by another user.Reply:-(in) This enumeration value is used in the ResponseType field of a RespondToFeedback call if the user is replying to a Feedback entry left by another user.") 

    @api.multi
    def update_changes(self):
        self.ensure_one()
        response_text=self.response_text
        response_type=self.response_type
        ebay_feedback_obj=self.env['ebay.feedback.ept']
        ebay_active_id=self._context.get('active_id',False)
        record=ebay_feedback_obj.search([('id','=',ebay_active_id)])
        return record.send_feedback_reply_ept(response_text,response_type)