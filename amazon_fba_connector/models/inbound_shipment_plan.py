from odoo import models,fields,api,_
from . import api as Amazon_api
# from api import InboundShipments_Extend
from odoo.exceptions import Warning
from datetime import datetime
import logging
from email.policy import default
_logger = logging.getLogger(__name__)

class inbound_shipment_plan_ept(models.Model):
    _name="inbound.shipment.plan.ept"
    _description = "Inbound Shipment Plan"
    _inherit = ['mail.thread']
    _order='id desc'
    label_preference_help="""     
        SELLER_LABEL - Seller labels the items in the inbound shipment when labels are required.
        AMAZON_LABEL_ONLY - Amazon attempts to label the items in the inbound shipment when labels are required. 
            If Amazon determines that it does not have the information required to successfully label an item, that item is not included in the inbound shipment plan
        AMAZON_LABEL_PREFERRED - Amazon attempts to label the items in the inbound shipment when labels are required. 
            If Amazon determines that it does not have the information required to successfully label an item, that item is included in the inbound shipment plan and the seller must label it.                    
    """
    @api.multi
    def get_error_logs(self):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        model_id=amazon_transaction_log_obj.get_model_id('inbound.shipment.plan.ept')
        logs=amazon_transaction_log_obj.search([('model_id','=',model_id),('res_id','=',self.id)])
        self.log_ids=logs.ids
    name = fields.Char(size=120, string='Name', readonly=True,required=False,index=True)
    instance_id = fields.Many2one('amazon.instance.ept',string='Instance',required=True,readonly=True,states={'draft': [('readonly', False)]})
    warehouse_id = fields.Many2one("stock.warehouse",string="Warehouse",readonly=True,states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company',string='Company',required=True,readonly=True,states={'draft': [('readonly', False)]},)
    ship_from_address_id = fields.Many2one('res.partner', string='Ship From Address',readonly=True,states={'draft': [('readonly', False)]})
    ship_to_address_ids = fields.Many2many('res.partner','rel_inbound_shipment_plan_res_partner','shipment_id','partner_id', string='Ship To Addresses',readonly=True)
    ship_to_country = fields.Many2one('res.country', string='Ship To Country',readonly=True,states={'draft': [('readonly', False)]},help="""
The country code for the country where you want your inbound shipment to be sent. 
Only for sellers in North America and Multi-Country Inventory (MCI) sellers in Europe.
    """)
    label_preference = fields.Selection([('SELLER_LABEL', 'SELLER_LABEL'),('AMAZON_LABEL_ONLY', 'AMAZON_LABEL_ONLY'),('AMAZON_LABEL_PREFERRED', 'AMAZON_LABEL_PREFERRED'),],default='SELLER_LABEL', string='LabelPrepPreference',readonly=True,states={'draft': [('readonly', False)]},help=label_preference_help)  
    picking_ids = fields.One2many('stock.picking', 'ship_plan_id',string="Picking", readonly=True)
    shipment_line_ids = fields.One2many('inbound.shipment.plan.line','shipment_plan_id',string='Shipment Plan Items',readonly=True,states={'draft': [('readonly', False)]},help="SKU and quantity information for the items in an inbound shipment.")
    odoo_shipment_ids = fields.One2many('amazon.inbound.shipment.ept','shipment_plan_id', string='Amazon Shipments')
    state = fields.Selection([('draft', 'Draft'),                              
                              ('plan_approved', 'Shipment Plan Approved'),
                              ('cancel','Cancelled')
                              ],default='draft',
                             string='State')
    log_ids=fields.One2many('amazon.transaction.log',compute="get_error_logs")
    is_partnered = fields.Boolean('Is Partnered',default=False,copy=False)
    shipping_type = fields.Selection([('sp','SP (Small Parcel)'),
                                      ('ltl','LTL (Less Than Truckload/FullTruckload (LTL/FTL))')
                                      ],string="Shipping Type",default="sp")
    is_allow_prep_instruction = fields.Boolean(string="Allow Prep Instruction in Inbound Shipment ?",default=False,help="Allow Prep Instruction in Inbound Shipment ?") 
    is_are_cases_required = fields.Boolean(string="Are Cases Required ?",default=False,help="Indicates whether or not an inbound shipment contains case-packed boxes. Note: A shipment must either contain all case-packed boxes or all individually packed boxes.")
    intended_boxcontents_source=fields.Selection([('NONE','NONE'),('FEED','FEED'),('2D_BARCODE','2D_BARCODE')],default='FEED',help="If your instance is USA then you must set box contect, other wise amazon will collect per piece fee",string="Intended BoxContents Source",states={'draft': [('readonly', False)]})

    @api.model
    def create(self,vals):
        try:
            sequence=self.env.ref('amazon_fba_connector.seq_inbound_shipment_plan')
            if sequence:
                name=sequence.next_by_id()
            else:
                name='/'
        except:
            name='/'
        vals.update({'name':name})
        return super(inbound_shipment_plan_ept,self).create(vals)
            
    @api.multi
    def unlink(self):
        for plan in self:
            if plan.state == 'plan_approved':
                raise Warning(_('You cannot delete Inbound Shipment plan which is not draft.'))
        return super(inbound_shipment_plan_ept, self).unlink()
            
    @api.onchange('instance_id')        
    def onchange_instance_id(self):
        if self.instance_id:
            self.company_id = self.instance_id.company_id and self.instance_id.company_id.id
            self.ship_to_country=self.instance_id.country_id and self.instance_id.country_id.id            
            self.is_allow_prep_instruction = self.instance_id.is_allow_prep_instruction or False
    
    @api.onchange('warehouse_id')        
    def onchange_warehouse_id(self):
        if self.warehouse_id:
            self.ship_from_address_id = self.warehouse_id.partner_id and self.warehouse_id.partner_id.id
                                        
    @api.multi
    def reset_all_lines(self):
        self.ensure_one()
        plan_line_obj=self.env['inbound.shipment.plan.line']
        self._cr.execute("""
                            select amazon_product_id from inbound_shipment_plan_line 
                            where shipment_plan_id=%s group by amazon_product_id having count(amazon_product_id)>1;"""%(self.id))
        result=self._cr.fetchall()
        for record in result:
            duplicate_lines=plan_line_obj.search([('amazon_product_id','=',record[0]),('shipment_plan_id','=',self.id)])
            qty=0.0
            for line in duplicate_lines:
                qty+=line.quantity
            duplicate_lines.unlink()
            plan_line_obj.create({'amazon_product_id':record[0],'quantity':qty,'shipment_plan_id':self.id})

    @api.multi
    def import_product_for_inbound_shipment(self):
        """
            Open wizard to import product through csv file.
            File contains only product sku and quantity.
        """
        import_obj = self.env['import.product.inbound.shipment'].create({'shipment_id': self.id})
                
        ctx = self.env.context.copy()
        ctx.update({'shipment_id':self.id, 'update_existing' : False, })
        return import_obj.with_context(ctx).wizard_view()

    """We are updating fix cancel"""
    @api.multi
    def cancel_entire_inbound_shipment(self,shipment,sku_qty_dict,job,mws_obj):
        amazon_transaction_obj=self.env['amazon.transaction.log']

        ship_plan = shipment.shipment_plan_id
        address = ship_plan.ship_from_address_id        
        name, add1, add2, city, postcode = address.name, address.street or '',address.street2 or '',address.city or '', address.zip or ''
        country = address.country_id and address.country_id.code or ''
        state = address.state_id and address.state_id.code or ''
        shipment_status = 'CANCELLED'
        label_prep_type = 'SELLER_LABEL' if shipment.label_prep_type=='NO_LABEL' else shipment.label_prep_type

        try:
            mws_obj.update_inbound_shipment(shipment.name,shipment.shipment_id,shipment.fulfill_center_id,
                                                       name,add1,add2,city,state,postcode,country,
                                                       labelpreppreference = label_prep_type,shipment_status=shipment_status,
                                                       inbound_box_content_status=shipment.intended_boxcontents_source,sku_qty_dict=sku_qty_dict) 
            shipment.write({'state':'CANCELLED'})               
        except Exception as e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message',{}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)  
            else:
                error_value = str(e)        
            amazon_transaction_obj.create({'log_type':'not_found',
                                           'action_type':'terminate_process_with_log',
                                           'operation_type':'export',
                                           'message':error_value,
                                           'model_id':amazon_transaction_obj.get_model_id('inbound.shipment.plan.ept'),
                                           'res_id':self.id,
                                           'job_id':job.id
                                           })
        return True
    @api.multi
    def cancel_inbound_shipemnts(self,odoo_shipments,job):
        for shipment in odoo_shipments:
            if shipment.state=='CANCELLED':
                continue
            ship_plan = shipment.shipment_plan_id
            instance = ship_plan.instance_id
            proxy_data=instance.seller_id.get_proxy_server()
            mws_obj = Amazon_api.InboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code,proxies=proxy_data)
            self.cancel_entire_inbound_shipment(shipment,{}, job, mws_obj)
        return True
    @api.multi
    def set_to_draft_ept(self):
        self.write({'state':'draft'})
        self.odoo_shipment_ids.unlink()
        self.reset_all_lines()
        self.message_post(body=_("<b>Reset to Draft Plan</b>"))
        return True
    @api.multi
    def view_log(self):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        model_id=amazon_transaction_log_obj.get_model_id('inbound.shipment.plan.ept')
        log=amazon_transaction_log_obj.search([('model_id','=',model_id),('res_id','=',self.id)],limit=1)
        if log:
            action = {
                'domain': "[('id', 'in', " + str(log.job_id.ids) + " )]",
                'name': 'Job',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'amazon.process.log.book',
                'type': 'ir.actions.act_window',
                      }
            return action
        else:
            return True

    @api.multi    
    def create_inbound_shipment_plan(self,):
        shipment_obj = self.env['amazon.inbound.shipment.ept']     
        amazon_log_obj=self.env['amazon.process.log.book']
        inbound_shipment_line_obj=self.env['inbound.shipment.plan.line']
        amazon_transaction_obj=self.env['amazon.transaction.log']   
        address = self.ship_from_address_id
        instance = self.instance_id
        ship_plan_rec = self
        ship_to_country_code=self.ship_to_country and self.ship_to_country.code or False
        is_are_cases_required = self.is_are_cases_required or False
        
        proxy_data=instance.seller_id.get_proxy_server()            
        mws_obj=Amazon_api.InboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code,proxies=proxy_data)
        name = address.name
        add1 = address.street or ''
        add2 = address.street2 or ''
        city = address.city or ''
        country = address.country_id and address.country_id.code or ''
        state = address.state_id and address.state_id.code or ''
        postcode = address.zip or ''
        address_ids = []
        odoo_shipments = []
        job=False
        lines=inbound_shipment_line_obj.search([('id','in',self.shipment_line_ids.ids),('quantity','<=',0.0)])
        if lines:
            raise Warning("Qty must be greater then zero Seller Sku : %s"%(lines[0].seller_sku))
        x=0
        while True:       
            shipment_lines=inbound_shipment_line_obj.search([('shipment_plan_id','=',self.id),('odoo_shipment_id','=',False)])
            if not shipment_lines:
                break
            if len(shipment_lines.ids)>20:
                shipment_line_ids = shipment_lines[x:x +20]
            else:
                shipment_line_ids=shipment_lines
            
            if ship_plan_rec and is_are_cases_required:
                zero_qty_in_case_list = []
                for shipment_line_id in shipment_line_ids:
                    if shipment_line_id.quantity_in_case <= 0:
                        zero_qty_in_case_list.append(shipment_line_id.seller_sku)        
                if zero_qty_in_case_list:
                    raise Warning("If you ticked 'Are Cases Required' then 'Quantity In Case' must be greater then zero for this Seller SKU: %s" % (zero_qty_in_case_list))
        
            sku_qty_dict = dict(map(lambda x:(str(x.seller_sku),[str(int(x.quantity)),str(int(x.quantity_in_case))]),shipment_line_ids))
            sku_prep_details_dict = {}
            if self.instance_id and self.instance_id.is_allow_prep_instruction:
                sku_prep_details_dict = dict(map(lambda x:(str(x.seller_sku),{"prep_instuction":[prep_instruction_id.name for prep_instruction_id in x.amazon_product_id.prep_instruction_ids],"prep_owner":x.amazon_product_id.barcode_instruction}),shipment_line_ids))
            
            try:
                result = mws_obj.create_inbound_shipment_plan(name,add1,add2,city,state,postcode,country,ship_to_country_code,
                                                            labelpreppreference = self.label_preference,
                                                            sku_qty_dict=sku_qty_dict,sku_prep_details_dict=sku_prep_details_dict)
            except Exception as e:                
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error)!=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                elif hasattr(mws_obj, 'response') and type(mws_obj.response)!=type(None):
                    error_value = str(mws_obj.response.content)
                else:
                    error_value = str(e)
                """ Here we have canceled all amazon inbound shipment"""
                if not job:
                    job=amazon_log_obj.create({'application':'other',
                                               'operation_type':'export',
                                               'instance_id':instance.id,
                                               'skip_process':True
                                               })
                amazon_transaction_obj.create({'log_type':'not_found',
                                               'action_type':'terminate_process_with_log',
                                               'operation_type':'export',
                                               'message':error_value,
                                               'model_id':amazon_transaction_obj.get_model_id('inbound.shipment.plan.ept'),
                                               'res_id':self.id,
                                               'job_id':job.id
                                               })
                self.cancel_inbound_shipemnts(self.odoo_shipment_ids,job)
                self.write({'state':'cancel'})                
                return True
            shipments = [] 
            if not isinstance(result.parsed.get('InboundShipmentPlans',{}).get('member',[]),list):
                shipments.append(result.parsed.get('InboundShipmentPlans',{}).get('member',{})) 
            else:
                shipments = result.parsed.get('InboundShipmentPlans',{}).get('member',[])
            for shipment in shipments:
                odoo_shipment,job = shipment_obj.create_or_update_inbound_shipment(ship_plan_rec,shipment,job=False)
                if not odoo_shipment:
                    if not job:
                        job=amazon_log_obj.create({'application':'other',
                                                   'operation_type':'export',
                                                   'instance_id':instance.id,
                                                   'skip_process':True
                                                   })
                    self.cancel_inbound_shipemnts(self.odoo_shipment_ids,job)
                    self.write({'state':'cancel'})                
                    return True
                address_ids.append(odoo_shipment.address_id.id)
                odoo_shipments.append(odoo_shipment)
        if odoo_shipments:
            self.create_procurements(list(set(odoo_shipments)),job)            
        vals = {'state':'plan_approved'}    
        if address_ids:
            address_ids=list(set(address_ids))
            vals.update({'ship_to_address_ids':[(6,0,address_ids)]})
        self.write(vals)    
        return True
    
    @api.model
    def create_procurements(self, odoo_shipments,job=False):
        proc_group_obj = self.env['procurement.group']
        picking_obj = self.env['stock.picking']
        shipping_obj = self.env['shipping.report.request.history']
        location_route_obj = self.env['stock.location.route']
        amazon_log_obj=self.env['amazon.process.log.book']
        amazon_transaction_obj=self.env['amazon.transaction.log']   
        group_wh_dict = {}
        for shipment in odoo_shipments:
            proc_group = proc_group_obj.create({'odoo_shipment_id':shipment.id,'name':shipment.name})
            fulfill_center = shipment.fulfill_center_id
            ship_plan = shipment.shipment_plan_id
            fulfillment_center,warehouse = shipping_obj.get_warehouse(fulfill_center,ship_plan.instance_id)
            if not warehouse:
                if not job:
                    job=amazon_log_obj.create({'application':'other',
                                               'operation_type':'export',
                                               'instance_id':shipment.shipment_plan_id.instance_id.id,
                                               'skip_process':True
                                               })
                error_value='No any warehouse found related to fulfillment center %s. Please set fulfillment center %s in warehouse || shipment %s.'%(fulfill_center,fulfill_center,shipment.name)
                amazon_transaction_obj.create({'log_type':'not_found',
                                               'action_type':'terminate_process_with_log',
                                               'operation_type':'export',
                                               'message':error_value,
                                               'model_id':amazon_transaction_obj.get_model_id('amazon.inbound.shipment.ept'),
                                               'res_id':shipment.id,
                                               'job_id':job.id
                                               })                
                continue
            location_routes = location_route_obj.search([('supplied_wh_id','=',warehouse.id),('supplier_wh_id','=',ship_plan.warehouse_id.id)])
            if not location_routes:
                if not job:
                    job=amazon_log_obj.create({'application':'other',
                                               'operation_type':'export',
                                               'instance_id':shipment.shipment_plan_id.instance_id.id,
                                               'skip_process':True
                                               })
                error_value='Location routes are not found. Please configure routes in warehouse properly || warehouse %s & shipment %s.'%(warehouse.name,shipment.name)
                amazon_transaction_obj.create({'log_type':'not_found',
                                               'action_type':'terminate_process_with_log',
                                               'operation_type':'export',
                                               'message':error_value,
                                               'model_id':amazon_transaction_obj.get_model_id('amazon.inbound.shipment.ept'),
                                               'res_id':shipment.id,
                                               'job_id':job.id
                                               })                
                continue
            location_routes = location_routes[0]
            group_wh_dict.update({proc_group:warehouse})

            for line in shipment.odoo_shipment_line_ids:
                qty = line.quantity
                amazon_product = line.amazon_product_id
                datas={'route_ids':location_routes, 
                       'group_id':proc_group,                       
                       'company_id':ship_plan.instance_id.company_id.id, 
                       'warehouse_id': warehouse, 
                       'priority': '1'
                       }
                self.env['procurement.group'].run(amazon_product.product_id,qty,amazon_product.uom_id,warehouse.lot_stock_id,amazon_product.name,shipment.name,datas)
        if group_wh_dict:
            for group,warehouse in group_wh_dict.items(): 
                picking = picking_obj.search([('group_id','=',group.id),('picking_type_id.warehouse_id','=',warehouse.id)])
                if picking:
                    picking.write({'is_fba_wh_picking':True})
        return True
    
    @api.multi
    def create_inbound_shipments(self):
        pickings = self.env['stock.picking'].search([('ship_plan_id','=',self.id)])
        for picking in pickings:
            picking.create_inbound_shipment()
        return True
    
    @api.multi
    def get_product_prep_instructions(self):
        """
            When click Get Prep-Instructions button to product wise get Prep-Instructions details.
            @return: True
        """
        amazon_product_obj = self.env['amazon.product.ept']
        instance = self.instance_id or False
        if instance:
            amazon_product_ids_list = [shipment_line_id.amazon_product_id.id for shipment_line_id in self.shipment_line_ids]
            amazon_products = amazon_product_obj.search([("id","in",amazon_product_ids_list),("instance_id","=",instance.id)])
            amazon_products and amazon_product_obj.get_product_prep_instructions(instance,amazon_products)
        return True
                
