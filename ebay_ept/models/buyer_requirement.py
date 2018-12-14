#!/usr/bin/python3

from odoo import models,fields,api

class ebay_policy(models.Model):
    _name = 'ebay.site.policy.ept'
    _description = "eBay Site Policy"

    name = fields.Char('Name',readonly=True)
    policy_id = fields.Char('Policy ID',readonly=True)
    policy_type = fields.Char('Type',readonly=True)
    short_summary = fields.Text('Summary',readonly=True)
    instance_id=fields.Many2one('ebay.instance.ept',string="Instance",readonly=True)
    
    @api.model
    def sync_policies(self,instance):
        api=instance.get_trading_api_object() 
        para ={'ShowSellerProfilePreferences':True,'ShowSellerReturnPreferences':True,'ShowOutOfStockControlPreference':True}
        api.execute('GetUserPreferences',para)
        result = api.response.dict()
        SellerProfilePreferences = result.get('SellerProfilePreferences',{})
        SupportedSellerProfiles = SellerProfilePreferences.get('SupportedSellerProfiles',{})
        policies = []
        if SupportedSellerProfiles :
            policies = SupportedSellerProfiles.get('SupportedSellerProfile',[])
        if not isinstance(policies, list):
            policies = [policies]
        OutOfStockControlPreference = result.get('OutOfStockControlPreference')
        if OutOfStockControlPreference == 'false':
            instance.write({'allow_out_of_stock_product':False})
        else :
            instance.write({'allow_out_of_stock_product':True})
        policy_ids = list(map(lambda p: p['ProfileID'], policies))
        existing_policies=self.search([('policy_id', 'not in', policy_ids),('instance_id','=',instance.id)])
        existing_policies.unlink()
        for policy in policies:
            record = self.search([('policy_id', '=', policy['ProfileID'])])
            if not record:
                record = self.create({
                    'policy_id': policy['ProfileID'],
                })
            record.write({
                'name': policy['ProfileName'],
                'policy_type': policy['ProfileType'],
                'short_summary': policy['ShortSummary'] if 'ShortSummary' in policy else ' ',
                'instance_id':instance.id
            })
        return True

