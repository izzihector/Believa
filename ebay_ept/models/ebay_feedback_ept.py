#!/usr/bin/python3
from odoo import models,fields,api
from datetime import date, timedelta
from odoo.exceptions import Warning

class ebay_feedback(models.Model):
    _name="ebay.feedback.ept"
    _inherit = ['mail.thread'] 
    _rec_name='ebay_feedback_id'
    _description = "eBay Feedback"
    
    ebay_product_id=fields.Many2one('ebay.product.product.ept',string="eBay Product")
    sale_order_id=fields.Many2one('sale.order',string="Sale Order")
    listing_id=fields.Many2one('ebay.product.listing.ept',string="eBay Listing")
    feedback_user_id=fields.Char(string="Feedback User Id")
    comment_time=fields.Date("Comment Time",required=False,help="Display Date and Time of Comment")
    comment_type=fields.Selection([('Positive','Positive'),('Negative','Negative'),('Neutral','Neutral')],string="Comment Type",default="Neutral")
    commenting_user_score=fields.Char(string="Commenting User Score")
    comment_text=fields.Text("Comment")
    ebay_feedback_id=fields.Char(string="FeedBack Id",required=True)
    instance_id = fields.Many2one('ebay.instance.ept',string="Instance")
    sale_order_line_id=fields.Many2one('sale.order.line',string="sale order line")
    is_feedback=fields.Boolean(string="Is Feedback Given?")
 
    @api.multi
    def get_feedback(self,instances):
        ebay_product_listing_obj=self.env['ebay.product.listing.ept']
        for instance in instances:
            product_listings=ebay_product_listing_obj.search([('instance_id','=',instance.id)])
            for product_listing in product_listings:
                if product_listing.state=='Active':
                    self.create_ebay_feedback_ept(instance,product_listing)
                else:
                    date_n_days_ago = str(date.today() - timedelta(days=10))
                    enddate=str(product_listing.end_time.date())
                    if (enddate >= date_n_days_ago):
                        self.create_ebay_feedback_ept(instance,product_listing)
        return True
                
    @api.multi
    def create_ebay_feedback_ept(self,instance,product_listing):
        try:
            api = instance.get_trading_api_object()
            api.execute('GetFeedback',{'DetailLevel':'ReturnAll','ItemID':product_listing.name})
            results = api.response.dict()
            feedback_results = results.get('FeedbackDetailArray',{}).get('FeedbackDetail',{})
            if isinstance(feedback_results,dict) :
                feedback_results = [feedback_results]
            if any(feedback_results):
                self.create_or_update_feedback_ept(feedback_results, instance, product_listing)
        except Exception as e:
                raise Warning(str(e))
        return True
    
    @api.multi 
    def create_or_update_feedback_ept(self,feedback_results,instance,product_listing):
        sale_order_line_obj=self.env['sale.order.line']
        sale_obj=self.env['sale.order']
        ebay_product_obj=self.env['ebay.product.product.ept']
        ebay_feedback_obj=self.env['ebay.feedback.ept']
        for feedback_result in feedback_results :
            sale_order_lines=sale_order_line_obj.search([('ebay_order_line_item_id','=',feedback_result.get('OrderLineItemID',[]))])
            for sale_order_line in sale_order_lines:
                sale_order=sale_obj.search([('id','=',sale_order_line.order_id.id)])
                if ebay_feedback_obj.search([('sale_order_id','=',sale_order.id),('ebay_feedback_id','=',feedback_result.get('FeedbackID',False))]):
                    continue
                else:
                    ebay_product=ebay_product_obj.search([('product_id','=',sale_order_line.product_id.id),('instance_id','=',instance.id)])
                    vals={}
                    vals.update({'ebay_product_id':ebay_product.id,
                                 'sale_order_id':sale_order.id,
                                 'listing_id':product_listing.id,
                                 'feedback_user_id':feedback_result.get('CommentingUser',False),
                                 'comment_time':feedback_result.get('CommentTime',False),
                                 'comment_type':feedback_result.get('CommentType',False),
                                 'commenting_user_score':feedback_result.get('CommentingUserScore',False),
                                 'comment_text':feedback_result.get('CommentText',False),
                                 'ebay_feedback_id':feedback_result.get('FeedbackID',False),
                                 'instance_id':instance.id,
                                 'sale_order_line_id':sale_order_line.id,
                                 'is_feedback':True
                                 })
                self.create(vals)               
        return True
    
    @api.multi
    def get_feedback_replay(self):
        ebay_feedback_view = self.env.ref('ebay_ept.ebay_feedback_wizard_view',False)
        return ebay_feedback_view and {
           'name': 'eBay Feedback',
           'view_type': 'form',
           'view_mode': 'form',
           'res_model': 'ebay.feedback.wizard',
           'type': 'ir.actions.act_window',
           'view_id':ebay_feedback_view.id,
           'target':'new'
        } or True
        
    @api.multi
    def send_feedback_reply_ept(self,response_text,response_type):
        for record in self:
            instance = record.instance_id
            iteam_id=self.sale_order_line_id.item_id
            ebay_order_line_item_id=self.sale_order_line_id.ebay_order_line_item_id
            transection_id=ebay_order_line_item_id.split("-")[1]
            results ={}
            para = {'ItemID':iteam_id,'TransactionID':transection_id,'ResponseText':response_text,'ResponseType':response_type,'TargetUserID':self.feedback_user_id}    
            try:
                api = instance.get_trading_api_object()
                api.execute('RespondToFeedback',para)
                results = api.response.dict()
                ack=results.get('Ack')
                if ack=='Success':
                    record.message_post(body=('<b>The FeedBack Message sent</b><br/>%s.') % (response_text))
            except Exception as e:
                    raise Warning(str(e))