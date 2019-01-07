#!/usr/bin/python3

from odoo import models,fields,api
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading
from odoo.addons.ebay_ept.ebaysdk.shopping import Connection as shopping
import time
from datetime import datetime
from odoo.exceptions import  Warning

class fetch_revoked_token_from_ebay(models.TransientModel):
    _name="ebay.instance.fetch.revoked.token"
    _description = "eBay Instance Fetch Revoked Token"
    
    session_id = fields.Char(string='SessionID')
    
    @api.multi
    def fetch_revoked_token(self):
        ebay_instance_obj = self.env['ebay.instance.ept']
        instance_ids = self._context.get('active_ids')
        for current in ebay_instance_obj.browse(instance_ids):
            if not current.redirect_url_name:
                raise Warning('Please enter the Username, Password and RuName in eBay credentials')
            else:
                raise Warning('Token Saved') 
        return True
    
    @api.multi
    def get_sessionid_for_revoked_fetch_token(self):
        ebay_instance_obj = self.env['ebay.instance.ept']
        instance_ids = self._context.get('active_ids')
        for instance in ebay_instance_obj.browse(instance_ids):  
            getsession_dict = {'RuName':instance.redirect_url_name}
            try:
                if instance.environment == 'is_sandbox' :
                    api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
                else:
                    api = instance.get_trading_api_object()
                api.execute('GetSessionID',getsession_dict)
                getsession_results = api.response.dict()
                sessionID_temp =  getsession_results['SessionID']
                self.session_id = sessionID_temp
             
                if instance.environment == 'is_sandbox' :
                    base_URL = 'https://signin.sandbox.ebay.com/ws/eBayISAPI.dll?SignIn&RUName='+instance.redirect_url_name+'&SessID='
                else:
                    base_URL = 'https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&RUName='+instance.redirect_url_name+'&SessID='             
                base_URL += sessionID_temp
                return{'type': 'ir.actions.act_url',
                       'url': base_URL,
                       'nodestroy': True,
                       'target': 'new'
                }               
            except Exception as e:
                raise Warning(e)
            
    @api.multi
    def fetch_revoked_token_from_ebay(self):
        "This Method is created for Fetching Token from eBay by calling <FetchToken> Api By passing SessionID only "
        "This Method requires user to complete sign-in in eBay site first "
        "This Method will execute when user click on <Continue> button on wizard "
        "Method will store token to database"
        ebay_instance_obj = self.env['ebay.instance.ept']
        instance_ids = self._context.get('active_ids')
        for instance in ebay_instance_obj.browse(instance_ids):
            try:
                if instance.environment == 'is_sandbox' :
                    api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
                else:
                    api = instance.get_trading_api_object()

                sessionID_dict = {'SessionID':self.session_id}
                api.execute('FetchToken',sessionID_dict)      
                fetchtoken_results = api.response.dict()
                token = fetchtoken_results['eBayAuthToken']
                results = instance.env['ebay.instance.ept'].search([('id','=',instance.id)])
                results.write({
                            'auth_token':token,
                            'fetch_token_boolean':False
                         })
            except Exception as e:
                raise Warning(e)
        return True