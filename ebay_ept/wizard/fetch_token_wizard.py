#!/usr/bin/python3

from odoo import models,fields,api

class fetch_token_from_ebay(models.TransientModel):
    _name = 'fetch.ebay.token'
    _description = "eBay Fetch Token"
    
    instance_id = fields.Many2one('ebay.instance.ept',string='Instance ID')
    session_id = fields.Char(string='SessionID')
    
    @api.multi
    def get_sessionid_from_ebay(self):
        "This Method is created for geting SessionID by calling <GetSessionID> API By passing RuName"
        "This Method will execute when click on link in wizard"
        "And Redirecting User to eBay Site for verification in new Tab " 
        getsession_dict = {'RuName':self.instance_id.redirect_url_name}
        try:
            if self.instance_id.environment == 'is_sandbox' :
                api = self.instance_id.with_context({'do_not_use_site_id':True}).get_trading_api_object()
            else:
                api = self.instance_id.get_trading_api_object()
            api.execute('GetSessionID',getsession_dict) 
            getsession_results = api.response.dict() 
            sessionID_temp =  getsession_results['SessionID']
            self.session_id = sessionID_temp
            if self.instance_id.environment == 'is_sandbox' :
                base_URL = 'https://signin.sandbox.ebay.com/ws/eBayISAPI.dll?SignIn&RUName='+self.instance_id.redirect_url_name+'&SessID='
            else:
                base_URL = 'https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&RUName='+self.instance_id.redirect_url_name+'&SessID='
            base_URL += sessionID_temp
        except Exception as e:
                raise Warning(e)
        return { 'type': 'ir.actions.act_url', 
                 'url': base_URL,   
                 'nodestroy': True,
                 'target': 'new' 
                 }
        
    def fetch_token_from_ebay(self):
        "This Method is created for Fetching Token from eBay by calling <FetchToken> Api By passing SessionID only "
        "This Method requires user to complete sign-in in eBay site first "
        "This Method will execute when user click on <Continue> button on wizard "
        "Method will store token to database"
        try:
            if self.instance_id.environment == 'is_sandbox' :
                api = self.instance_id.with_context({'do_not_use_site_id':True}).get_trading_api_object()
            else:
                api = self.instance_id.get_trading_api_object()
            sessionID_dict = {'SessionID':self.session_id}
            api.execute('FetchToken',sessionID_dict) 
            fetchtoken_results = api.response.dict()
            token = fetchtoken_results['eBayAuthToken']
            results = self.env['ebay.instance.ept'].search([('id','=',self.instance_id.id)])
            results.write({
                            'auth_token':token,
                            'fetch_token_boolean':False
                         })
        except Exception as e:
                raise Warning(e)
        return True