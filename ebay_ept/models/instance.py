#!/usr/bin/python3

from odoo import models,fields,api
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading
from odoo.addons.ebay_ept.ebaysdk.shopping import Connection as shopping
import time
from datetime import datetime
from odoo.exceptions import  Warning
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class ebay_instace_ept(models.Model):
    _name = "ebay.instance.ept"
    _description = "eBay Instance"
    
    @api.model_cr
    def init(self):        
        self.create_operations()

    @api.multi
    def write(self, vals):
        check = vals.get('allow_out_of_stock_product')
        if ('allow_out_of_stock_product' in vals) and self.auth_token and len(self.auth_token)>1:
            api = self.get_trading_api_object()
            if check == True:
                dict_temp = {'OutOfStockControlPreference':'true'}
            else:
                dict_temp = {'OutOfStockControlPreference':'false'}                
            api.execute('SetUserPreferences',dict_temp)
            results = api.response.dict()
        res = super(ebay_instace_ept, self).write(vals)
        return res
        
    @api.model
    def create_operations(self):
        instances=self.env['ebay.instance.ept'].search([])
        for instance in instances:
            if not self.env['ebay.operations.ept'].search([('instance_id','=',instance.id)]):
                self.create_sequences_and_dashboard_operation(instance)        
        return True
    
    @api.model
    def _get_default_stock_field(self):
        stock_field = self.env['ir.model.fields'].search([('name','=','qty_available'),('model_id.model','=','product.product')],limit=1)
        return stock_field and stock_field.id or False
    
    @api.one
    def _token_expiring_soon(self):
        if self.token_expirationtime :
            time_delta = self.token_expirationtime - datetime.now()
            if time_delta.days < 15:
                self.is_token_expiAlring_soon = True
    
    
    is_auto_get_feedback=fields.Boolean(string="Auto Get FeedBacks?")
    
    name = fields.Char(size=120, string='Name', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    partner_id = fields.Many2one('res.partner', string='Default Customer')
    lang_id = fields.Many2one('res.lang', string='Language')
    order_prefix = fields.Char(size=10, string='Order Prefix')
    auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Auto Workflow')
    order_auto_import = fields.Boolean(string='Auto Order Import?')
    order_auto_update=fields.Boolean(string="Auto Order Update ?")
    stock_auto_export=fields.Boolean(string="Auto Stock Export?")    
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    price_tax_included = fields.Boolean(string='Is Price Tax Included?')
    tax_id = fields.Many2one('account.tax', string='Default Sales Tax')
    stock_field = fields.Many2one('ir.model.fields', string='Stock Field', default=_get_default_stock_field)
    picking_policy =  fields.Selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')], string='Shipping Policy',related="auto_workflow_id.picking_policy",readonly=True)
    invoice_policy = fields.Selection([('order', 'Ordered quantities'),('delivery', 'Delivered quantities'),],string='Invoicing Policy',related="auto_workflow_id.invoice_policy",readonly=True)
    country_id=fields.Many2one("res.country","Country")    
    create_new_product=fields.Boolean("Create New Product",default=False)
    create_quotation_without_product=fields.Boolean("Create Quotation Without Product",default=False)
    pay_mthd = fields.Selection([('PayPal', 'PayPal'),('PaisaPay', 'PaisaPay')],'Payment Methods',help="Method of Payment")
    email_add = fields.Char('Email Address', size=126,help="Seller Email Address")
    post_code = fields.Char('Postal Code',size=64,help="Enter the Postal Code for Item Location")
    auto_update_product = fields.Boolean("Auto Update Product")    
    site_id = fields.Many2one('ebay.site.details','Site')
    dev_id = fields.Char('Dev ID',size=256,required=True,help="eBay Dev ID")
    app_id = fields.Char('App ID',size=256,required=True,help="eBay App ID")
    cert_id = fields.Char('Cert ID',size=256,required=True,help="eBay Cert ID")
    server_url = fields.Char('Server URL',size=256,help="eBay Server URL")
    environment = fields.Selection([('is_sandbox', 'Sandbox'),('is_production', 'Production')],'Environment',required=True)
    auth_token = fields.Text('Token',help="eBay Token")
    ebay_default_product_category_id = fields.Many2one('product.category','Default Product Category',required=False)
    order_status = fields.Selection([('Active', 'Active'),('All', 'All'),('CancelPending','CancelPending'),
                                     ('Completed','Completed'),('Inactive','Inactive'),('Shipped','Shipped')],default='Completed',string='Import Order Status',required=True)
 
    manage_multi_tracking_number_in_delivery_order=fields.Boolean("One order can have multiple Tracking Number ?",default=False)        
    last_ebay_catalog_import_date = fields.Datetime('Last Catalog Import Time',help="Product was last Imported On")
    last_ebay_order_import_date = fields.Datetime('Last Order Import  Time',help="Order was last Imported On")
    last_inventory_export_date = fields.Datetime('Last Inventory Export Time',help="Product Stock last Updated On ")
    last_update_order_export_date = fields.Datetime('Last Order Update  Time',help="Order Status was last Updated On")
    team_id=fields.Many2one('crm.team', 'Sales Team',oldname='section_id')
    shipment_charge_product_id=fields.Many2one("product.product","Shipment Fee",domain=[('type','=','service')])    
    
    is_paypal_account = fields.Boolean('LinkedPayPalAccount',default=False)
    ebay_plus = fields.Boolean("Is eBay Plus Account",default=False)
    is_primary_shipping_address = fields.Boolean('ShipToRegistrationCountry',default=False)
    company_id=fields.Many2one('res.company',string="Company")
    discount_charge_product_id=fields.Many2one("product.product","Order Discount",domain=[('type','=','service')])
    auto_update_payment=fields.Boolean(string="Auto Update Payment In eBay On invoice paid ?")
    state=fields.Selection([('not_confirmed','Not Confirmed'),('confirmed','Confirmed')],default='not_confirmed')
    
    token_expirationtime = fields.Datetime('Token Expiration Time')
    sessionID = fields.Char('SessionID')
    fetch_token_boolean = fields.Boolean('GetToken')
    redirect_url_name = fields.Char('RUname',size=256,help="Redirect URL Name")
    username = fields.Char('Username',size=256,help="Username")
    password = fields.Char('Password',size=256,help="Password")
    allow_out_of_stock_product = fields.Boolean(string="Allow out of stock ?", help="When the quantity of your Good 'Til Cancelled listing reaches zero, the listing remains active but is hidden from search until you increase the quantity. You may also qualify for certain fee credits",default=True)
    use_dynamic_desc = fields.Boolean("Use Dynamic Description", help='If ticked then you can able to use dynamic product description for an individual product only.')
    is_token_expiring_soon = fields.Boolean("Token Expire", compute="_token_expiring_soon", default=False)    
    auto_sync_active_products = fields.Boolean(string="Auto Sync. Active Products ?",help="Auto Sync. Active Products ?")
    sync_active_products_start_date = fields.Date(string="Sync. Active Products Start Date",help="Sync. Active Products Start Date")
    
    auto_send_invoice_via_email = fields.Boolean(string="Auto Send Invoice Via Email ?",help="Auto Send Invoice Via Email.")
    send_invoice_template_id = fields.Many2one("mail.template", "Invoice Template")
    
    is_import_shipped_order = fields.Boolean(string="Import Shipped Orders?",default=False,help="Import Shipped Orders.")
    
    #added by Dhruvi
    global_channel_id = fields.Many2one('global.channel.ept',string='Global Channel')
    product_url = fields.Char(string="Product Site URL")
    
    @api.onchange('environment')
    def onchange_environment(self):
        if self.environment == 'is_sandbox':
            self.server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            self.server_url = 'https://api.ebay.com/ws/api.dll'

    @api.multi
    def openerp_format_date(self, srcDate):
        srcDate = srcDate[:19]
        srcDate = time.strptime(srcDate, "%Y-%m-%dT%H:%M:%S")
        srcDate = time.strftime("%Y-%m-%d %H:%M:%S",srcDate)
        return srcDate
        
    @api.model
    def auto_get_feedback(self,args={}):
        ebay_feedback_obj=self.env['ebay.feedback.ept']
        instance_id=args.get('instance_id')
        if instance_id:
            instances=self.search([('state','=','confirmed'),('id','=',instance_id)])
            ebay_feedback_obj.get_feedback(instances)
        return True
                     
    @api.model
    def auto_import_ebay_sales_orders(self,args={}):
        ebay_sale_order_obj = self.env['sale.order']
        instance_id = args.get('instance_id')
        if instance_id:
            instances = self.search([('state','=','confirmed'),('id','=',instance_id)])
            for instance in instances:
                is_import_shipped_order = instance.is_import_shipped_order or False
                ebay_sale_order_obj.ebay_import_sales_order(instance,is_import_shipped_order)
        return True
    
    @api.model
    def auto_update_order_status(self,args={}):
        instance_id=args.get('instance_id')
        sale_order_obj=self.env['sale.order']
        if instance_id:
            instances=self.search([('id','=',instance_id),('state','=','confirmed')])
            for instance in instances:
                sale_order_obj.ebay_update_order_status(instance)
                instance.write({'last_update_order_export_date':datetime.now()})
        return True
    
    @api.model
    def auto_export_inventory_ept(self,args={}):
        instance_id=args.get('instance_id')
        ebay_product_obj=self.env['ebay.product.product.ept']
        if instance_id:
            instances=self.search([('state','=','confirmed'),('id','=',instance_id)])
            for instance in instances:
                ebay_product_obj.export_stock_levels_ebay(instance)
                instance.write({'last_inventory_export_date':datetime.now()})
        return True  
      
    @api.model
    def check_instance_confirmed_or_not(self):
        if self.state=='confirmed':
            return True
        else:
            return False
        
    @api.model
    def get_trading_api_object(self):
        appid = self.app_id
        devid =  self.dev_id
        certid = self.cert_id
        token = self.auth_token
        username= self.username
        password = self.password

        domain =  'api.sandbox.ebay.com' if self.environment == 'is_sandbox' else 'api.ebay.com'

        site_id = self.site_id.site_id or False
        
        if site_id and not self._context.get('do_not_use_site_id'):
            api = trading(config_file=False,appid=appid,devid=devid,certid=certid,token=token,domain=domain,siteid=self.site_id.site_id,username=username,password=password,timeout=500)
        else:
            api = trading(config_file=False,appid=appid,devid=devid,certid=certid,token=token,domain=domain,username=username,password=password,timeout=500)
        return api
    
    @api.one
    def check_connection(self):
        api=self.get_trading_api_object()
        para ={}
        try:
            api.execute('GetUser', para)
        except Exception as e:
            raise Warning(e)
        raise Warning('Service working properly')
        return True
          
    @api.multi
    def ebay_credential_update(self):
        ebay_credential_view = self.env.ref('ebay_ept.ebay_credential_upadte_wizard', False)
        return ebay_credential_view and {
           'name': 'eBay Credential',
           'view_type': 'form',
           'view_mode': 'form',
           'res_model': 'ebay.credential',
           'type': 'ir.actions.act_window',
           'view_id': ebay_credential_view.id,
           'target': 'new'
        } or True
        
        
    @api.model
    def get_shopping_api_object(self):
        appid = self.app_id
        devid =  self.dev_id
        certid = self.cert_id
        token = self.auth_token
        domain =  'open.api.sandbox.ebay.com' if self.environment == 'is_sandbox' else 'open.api.ebay.com'        
        api = shopping(config_file=False,appid=appid,devid=devid,certid=certid,token=token,domain=domain)        
        return api
        
    @api.model
    def get_ebay_official_time(self):
        try:
            api = self.get_trading_api_object()
            api.execute('GeteBayOfficialTime', {})
            results = api.response.dict()
            return results.get('Timestamp',False) and results['Timestamp'][:19]+'.000Z'
        except Exception:
            raise Warning("Call GeteBayOfficialTime API time error.")
            
    @api.multi
    def create_sequences_and_dashboard_operation(self, instance):
        seq_obj = self.env['ir.sequence']
        dashboard_obj = self.env['ebay.operations.ept']

        color = 0
        available_colors = [0, 3, 5, 4, 6, 7, 8, 1, 2]
        all_used_colors = dashboard_obj.search([('instance_id', '!=', False), ('color', '!=', False)],order='color')
        for x in all_used_colors:
            if x.color in available_colors:
                available_colors.remove(x.color)
        if available_colors:
            color = available_colors[0]

        dashboard_obj.create({
            'name' : instance and instance.name or False,
            'sequence' : seq_obj.sudo().next_by_code('ebay.dashboard.seq'),
            'instance_id' : instance and instance.id or False,
            'color': color})
        return True
    
    @api.multi
    def confirm(self):
        if self.state != 'confirmed' :
            api=self.get_trading_api_object()
            para ={}
            try:
                api.execute('GetUser', para)
            except Exception as e:
                raise Warning(e)
            self.write({'state':'confirmed'})
        return True
        
    @api.multi
    def reset_to_confirm(self):
        self.write({'state':'not_confirmed'})
        return True
    
    @api.multi
    def unlink(self):
        for record in self:
            dashboard_records = self.env['ebay.operations.ept'].search([('instance_id','=',record.id)])
            if dashboard_records :
                dashboard_records.unlink()        
        return super(ebay_instace_ept,self).unlink()
    
    @api.model
    def create(self,vals):
        payment_option_obj=self.env['ebay.payment.options']
        site_details_obj=self.env['ebay.site.details']
        instance = super(ebay_instace_ept, self).create(vals)
        self.create_sequences_and_dashboard_operation(instance)
        if not instance.fetch_token_boolean:
            results = {}
            api = instance.get_trading_api_object()
            para ={}
            api.execute('GeteBayDetails', para)
            results = api.response.dict()
#                 instance.unlink()
#                 self._cr.commit()
#             raise Warning(('%s')%(str(e)))
            if results:
                payment_option_obj.get_payment_options(instance,results.get('PaymentOptionDetails',[]))
                site_details_obj.get_site_details(instance,results.get('SiteDetails',False))
        return instance

    @api.multi
    def fetch_ebay_token(self):
        self.ensure_one()
        """This method is used to catch the auth token experation date and we will able to revoke it from Odoo once it is expired"""
        try:
            if self.environment == 'is_sandbox' :
                api = self.with_context({'do_not_use_site_id':True}).get_trading_api_object()
            else:
                api = self.get_trading_api_object()
            api.execute('GetTokenStatus',{}) 
            results = api.response.dict()
            if results :
                tokenDate = results.get('TokenStatus',{}).get('ExpirationTime')
                tokenDate = tokenDate[0:19]
                tokenDate = time.strptime(tokenDate, "%Y-%m-%dT%H:%M:%S")
                tokenDate = time.strftime("%Y-%m-%d %H:%M:%S",tokenDate)
                self.token_expirationtime = tokenDate    
        except Exception as e:
            raise Warning(e)
        return True
    
    @api.model
    def auto_sync_active_products_listings(self,args={}):
        
        instance_id = args.get('instance_id', False)
        ebay_product_listing_obj = self.env['ebay.product.listing.ept']
    
        if instance_id:
            instances = self.search([('id', '=', instance_id),('state','=','confirmed')])
            if not instances: 
                return False
            
            from_date = instances.sync_active_products_start_date
            to_date = datetime.now().date()
            date_range = []
            while True:
                to_date_tmp = from_date + relativedelta(days=119)
                if to_date_tmp > to_date:
                    date_range.append((datetime.strftime(from_date, DEFAULT_SERVER_DATE_FORMAT),
                                       datetime.strftime(to_date, DEFAULT_SERVER_DATE_FORMAT)))
                    break
                else:
                    date_range.append((datetime.strftime(from_date, DEFAULT_SERVER_DATE_FORMAT),
                                       datetime.strftime(to_date_tmp, DEFAULT_SERVER_DATE_FORMAT)))
                    from_date = to_date_tmp
            for instance in instances:
                for from_date, to_date in date_range:
                    ebay_product_listing_obj.sync_product_listings(instance, from_date, to_date)
            return True
    
    @api.model
    def send_ebay_invoice_via_email(self,args={}):
        instance_obj = self.env['ebay.instance.ept']
        invoice_obj = self.env['account.invoice']
        instance_id = args.get('instance_id', False)

        if instance_id:
            instances = instance_obj.search([('id', '=', instance_id),('state','=','confirmed')])
            if not instances: return False
            
            email_template = (instances.send_invoice_template_id and instances.send_invoice_template_id.id) if instances.send_invoice_template_id else self.env.ref('account.email_template_edi_invoice', False)
            for instance in instances:
                invoices = invoice_obj.search([('ebay_instance_id', '=', instance.id),('state', 'in', ['open', 'paid']), ('sent', '=', False)])
                for x in range(0, len(invoices), 10):
                    invs = invoices[x:x + 10]
                    for invoice in invs:
                        email_template.send_mail(invoice.id)
                        invoice.write({'sent': True})
                    self._cr.commit()
        return True