class feedback_score_ept(models.Model):
    _name="ebay.feedback.score"
    _description = "eBay Feedback Score"
    
    name=fields.Char("Feedbackscore",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_feed_back_score_rel','feedback_id','site_id',required=True)

    def create_buyer_requirement(self,instance,details):
        feedback_score=details.get('MinimumFeedbackScore',{}).get('FeedbackScore',[])
        site_id=instance.site_id.id
        for value in feedback_score:
            exist_score=self.search([('name','=',value),('site_ids','in',[site_id])])
            if not exist_score:
                exist_score=self.search([('name','=',value)])
                if not exist_score:
                    self.create({'name':value,'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_score.site_ids.ids+[site_id]))
                    exist_score.write({'site_ids':[(6,0,site_ids)]})
        item_feed_score_obj=self.env['item.feedback.score']
        item_feed_score=details.get('MaximumItemRequirements',{}).get('MinimumFeedbackScore',[])
        for value in item_feed_score:
            exist_score=item_feed_score_obj.search([('name','=',value),('site_ids','in',[site_id])])
            if not exist_score:
                exist_score=item_feed_score_obj.search([('name','=',value)])
                if not exist_score:
                    item_feed_score_obj.create({'name':value,'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_score.site_ids.ids+[site_id]))
                    exist_score.write({'site_ids':[(6,0,site_ids)]})

        max_item_count_obj=self.env['ebay.max.item.counts']
        max_item_count=details.get('MaximumItemRequirements',{}).get('MaximumItemCount',[])
        for value in max_item_count:
            exist_record=max_item_count_obj.search([('name','=',value),('site_ids','in',[site_id])])
            if not exist_record:
                exist_record=max_item_count_obj.search([('name','=',value)])
                if not exist_record:
                    max_item_count_obj.create({'name':value,'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_record.site_ids.ids+[site_id]))
                    exist_record.write({'site_ids':[(6,0,site_ids)]})
        
        unpaid_strike_obj=self.env['ebay.unpaid.item.strike.count']
        unpaid_strike_count=details.get('MaximumUnpaidItemStrikesInfo',{}).get('MaximumUnpaidItemStrikesCount',{}).get('Count','[]')
        for value in unpaid_strike_count:
            exist_record=unpaid_strike_obj.search([('name','=',value),('site_ids','in',[site_id])])
            if not exist_record:
                exist_record=unpaid_strike_obj.search([('name','=',value)])
                if not exist_record:
                    unpaid_strike_obj.create({'name':value,'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_record.site_ids.ids+[site_id]))
                    exist_record.write({'site_ids':[(6,0,site_ids)]})
        unpaid_strike_duration_obj=self.env['ebay.unpaid.item.strike.duration']
        unpaid_strike_duration=details.get('MaximumUnpaidItemStrikesInfo',{}).get('MaximumUnpaidItemStrikesDuration',[])
        for record in unpaid_strike_duration:
            exist_record=unpaid_strike_duration_obj.search([('name','=',record.get('Period')),('description','=',record.get('Description')),('site_ids','in',[site_id])])
            if not exist_record:
                exist_record=unpaid_strike_duration_obj.search([('name','=',record.get('Period'))])
                if not exist_record:
                    unpaid_strike_duration_obj.create({'name':record.get('Period'),'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_record.site_ids.ids+[site_id]))
                    exist_record.write({'site_ids':[(6,0,site_ids)]})
        policy_violations_duration_obj=self.env['ebay.policy.violations.durations']
        policy_violations_duration=details.get('MaximumBuyerPolicyViolations',{}).get('PolicyViolationDuration',[])
        for record in policy_violations_duration:
            exist_record=policy_violations_duration_obj.search([('name','=',record.get('Period')),('description','=',record.get('Description')),('site_ids','in',[site_id])])
            if not exist_record:
                exist_record=policy_violations_duration_obj.search([('name','=',record.get('Period'))])
                if not exist_record:
                    policy_violations_duration_obj.create({'name':record.get('Period'),'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_record.site_ids.ids+[site_id]))
                    exist_record.write({'site_ids':[(6,0,site_ids)]})
        policy_violations_obj=self.env['ebay.policy.violations']
        policy_violations=details.get('MaximumBuyerPolicyViolations',{}).get('NumberOfPolicyViolations',{}).get('Count',[])
        for value in policy_violations:
            exist_record=policy_violations_obj.search([('name','=',value),('site_ids','in',[site_id])])
            if not exist_record:
                exist_record=policy_violations_obj.search([('name','=',value)])
                if not exist_record:
                    policy_violations_obj.create({'name':value,'site_ids':[(6,0,[site_id])]})
                else:
                    site_ids=list(set(exist_record.site_ids.ids+[site_id]))
                    exist_record.write({'site_ids':[(6,0,site_ids)]})

class max_item_counts(models.Model):
    _name="ebay.max.item.counts"
    _description = "eBay Max Item Count"
    
    name=fields.Char("MaximumItemCount",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_max_item_counts_rel','feedback_id','site_id',required=True)

class min_feedback_score(models.Model):
    _name="item.feedback.score"
    _description = "Item Feedback Score"
    
    name=fields.Char("MinimumFeedbackScore",help="This is under item strikes")
    site_ids=fields.Many2many("ebay.site.details",'ebay_item_feed_score_rel','feedback_id','site_id',required=True)
    
    
class policy_violations(models.Model):
    _name="ebay.policy.violations"
    _description = "eBay Policy Violations"
    
    name=fields.Char("NumberOfPolicyViolations",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_policy_violation_rel','feedback_id','site_id',required=True)

class policy_violations_durations(models.Model):
    _name="ebay.policy.violations.durations"
    _description = "eBay Policy Violations Durations"
    
    name=fields.Char("PolicyViolationDuration",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_policy_vio_dur_rel','feedback_id','site_id',required=True)
    description=fields.Char("Description")
    
class unpaid_item_strike(models.Model):
    _name="ebay.unpaid.item.strike.count"
    _description = "eBay Unpaid Item Strike Count"

    name=fields.Char("Period",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_unpaid_strike_rel','feedback_id','site_id',required=True)

class unpaid_item_duration(models.Model):
    _name="ebay.unpaid.item.strike.duration"
    _description = "eBay Unpaid Item Strike Duration"

    name=fields.Char("MaximumUnpaidItemStrikesDuration",required=True)
    site_ids=fields.Many2many("ebay.site.details",'ebay_unpaid_st_dur_rel','feedback_id','site_id',required=True)
    description=fields.Char("Description")
    