class inbound_shipment_plan_line(models.Model):
    _name="inbound.shipment.plan.line"  
    _description = 'inbound.shipment.plan.line'  
    
    amazon_product_id = fields.Many2one('amazon.product.ept',string='Product',domain=[('fulfillment_by','=','AFN')])
    quantity = fields.Float('Quantity')
    seller_sku = fields.Char(size=120, string='Seller SKU', related="amazon_product_id.seller_sku",readonly=True)
    shipment_plan_id = fields.Many2one('inbound.shipment.plan.ept',string='Shipment Plan')
    odoo_shipment_id = fields.Many2one('amazon.inbound.shipment.ept',string='Shipment')
    fn_sku = fields.Char(size=120, string='Fulfillment Network SKU', readonly=True, help="Provided by Amazon when we send shipment to Amazon")
    quantity_in_case = fields.Float(string="Quantity In Case",help="Amazon FBA: Quantity In Case.")
    received_qty =  fields.Float("Received Quantity",default=0.0,copy=False,help="Received Quantity")
    difference_qty = fields.Float("Difference Quantity",compute="_get_total_diffrence_qty",help="Difference Quantity")
    is_extra_line = fields.Boolean("Extra Line ?",default=False,help="Extra Line ?")
    
    @api.one
    def _get_total_diffrence_qty(self):
        self.ensure_one()
        self.difference_qty = self.quantity - self.received_qty
    
    @api.one
    @api.constrains('amazon_product_id', 'shipment_plan_id','shipment_id')
    def _check_unique_line(self):
        if self.odoo_shipment_id:
            domain = [('id','<>',self.id),('amazon_product_id','=',self.amazon_product_id.id),('shipment_plan_id','=',self.shipment_plan_id.id),('odoo_shipment_id','=',self.odoo_shipment_id.id)]
        else:    
            domain = [('id','<>',self.id),('amazon_product_id','=',self.amazon_product_id.id),('shipment_plan_id','=',self.shipment_plan_id.id),('odoo_shipment_id','=',False)]
        if self.search(domain): 
            if not self._context.get('ignore_rule'):       
                raise Warning(_('Product %s line already exist in Shipping plan Line.'%(self.amazon_product_id.seller_sku)))

    @api.multi        
    def create_update_plan_line(self,odoo_shipment,items):        
        ship_plan = odoo_shipment.shipment_plan_id
        sku_qty_dict = {}
        sku_prep_details_dict = {}
        for item in items:
            sku = item.get('SellerSKU',{}).get('value','')
            qty = float(item.get('Quantity',{}).get('value',0.0))
            quantity_in_case = float(item.get('QuantityInCase',{}).get('value',0.0))
            fn_sku = item.get('FulfillmentNetworkSKU',{}).get('value','')
            
            line = self.search([('amazon_product_id.seller_sku','=',sku),('shipment_plan_id','=',ship_plan.id)])
            if line and len(line) > 1:
                line = self.search([('amazon_product_id.seller_sku','=',sku),('shipment_plan_id','=',ship_plan.id),('odoo_shipment_id','=',odoo_shipment.id)])
                if not line:
                    line = self.search([('amazon_product_id.seller_sku','=',sku),('shipment_plan_id','=',ship_plan.id),('odoo_shipment_id','=',False)])
            if line:
                line = line[0] if len(line) > 1 else line
                vals = {'odoo_shipment_id':odoo_shipment.id,'fn_sku':fn_sku}
                amazon_product = line.amazon_product_id
                
                if amazon_product.prep_instruction_ids:
                    sku_prep_details_dict.update({ 
                        sku: {
                            "prep_instuction": [prep_instruction_id.name for prep_instruction_id in amazon_product.prep_instruction_ids],
                            "prep_owner": amazon_product.barcode_instruction}
                    })
                
                if line.quantity == qty:
                    line.write(vals)
                else:
                    qty_left = line.quantity - qty
                    vals.update({'quantity':qty})
                    line.write(vals)    
                    self.with_context({'ignore_rule':True}).create({'quantity':qty_left,'amazon_product_id':amazon_product.id,'shipment_plan_id':ship_plan.id,'odoo_shipment_id':False,'quantity_in_case':quantity_in_case})
                sku_qty_dict.update({sku: [str(int(qty)),str(int(quantity_in_case))] })
        return sku_qty_dict,sku_prep_details_dict

         
