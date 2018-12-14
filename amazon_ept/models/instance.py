from odoo import models,fields,api,_
from datetime import datetime
from odoo.exceptions import Warning
from ..amazon_emipro_api.mws import Sellers
from odoo.addons.amazon_ept.amazon_emipro_api.api import AmazonAPI

class amazon_instace_ept(models.Model):
    _name="amazon.instance.ept"
    _inherit = ['mail.thread']
    
    def _get_default_company_id(self):
        return self.env.user.company_id.id   
    
    """Added by Dhruvi [28-08-2018]
    To set default value to stock field"""
    
    def _get_default_stock_field(self):
        return self.env.ref('stock.field_product_product__qty_available')
   
    seller_id = fields.Many2one('amazon.seller.ept',string='Seller',required=True)
    marketplace_id = fields.Many2one('amazon.marketplace.ept',string='Marketplace',required=True,
                                     domain="[('seller_id','=',seller_id),('is_participated','=',True)]")
    
    name = fields.Char(size=120, string='Name', required=True)
    company_id = fields.Many2one('res.company',string='Company', required=True,default=_get_default_company_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    partner_id = fields.Many2one('res.partner', string='Default Customer')
    lang_id = fields.Many2one('res.lang', string='Language')
    account_id = fields.Many2one('account.account', string='Account')
    
    """Commented by Dhruvi As these is added to amazon seller"""
#     order_auto_import = fields.Boolean(string='Auto Order Import?')
#     order_prefix = fields.Char(size=10, string='Order Prefix')
#     auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Auto Workflow (FBM)')

    stock_auto_export=fields.Boolean(string="Stock Auto Export?")    
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    price_tax_included = fields.Boolean(string='Is Price Tax Included?')
    tax_id = fields.Many2one('account.tax', string='Default Sales Tax')
    stock_field = fields.Many2one('ir.model.fields', string='Stock Field',default=_get_default_stock_field)
    
    """Changes by Dhruvi auto_workflow_id is fetched according to seller wise"""
    picking_policy=fields.Selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')], string='Shipping Policy',related="seller_id.auto_workflow_id.picking_policy",readonly=True)
    invoice_policy = fields.Selection([('order', 'Ordered quantities'),('delivery', 'Delivered quantities'),],string='Invoicing Policy',related="seller_id.auto_workflow_id.invoice_policy",readonly=True)

    country_id = fields.Many2one("res.country","Country", related="marketplace_id.country_id")    
    
    access_key = fields.Char("Access Key",related="seller_id.access_key")
    secret_key = fields.Char("Secret Key",related="seller_id.secret_key")
    merchant_id = fields.Char("Merchant Id", related="seller_id.merchant_id")
    market_place_id = fields.Char("Marketplace ID", related="marketplace_id.market_place_id")
    
    send_order_acknowledgment = fields.Boolean("Order Acknowledgment required ?")
    allow_order_adjustment = fields.Boolean("Allow Order Adjustment ?")
    catalog_last_sync_on = fields.Datetime("Last Catalog Sync Time")
    inventory_last_sync_on = fields.Datetime("Last FBM Inventory Sync Time")
    image_last_sync_on = fields.Datetime("Last Images Sync Time")
    
    """Commented by Dhruvi as these fields are moved to amazon seller ept"""
#     shipment_charge_product_id=fields.Many2one("product.product","Shipment Fee",domain=[('type','=','service')])
#     gift_wrapper_product_id=fields.Many2one("product.product","Gift Wrapper Fee",domain=[('type','=','service')])
#     promotion_discount_product_id=fields.Many2one("product.product","Promotion Discount",domain=[('type','=','service')])
#     ship_discount_product_id = fields.Many2one("product.product","Shipment Discount",domain=[('type','=','service')])
#     payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')
#     condition = fields.Selection([('New','New'),
#                                   ('UsedLikeNew','UsedLikeNew'),
#                                   ('UsedVeryGood','UsedVeryGood'),
#                                   ('UsedGood','UsedGood'),
#                                   ('UsedAcceptable','UsedAcceptable'),
#                                   ('CollectibleLikeNew','CollectibleLikeNew'),
#                                   ('CollectibleVeryGood','CollectibleVeryGood'),
#                                   ('CollectibleGood','CollectibleGood'),
#                                   ('CollectibleAcceptable','CollectibleAcceptable'),
#                                   ('Refurbished','Refurbished'),
#                                   ('Club','Club')],string="Condition",default='New',copy=False)

    cod_charge_product_id=fields.Many2one("product.product","COD Fee",domain=[('type','=','service')])
    team_id=fields.Many2one('crm.team', 'Sales Team')

    
    pro_advt_access_key=fields.Char("Pro Access Key")
    pro_advt_scrt_access_key=fields.Char("Secret Access Key")
    pro_advt_associate_tag=fields.Char("Associate Tag")
    
    default_amazon_tax_code_id=fields.Many2one('amazon.tax.code.ept',"Default Tax Code")
    fulfillment_by=fields.Selection([('MFN','Manufacturer Fulfillment Network')],string="Fulfillment By",default='MFN')

    manage_multi_tracking_number_in_delivery_order=fields.Boolean("Manage Multi Tracking Number In Delivery Order",default=False)
    
    """Commented by Dhruvi as these fields are added in amazon seller"""
#     auto_create_return_picking = fields.Boolean("Auto Create Return Picking ?",default=False)
#     auto_create_refund = fields.Boolean("Auto Create Refund ?",default=False)
    
    update_stock_on_fly=fields.Boolean("Auto Update Stock On the Fly ?",default=False,help='If it is ticked, real time stock update in Amazon.')
    customer_is_company = fields.Boolean("Customer is Company ?",default=False)
    settlement_report_journal_id = fields.Many2one('account.journal',string='Settlement Report Journal')
    
    """Commented by Dhruvi
        As is_default_odoo_sequence_in_sale_order is moved to amazon seller"""
#     is_default_odoo_sequence_in_sales_order=fields.Boolean("Is default Odoo Sequence in Sales Orders ?")
    ending_balance_account_id=fields.Many2one('account.account',string="Ending Balance Account")
    ending_balance_description=fields.Char("Ending Balance Description")
    invoice_tmpl_id=fields.Many2one("mail.template",string="Invoice Template")# for auto_send_invoice
    refund_tmpl_id=fields.Many2one("mail.template",string="Refund Template")# for auto_send_refund    
    
    #added by Dhruvi
    producturl_prefix = fields.Char(string="Product URL")

    def _count_all(self):
        for instance in self:
            instance.product_count = len(instance.ept_product_ids)
            instance.sale_order_count = len(instance.amazon_sale_order_ids)
            instance.picking_count = len(instance.picking_ids)
            instance.invoice_count = len(instance.invoice_ids)
            instance.exported_product_count = len(instance.exported_product_ids)
            instance.ready_to_expor_product_count = len(instance.ready_to_expor_product_ids)
            
            instance.quotation_count = len(instance.quotation_ids)
            instance.order_count = len(instance.order_ids)
            instance.confirmed_picking_count = len(instance.confirmed_picking_ids)
            instance.assigned_picking_count = len(instance.assigned_picking_ids)
            instance.partially_available_picking_count = len(instance.partially_available_picking_ids)
            instance.done_picking_count = len(instance.done_picking_ids)
            instance.open_invoice_count = len(instance.open_invoice_ids)
            instance.paid_invoice_count = len(instance.paid_invoice_ids)
            instance.refund_invoice_count = len(instance.refund_invoice_ids)
            
    
    color = fields.Integer(string='Color Index')
    
    
    exported_product_ids = fields.One2many('amazon.product.ept', 'instance_id', string='Exported Products',domain=[('exported_to_amazon','=',True)])
    exported_product_count = fields.Integer(compute='_count_all', string="Exported Product")
    
    ready_to_expor_product_ids = fields.One2many('amazon.product.ept','instance_id',domain=[('exported_to_amazon','=',False)],string="Ready To Export")
    ready_to_expor_product_count = fields.Integer(compute='_count_all', string="Ready For Export")
    
#     amazon_browse_node_ids = fields.One2many('amazon.browse.node.ept', 'instance_id', string='Categories')        
    node_count = fields.Integer(compute='_count_all', string="Browse Node")
    ept_product_ids = fields.One2many('amazon.product.ept', 'instance_id', string='Product')
    product_count = fields.Integer(compute='_count_all', string="Products")    
    amazon_sale_order_ids = fields.One2many('sale.order', 'amz_instance_id', string='Order')
    sale_order_count = fields.Integer(compute='_count_all', string="Orders")
    picking_ids = fields.One2many('stock.picking','amazon_instance_id',string="Picking")
    picking_count = fields.Integer(compute='_count_all', string="Pickings") 
    invoice_ids = fields.One2many('account.invoice','amazon_instance_id',string="Invoice")
    invoice_count = fields.Integer(compute='_count_all', string="Invoices")
    
    quotation_ids = fields.One2many('sale.order','amz_instance_id',domain=[('state','in',['draft','sent'])],string="Quotation")        
    quotation_count = fields.Integer(compute='_count_all', string="Quotations")
        
    order_ids = fields.One2many('sale.order','amz_instance_id',domain=[('state','not in',['draft','sent','cancel'])],string="Sales Order")
    order_count =fields.Integer(compute='_count_all', string="Sales Orders")
    
    confirmed_picking_ids = fields.One2many('stock.picking','amazon_instance_id',domain=[('state','=','confirmed')],string="Confirm Picking")
    confirmed_picking_count =fields.Integer(compute='_count_all', string="Confirm Pickings")
    assigned_picking_ids = fields.One2many('stock.picking','amazon_instance_id',domain=[('state','=','assigned')],string="Assigned Picking")
    assigned_picking_count =fields.Integer(compute='_count_all', string="Assigned Pickings")
    partially_available_picking_ids = fields.One2many('stock.picking','amazon_instance_id',domain=[('state','=','partially_available')],string="Partially Available Picking")
    partially_available_picking_count =fields.Integer(compute='_count_all', string="Partially Available Pickings")
    done_picking_ids = fields.One2many('stock.picking','amazon_instance_id',domain=[('state','=','done')],string="Done Picking")
    done_picking_count =fields.Integer(compute='_count_all', string="Done Pickings")
    
    open_invoice_ids = fields.One2many('account.invoice','amazon_instance_id',domain=[('state','=','open'),('type','=','out_invoice')],string="Open Invoice")
    open_invoice_count =fields.Integer(compute='_count_all', string="Open Invoices")    

    paid_invoice_ids = fields.One2many('account.invoice','amazon_instance_id',domain=[('state','=','paid'),('type','=','out_invoice')],string="Paid Invoice")
    paid_invoice_count =fields.Integer(compute='_count_all', string="Paid Invoices")
    
    refund_invoice_ids = fields.One2many('amazon.order.refund.ept','instance_id',string="Refund Invoice")
    refund_invoice_count =fields.Integer(compute='_count_all', string="Refund Invoices")    
    
    

    @api.multi
    def test_amazon_connection(self):
        proxy_data=self.seller_id.get_proxy_server()
        mws_obj=Sellers(access_key=str(self.access_key),secret_key=str(self.secret_key),account_id=str(self.merchant_id),region=self.country_id.amazon_marketplace_code or self.country_id.code,proxies=proxy_data)
        flag=False
        try:
            result = mws_obj.list_marketplace_participations()
            result.parsed.get('ListParticipations',{})
            flag=True
        except Exception as e:
            raise Warning('Given Credentials is incorrect, please provide correct Credentials.')
        if flag:
            raise Warning('Service working properly')
        return True
       
    @api.multi
    def update_changes(self):
        return True
    
    @api.multi
    def write(self,vals):
        res = super(amazon_instace_ept,self).write(vals)
        if 'access_key' in vals or 'secret_key' in vals or 'market_place_id' in vals or 'merchant_id' in vals or \
        'pro_advt_access_key' in vals or 'pro_advt_scrt_access_key' in vals or 'pro_advt_associate_tag' in vals:
            user_object=self.env.user  
            for instance in self:                
                partner_ids=[]
                for follower in instance.message_follower_ids:                    
                    partner_ids.append(follower.partner_id.id)
                body = 'Amazon credentials are updated by %s.'%(user_object.name)
                instance.message_post(body=body,subject='Amazon Credentials Updated',message_type='notification',partner_ids=partner_ids)
        return res 
    
    @api.multi
    def show_amazon_credential(self):
        form = self.env.ref('amazon_ept.amazon_instance_credential_form', False)
        return {
            'name': _('Amazon MWS Credential'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'amazon.instance.ept',
            'view_id': form.id,
            'nodestroy': True,
            'target': 'new',
            'context': {},
            'res_id': self and self.ids[0] or False,
        }         

    @api.multi
    def action_view_products(self):
        action = self.env.ref('amazon_ept.action_amazon_product_ept', False)
        result = action and action.read()[0] or {}
        result['domain'] = "[('instance_id','in',[" + ','.join(map(str, self.ids)) + "])]"
        return result
    
#     @api.multi
#     def action_view_browse_node(self):
#         action = self.env.ref('amazon_ept.action_amazon_browse_node_ept', False)
#         result = action and action.read()[0] or {}
#         result['domain'] = "[('instance_id','in',[" + ','.join(map(str, self.ids)) + "])]"
#         return result
    
    @api.one
    @api.constrains('warehouse_id','company_id')
    def onchange_company_warehouse_id(self):
        if self.warehouse_id and self.company_id and self.warehouse_id.company_id.id != self.company_id.id:
            raise Warning("Company in warehouse is different than the selected company. Selected Company and Warehouse company must be same.")

    @api.onchange('company_id')
    def onchange_company_id(self):
        vals = {}
        domain = {}
        if self.company_id:
            journals = self.env['account.journal'].search([('company_id','=',self.company_id.id),('type','in',['cash','bank'])])
            domain['settlement_report_journal_id'] = [('id','in',journals.ids)]
        else:
            domain['settlement_report_journal_id'] = [('id','in',[])]
        vals.update({'domain' : domain})    
        return vals        

    """Here We have checked if root node exist or not.
        If root node is not exist then we can create root node as an base(parent) node
    """
    
    @api.model
    def check_root_node_exist(self,records):
        vals={}
        browse_node=False
        browse_node_obj=self.env['amazon.browse.node.ept']                    
        for record in records:
            browse_node=browse_node_obj.search([('ama_category_code','=',record.eco_category_code),
                                                ('country_id','=',self.country_id.id),
                                                ('name','=',record.name)])
            if not browse_node:
                vals={'ama_category_code':record.eco_category_code,
                      'name':record.name,
                      'country_id':self.country_id.id}
                browse_node_obj.create(vals)
        return True
    
    
    """Here We Import child browse node from an product advertising api"""
    @api.multi
    def import_browse_node_ept(self):
        base_browse_node_obj=self.env['amazon.base.browse.node.ept']                      
        records=base_browse_node_obj.search([('country_id','=',self.country_id.id)])     
        self.check_root_node_exist(records) 
        return True
       
#     @api.multi
#     def import_sales_order_ept(self):
#         self.env['sale.order'].import_sales_order(self)
#         #self.write({'order_last_sync_on':datetime.now()})
#         return True
    
#     @api.model
#     def auto_import_sale_order_ept(self):
#         sale_order_obj=self.env['sale.order']
#         ctx = dict(self._context) or {}
#         instance_id = ctx.get('instance_id',False)
#         if instance_id:
#             instance=self.search([('id','=',instance_id)])
#             sale_order_obj.import_sales_order(instance)
#             instance.write({'order_last_sync_on':datetime.now()})
#         return True

    @api.multi
    def update_order_status(self):
        self.env['sale.order'].update_order_status(self.seller_id,[self.market_place_id])
        self.write({'shipment_last_sync_on':datetime.now()})
        return True
    

    @api.multi
    def export_stock_levels(self):
        self.env['amazon.product.ept'].export_stock_levels(self)
        self.write({'inventory_last_sync_on':datetime.now()})
        return True
    
#     @api.model
#     def auto_export_inventory_ept(self):
#         amazon_product_obj=self.env['amazon.product.ept']
#         ctx = dict(self._context) or {}
#         instance_id = ctx.get('instance_id',False)
#         if instance_id:
#             instance=self.search([('id','=',instance_id)])
#             amazon_product_obj.export_stock_levels(instance)
#             instance.write({'inventory_last_sync_on':datetime.now()})
# 
#         return True