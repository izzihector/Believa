#!/usr/bin/python3
import ast, time, datetime

from odoo import models,fields,api

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import Warning
from dateutil.relativedelta import relativedelta

class ebay_operations_ept(models.Model):
    _name="ebay.operations.ept"
    _description = "eBay Dashboard"
    _order = "sequence,id"
    
    @api.model
    def find_ebay_cron(self,action_id):
        import_order_cron = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders',raise_if_not_found=False)
        update_order_cron = self.env.ref('ebay_ept.ir_cron_update_order_status',raise_if_not_found=False)
        export_stock_cron = self.env.ref('ebay_ept.ir_cron_auto_export_inventory',raise_if_not_found=False)
        cron_ids = []
        if import_order_cron:
            cron_ids.append(import_order_cron.id)
        if update_order_cron:
            cron_ids.append(update_order_cron.id)
        if export_stock_cron:
            cron_ids.append(export_stock_cron.id)
        for instance in self.env['ebay.instance.ept'].search([]):
            export_stock_cron = self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id),raise_if_not_found=False)
            import_order_cron = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            update_order_cron = self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id),raise_if_not_found=False)
            
            if import_order_cron:
                cron_ids.append(import_order_cron.id)
            if update_order_cron:
                cron_ids.append(update_order_cron.id)
            if export_stock_cron:
                cron_ids.append(export_stock_cron.id)        
        return cron_ids
            
    @api.one
    def _count_operations(self):
        if self.action_id:
            if self.action_id.res_model == 'ir.cron':
                cron_ids = self.find_ebay_cron(self.action_id)
                self.count_record = len(cron_ids) or 0
            else:    
                domain =[]
                if self.action_id.domain:
                    domain = eval(self.action_id.domain)
                count = self.env[self.action_id.res_model].search_count(domain)
                self.count_record = count or 0
            
    @api.multi
    def count_all(self):
        picking_obj=self.env['stock.picking']
        sale_order_obj=self.env['sale.order']
        product_obj=self.env['ebay.product.template.ept']
        invoice_obj=self.env['account.invoice']
        for record in self:

            pickings=picking_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','=','confirmed')])
            record.count_picking_confirmed=len(pickings.ids)
            pickings=picking_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','=','assigned')])
            record.count_picking_assigned=len(pickings.ids)
            pickings=picking_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','=','partially_available')])
            record.count_picking_partial=len(pickings.ids)
            pickings=picking_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','=','done')])
            record.count_picking_done=len(pickings.ids)

            count_picking_late=[('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available')),('ebay_instance_id','=',record.instance_id.id)]
            count_picking_backorders=[('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available')),('ebay_instance_id','=',record.instance_id.id)]
            count_picking=[('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available')),('ebay_instance_id','=',record.instance_id.id)]

            count_picking=picking_obj.search(count_picking)
            count_picking_late=picking_obj.search(count_picking_late)
            count_picking_backorders=picking_obj.search(count_picking_backorders)
            
            if count_picking:
                record.rate_picking_late=len(count_picking_late.ids)*100/len(count_picking.ids)
                record.rate_picking_backorders=len(count_picking_backorders.ids)*100/len(count_picking.ids)
            else:
                record.rate_picking_late=0
                record.rate_picking_backorders=0
            record.count_picking_late=len(count_picking_late.ids)
            record.count_picking_backorders=len(count_picking_backorders.ids)
            orders=sale_order_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','in',['draft','sent'])])
            record.count_quotations=len(orders.ids)
            orders=sale_order_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','not in',['draft','sent','cancel'])])
            record.count_orders=len(orders.ids)

            products=product_obj.search([('instance_id','=',record.instance_id.id),('exported_in_ebay','=',True)])
            record.count_exported_products=len(products.ids)
            products=product_obj.search([('instance_id','=',record.instance_id.id),('exported_in_ebay','=',False)])
            record.count_ready_products=len(products.ids)
            products=product_obj.search([('instance_id','=',record.instance_id.id),('ebay_active_listing_id','!=','False')])
            record.count_active_listing_products=len(products.ids)
            products=product_obj.search([('instance_id','=',record.instance_id.id),('ebay_active_listing_id','=','False'),('exported_in_ebay','=',True)])
            record.count_not_active_listing_products=len(products.ids)
            
            invoices=invoice_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','=','open'),('type','=','out_invoice')])
            record.count_open_invoices=len(invoices.ids)

            invoices=invoice_obj.search([('ebay_instance_id','=',record.instance_id.id),('state','=','paid'),('type','=','out_invoice')])
            record.count_paid_invoices=len(invoices.ids)
            
            invoices=invoice_obj.search([('ebay_instance_id','=',record.instance_id.id),('type','=','out_refund')])
            record.count_refund_invoices=len(invoices.ids)
            
    @api.multi
    def get_today_total_sales(self):
        for record in self:
            instance=record.instance_id
            record.currency_id=instance.pricelist_id.currency_id.id
            order_date=datetime.date.today()
            orders=self.env["sale.order"].search([('date_order','>=',str(order_date)),('state','not in',['cancel','draft']),('ebay_instance_id','=',instance.id)])    
            amount_total=0
            total_units = 0.0
            for order in orders:
                for order_line in order.order_line :
                    if order_line.product_id and order_line.product_id.type != 'service' :
                        total_units += order_line.product_uom_qty
                amount_total+=order.amount_total
            record.today_total_sale = amount_total
            record.today_total_sale_units = total_units
            
    @api.multi
    def get_last_week_total_sales(self):
        for record in self:
            instance=record.instance_id
            today_date=datetime.date.today()
            orders=self.env["sale.order"].search([('date_order','>=',str(today_date+relativedelta(days=-7))),('state','not in',['cancel','draft']),('ebay_instance_id','=',instance.id)])
            amount_total = 0
            total_units = 0.0
            for order in orders:
                for order_line in order.order_line :
                    if order_line.product_id and order_line.product_id.type != 'service' :
                        total_units += order_line.product_uom_qty                
                amount_total+=order.amount_total
            record.week_total_sale=amount_total
            record.week_total_sale_units = total_units
    
    @api.multi
    def get_last_half_month_total_sales(self):
        for record in self:
            instance=record.instance_id
            today_date=datetime.date.today()
            orders=self.env["sale.order"].search([('date_order','>=',str(today_date+relativedelta(days=-15))),('state','not in',['cancel','draft']),('ebay_instance_id','=',instance.id)])
            amount_total = 0
            total_units = 0.0
            for order in orders:
                for order_line in order.order_line :
                    if order_line.product_id and order_line.product_id.type != 'service' :
                        total_units += order_line.product_uom_qty                
                amount_total+=order.amount_total
            record.half_month_total_sale=amount_total
            record.half_month_total_sale_units = total_units

    @api.multi
    def get_last_month_total_sales(self):
        for record in self:
            instance=record.instance_id
            today_date=datetime.date.today()
            orders=self.env["sale.order"].search([('date_order','>=',str(today_date+relativedelta(days=-30))),('state','not in',['cancel','draft']),('ebay_instance_id','=',instance.id)])
            amount_total = 0
            total_units = 0.0
            for order in orders:
                for order_line in order.order_line :
                    if order_line.product_id and order_line.product_id.type != 'service' :
                        total_units += order_line.product_uom_qty                
                amount_total+=order.amount_total
            record.month_total_sale=amount_total
            record.month_total_sale_units = total_units
          
    @api.multi
    @api.depends('instance_id.name')
    def _get_instance_name(self):
        for record in self :
            record.name = record.instance_id and record.instance_id.name or False
                                   
    action_id = fields.Many2one('ir.actions.act_window',string='Action')
    url = fields.Char('Image URL')
    sequence = fields.Integer('Sequence')
    color = fields.Integer('Color')
    name = fields.Char('Name', translate=True, compute="_get_instance_name",store=True)
    
    currency_id = fields.Many2one("res.currency",related="instance_id.pricelist_id.currency_id")
    today_total_sale = fields.Monetary("Total Of Today Sales",compute="get_today_total_sales")
    week_total_sale = fields.Monetary("Total Of Last Week Sales",compute="get_last_week_total_sales")
    half_month_total_sale = fields.Monetary("Total Of Half Month Sales",compute="get_last_half_month_total_sales")
    month_total_sale = fields.Monetary("Total Of Last Month Sales",compute="get_last_month_total_sales")
    
    today_total_sale_units = fields.Float("Total Of Today Sales Units",compute='get_today_total_sales')
    week_total_sale_units = fields.Float("Total Of Last Week Sales Units",compute='get_last_week_total_sales')
    half_month_total_sale_units = fields.Float("Total Of Half Month Sales Units",compute='get_last_half_month_total_sales')
    month_total_sale_units = fields.Float("Total Of Last Month Sales Units",compute='get_last_month_total_sales')
    
    
    count_record = fields.Integer(compute=_count_operations, string='# Record')
    display_inline_image = fields.Boolean('Display Number of records(Inline) in Kanban ?')
    display_outline_image = fields.Boolean('Display Number of records(Outline) in Kanban ?')
    instance_id = fields.Many2one('ebay.instance.ept',string="Instance")
    
    use_quotations=fields.Boolean('Quotations', help="Check this box to manage quotations")
    use_products=fields.Boolean("Products",help="Check this box to manage Products")
    use_invoices=fields.Boolean("Invoices",help="Check This box to manage Invoices")
    use_delivery_orders=fields.Boolean("Delivery Orders",help="Check This box to manage Delivery Orders")
    use_ebay_commerce_workflow=fields.Boolean("Use eBay Workflow",help="Check This box to manage eBay Workflow")
    use_log=fields.Boolean("Use Log",help="Check this box to manage eBay Log")

    count_quotations=fields.Integer("Count Sales Quotations",compute="count_all")
    count_orders=fields.Integer("Count Sales Orders",compute="count_all")    

    count_exported_products=fields.Integer("Count Exported Products",compute="count_all")
    count_ready_products=fields.Integer("Count Ready Products",compute="count_all")
    count_active_listing_products=fields.Integer("Count Active Listing Products",compute="count_all")
    count_not_active_listing_products=fields.Integer("Count Not Active Listing Products",compute="count_all")

    count_picking_confirmed=fields.Integer(string="Count Waiting Picking Waiting",compute="count_all")
    count_picking_assigned=fields.Integer(string="Count Assigned Picking",compute="count_all")
    count_picking_partial=fields.Integer(string="Count Partial Picking",compute="count_all")
    count_picking_done=fields.Integer(string="Count Done Picking",compute="count_all")

    count_open_invoices=fields.Integer(string="Count Open Invoices",compute="count_all")
    count_paid_invoices=fields.Integer(string="Count Paid Invoices",compute="count_all")
    count_refund_invoices=fields.Integer(string="Count Refund Invoices",compute="count_all")

    rate_picking_late=fields.Integer(string="Count Rate Late Pickings",compute="count_all")
    rate_picking_backorders=fields.Integer(string="Count Rate Picking Back Orders",compute="count_all")
    count_picking_late=fields.Integer(string="Count Late Pickings",compute="count_all")
    count_picking_backorders=fields.Integer(string="Count Picking Back Orders",compute="count_all")


    @api.multi
    def _get_action(self, action):
        if self.instance_id.state!='confirmed':
            raise Warning("Instance %s state is not confirmed..."%(self.instance_id.name))
        action = self.env.ref(action) or False
        result = action.read()[0] or {}
        domain = result.get('domain') and ast.literal_eval(result.get('domain')) or []
        if action.res_model == 'res.config.settings' :
            result['context'] = {'instance_id': self.instance_id.id}
        if action.res_model == 'ebay.process.import.export' :
            result['context'] = {'instance_ids': self.instance_id.ids}
        if action.res_model in ['sale.order','stock.picking','account.invoice'] :
            domain.append(('ebay_instance_id','=',self.instance_id.id))
            result['domain'] = domain
        if action.res_model in ['ebay.product.template.ept','ebay.product.product.ept','ebay.template.ept',
                                'ebay.product.listing.ept','ebay.sale.report','ebay.payment.options',
                                'ebay.log.book'] :
            domain.append(('instance_id','=',self.instance_id.id))
            result['domain'] = domain
        if action.res_model == 'ebay.category.master.ept' :
            if self.instance_id.site_id :
                domain.append(('site_id','=',self.instance_id.site_id.id))
                result['domain'] = domain
        if action.res_model == 'ebay.attribute.master' :
            if self.instance_id.site_id :
                domain.append(('categ_id.site_id','=',self.instance_id.site_id.id))
                result['domain'] = domain
        if action.res_model == 'ir.cron':
            cron_ids = self.find_ebay_cron(action)
            result['domain'] = "[('id','in',[" + ','.join(list(map(str, cron_ids))) + "])]"                
        result['display_name'] = "%s: %s" %(self.instance_id.name, action.name)
        return result

    @api.multi
    def get_action_ebay_sale_quotation(self):
        return self._get_action('ebay_ept.action_ebay_sale_quotation')

    @api.multi
    def get_action_ebay_sales_orders(self):
        return self._get_action('ebay_ept.action_ebay_sales_orders')
    
    @api.multi
    def get_action_ebay_product_exported_ept(self):
        return self._get_action('ebay_ept.action_ebay_product_exported_ept')

    @api.multi
    def get_action_ebay_product_not_exported_ept(self):
        return self._get_action('ebay_ept.action_ebay_product_not_exported_ept')
    
    @api.multi
    def get_action_ebay_product_active_ept(self):
        return self._get_action('ebay_ept.action_ebay_product_active_ept')
    
    @api.multi
    def get_action_ebay_product_not_active_ept(self):
        return self._get_action('ebay_ept.action_ebay_product_not_active_ept')
    
    @api.multi
    def get_action_invoice_ebay_invoices_open(self):
        return self._get_action('ebay_ept.action_invoice_ebay_invoices_open')
    
    @api.multi
    def get_action_refund_ebay_invoices(self):
        return self._get_action('ebay_ept.action_refund_ebay_invoices')

    @api.multi
    def get_action_invoice_ebay_invoices_paid(self):
        return self._get_action('ebay_ept.action_invoice_ebay_invoices_paid')

    @api.multi
    def get_action_picking_view_confirm_ept(self):
        return self._get_action('ebay_ept.action_picking_view_confirm_ept')
    
    @api.multi
    def get_action_picking_view_partially_available_ept(self):
        return self._get_action('ebay_ept.action_picking_view_partially_available_ept')

    @api.multi
    def get_action_picking_view_assigned_ept(self):
        return self._get_action('ebay_ept.action_picking_view_assigned_ept')

    @api.multi
    def get_action_picking_view_done_ept(self):
        return self._get_action('ebay_ept.action_picking_view_done_ept')

    #new dashboard        
    @api.multi
    def get_action_perform_oprations(self):
        return self._get_action('ebay_ept.action_wizard_ebay_import_processes_in_ebay_ept')
    
    @api.multi
    def get_action_picking_view_ept(self):
        return self._get_action('ebay_ept.action_picking_view_ept')

    @api.multi
    def get_action_instance_settings(self):
        return self._get_action('ebay_ept.action_ebay_config')
   
    @api.multi
    def get_action_invoice_ebay_invoices(self):
        return self._get_action('ebay_ept.action_invoice_ebay_invoices')
    
    @api.multi
    def get_action_check_ebay_credentials(self):
        if self.instance_id :
            return self.instance_id.ebay_credential_update()
        return True

    @api.multi
    def get_action_ebay_product_template_ept(self):
        return self._get_action('ebay_ept.action_ebay_product_template_ept')
    
    @api.multi
    def get_action_ebay_product_variant_ept(self):
        return self._get_action('ebay_ept.action_ebay_product_variant_ept')
    
    @api.multi
    def get_action_category_master(self):
        return self._get_action('ebay_ept.action_category_master')
        
    @api.multi
    def get_action_store_category_master(self):
        return self._get_action('ebay_ept.action_store_category_master')
    
    @api.multi
    def get_action_attribute_master(self):
        return self._get_action('ebay_ept.action_attribute_master')
    
    @api.multi
    def get_action_ebayerp_template(self):
        return self._get_action('ebay_ept.action_ebayerp_template')
    
    @api.multi
    def get_action_ebay_active_listing(self):
        return self._get_action('ebay_ept.action_ebayerp_active')
    
    @api.multi
    def get_action_ebay_sale_analysis(self):
        return self._get_action('ebay_ept.action_order_report_all')
   
    @api.multi
    def get_action_payment_options(self):
        return self._get_action('ebay_ept.act_payment_method_form')
    
    @api.multi
    def get_action_ebay_job_logs(self):
        return self._get_action('ebay_ept.action_ebay_process_job_ept')
    
    @api.multi
    def get_action_ebay_cron_jobs(self):
        return self._get_action('base.ir_cron_act')
        
    @api.multi
    def view_data(self):
        result = {}
        domain = []
        if self.action_id:
            result = self.action_id and self.action_id.read()[0] or {}
            domain = result.get('domain') and ast.literal_eval(result.get('domain')) or []
            if self.action_id.res_model == 'ir.cron':
                cron_ids = self.find_ebay_cron(self.action_id)
                result['domain'] = "[('id','in',[" + ','.join(list(map(str, cron_ids))) + "])]"        
            if self.action_id.res_model in ['ebay.product.template.ept','ebay.sale.report'] :
                domain.append(('instance_id','=',self.instance_id.id))
                result['domain'] = domain
            if self.action_id.res_model == 'ebay.category.master.ept' :
                if self.instance_id.site_id :
                    domain.append(('site_id','=',self.instance_id.site_id.id))
                    result['domain'] = domain
            if self.action_id.res_model in ['sale.order','stock.picking','account.invoice']:
                domain.append(('ebay_instance_id','=',self.instance_id.id))
                result['domain'] = domain
            if self.action_id.res_model == 'ebay.sale.report' :
                domain.append(('instance_id','=',self.instance_id.id))
        result['display_name'] = "%s: %s" %(self.instance_id.name, self.display_name)
        return result     