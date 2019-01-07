#!/usr/bin/python3

from odoo import models, fields, api
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading

class ebay_credential(models.TransientModel):
    _name = "ebay.credential"
    _description = "eBay Credential"
    
    site_id = fields.Many2one('ebay.site.details','Site')
    dev_id = fields.Char('Dev ID',size=256,required=True,help="eBay Dev ID")
    app_id = fields.Char('App ID (Client ID)',size=256,required=True,help="eBay App ID")
    cert_id = fields.Char('Cert ID (Client Secret)',size=256,required=True,help="eBay Cert ID")
    server_url = fields.Char('Server URL',size=256,help="eBay Server URL")
    environment = fields.Selection([('is_sandbox', 'Sandbox'),('is_production', 'Production')],'Environment',required=True)
    auth_token = fields.Text('Token',help="eBay Token")
    redirect_url_name = fields.Char('eBay Redirect URL Name',size=256,help="eBay Redirect URL Name")
    username = fields.Char('eBay Username',size=256,help="eBay Username")
    password = fields.Char('eBay Password',size=256,help="eBay Password")
    
    @api.model
    def default_get(self,fields):
        obj_instance_ept = self.env['ebay.instance.ept']
        instance_record = obj_instance_ept.browse(self.env.context.get('active_id'))
        res = super(ebay_credential, self).default_get(fields)
        res.update({
                        'site_id' : instance_record.site_id.id,
                        'dev_id' : instance_record.dev_id,
                        'app_id' : instance_record.app_id,
                        'cert_id' : instance_record.cert_id,
                        'server_url' : instance_record.server_url,
                        'environment' : instance_record.environment,
                        'auth_token' : instance_record.auth_token,
                        'redirect_url_name' : instance_record.redirect_url_name,
                        'username' : instance_record.username,
                        'password' : instance_record.password
                        })
        return res
    
    @api.one
    def update_changes(self):
        obj_instance_ept = self.env['ebay.instance.ept']
        instance_record = obj_instance_ept.browse(self.env.context.get('active_id'))
        instance_record.write({
                        'site_id' : self.site_id.id,
                        'dev_id' : self.dev_id,
                        'app_id' : self.app_id,
                        'cert_id' : self.cert_id,
                        'server_url' : self.server_url,
                        'environment' : self.environment,
                        'auth_token' : self.auth_token,
                        'redirect_url_name' : self.redirect_url_name,
                        'username' : self.username,
                        'password' : self.password
                        })
        return True
    
    @api.onchange('environment')
    def onchange_environment(self):
        if self.environment == 'is_sandbox':
            self.server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            self.server_url = 'https://api.ebay.com/ws/api.dll'