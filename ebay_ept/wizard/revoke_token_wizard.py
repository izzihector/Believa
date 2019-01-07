#!/usr/bin/python3

from odoo import models,fields,api
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading
from odoo.addons.ebay_ept.ebaysdk.shopping import Connection as shopping
import time
from datetime import datetime
from odoo.exceptions import  Warning

class revoke_token_action(models.TransientModel):
    _name="ebay.instance.revoke.token"
    _description = "eBay Instance Revoke Token"

    @api.multi
    def revoke_token_from_ebay(self):
        ebay_instance_obj = self.env['ebay.instance.ept']
        instance_ids = self._context.get('active_ids')
        for instance in ebay_instance_obj.browse(instance_ids) :
            if not instance.auth_token :
                raise Warning("Instance %s doesn's have Token."%instance.name)
            revoke_token_dict=  {'RequesterCredentials':{'eBayAuthToken': instance.auth_token}}       
            try:
                if instance.environment == 'is_sandbox' :
                    api = instance.with_context({'do_not_use_site_id':True}).get_trading_api_object()
                else:
                    api = instance.get_trading_api_object()
                api.execute('RevokeToken',revoke_token_dict)
                instance.write({'auth_token':False})
            except Exception as e:
                raise Warning(e)
        return True