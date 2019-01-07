from openerp import models,fields,api,_
from openerp.addons.amazon_ept.amazon_emipro_api.mws import Reports
from openerp.exceptions import Warning
import time
from datetime import datetime,timedelta
import base64
import csv
from io import StringIO
class amazon_live_stock_report_ept(models.Model):
    _name="amazon.fba.live.stock.report.ept"
    _inherits={"report.request.history":'report_history_id'}
    _description = "Amazon Live Stock Report"
    _inherit = ['mail.thread']
    _order = 'id desc'

    @api.model
    def create(self,vals):    
        try:
            sequence=self.env.ref('amazon_fba_connector.seq_import_live_stock_report_job')
            if sequence:
                report_name=sequence.next_by_id()
            else:
                report_name='/'
        except:
            report_name='/'
        vals.update({'name':report_name})
        return super(amazon_live_stock_report_ept,self).create(vals)

    name = fields.Char(size=256, string='Name')
    report_history_id = fields.Many2one('report.request.history', string='Report',required=True,ondelete="cascade",index=True, auto_join=True)
    state = fields.Selection([('draft','Draft'),('_SUBMITTED_','SUBMITTED'),('_IN_PROGRESS_','IN_PROGRESS'),
                                     ('_CANCELLED_','CANCELLED'),('_DONE_','DONE'),
                                     ('_DONE_NO_DATA_','DONE_NO_DATA'),('processed','PROCESSED')
                                     ],
                                    string='Report Status', default='draft')
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    auto_generated = fields.Boolean('Auto Generated Record ?', default=False)
    report_date=fields.Date('Report Date')
    log_count=fields.Integer(compute="get_log_count",string="Log Count")
    inventory_ids=fields.One2many('stock.inventory','fba_live_stock_report_id',string='Inventory')
    @api.one
    def get_log_count(self):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        model_id=amazon_transaction_log_obj.get_model_id('amazon.fba.live.stock.report.ept')
        records=amazon_transaction_log_obj.search([('model_id','=',model_id),('res_id','=',self.id)])
        self.log_count=len(records.ids)
    
    @api.multi
    def list_of_inventory(self):
        action = {
            'domain': "[('id', 'in', " + str(self.inventory_ids.ids) + " )]",
            'name': 'FBA Live Stock Inventory',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.inventory',
            'type': 'ir.actions.act_window',
                  }
        return action
    @api.multi
    def download_report(self):
        self.ensure_one()
        if self.attachment_id:
            return {
                    'type' : 'ir.actions.act_url',
                    'url':   '/web/content/%s?download=true' % ( self.attachment_id.id ),
                    'target': 'self',
                    }
        return True
    
    @api.model
    def auto_import_amazon_fba_live_stock_report(self,args={}):
        instance_id = args.get('instance_id',False)
        if instance_id:
            instance = self.env['amazon.instance.ept'].browse(instance_id)
            if instance.stock_auto_import_by_report:
                fba_live_stock_report=self.create({'seller_id':instance.seller_id.id,'report_date':datetime.now()})
                fba_live_stock_report.request_report()
        return True
    
    @api.model
    def auto_process_amazon_fba_live_stock_report(self,args={}):
        instance_id = args.get('instance_id',False)
        if instance_id:
            instance = self.env['amazon.instance.ept'].browse(instance_id)
            seller=instance.seller_id
            fba_live_stock_report = self.search([('seller_id','=',seller.id),
                                            ('state','in',['_SUBMITTED_','_IN_PROGRESS_']),
                                            ])
            fba_live_stock_report.get_report_request_list_via_cron(seller)
             
            reports = self.search([('seller_id','=',seller.id),
                                            ('state','=','_DONE_'),
                                            ('report_id','!=',False)
                                            ])             
            for report in reports:
                report.get_report()
                report.process_fba_live_stock_report()
                self._cr.commit()                
        return True
    
    @api.multi
    def list_of_logs(self):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        model_id=amazon_transaction_log_obj.get_model_id('amazon.fba.live.stock.report.ept')
        records=amazon_transaction_log_obj.search([('model_id','=',model_id),('res_id','=',self.id)])
        action = {
            'domain': "[('id', 'in', " + str(records.ids) + " )]",
            'name': 'Feed Logs',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'amazon.transaction.log',
            'type': 'ir.actions.act_window',
                  }
        return action
    
    @api.model
    def create_log(self, message, model_id, job, report_id, missing_value='', log_type='not_found'):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        amazon_transaction_log_obj.create({
                                   'model_id':model_id,
                                   'message':message,
                                   'res_id':report_id,
                                   'operation_type':'import',
                                   'job_id':job.id,
                                   'skip_record' : True,
                                   'log_type' : log_type,  
                                   'not_found_value' : missing_value or '',  
                                   'action_type' : 'skip_line',                                                    
       })
    
    def fill_dictionary_from_file(self, reader,job,report_id):
        amazon_transaction_log_obj=self.env['amazon.transaction.log']
        amazon_instnace_obj=self.env['amazon.instance.ept']
        amazon_product_obj=self.env['amazon.product.ept']

        model_id=amazon_transaction_log_obj.get_model_id('amazon.fba.live.stock.report.ept')
        sellable_line_dict={}
        unsellable_line_dict={}
        instance_ids = amazon_instnace_obj.search([('seller_id','=',self.seller_id.id)]).ids
        for row in reader:
            seller_sku=row.get('seller-sku')
            odoo_product=False
            if not seller_sku:
                continue
            domain = [('seller_sku','=',seller_sku),('instance_id','in',instance_ids)]
            amazon_product = amazon_product_obj.search(domain, limit=1)
            warehouse_condition=row.get('Warehouse-Condition-code')
            if amazon_product:
                odoo_product=amazon_product.product_id
            else:
                message = 'Amazon product not found for SKU %s'%(seller_sku)
                if not amazon_transaction_log_obj.search([('message','=',message),('manually_processed','=',False)]):
                    self.create_log(message, model_id, job, report_id, missing_value=seller_sku)                
                continue     
                   
            if warehouse_condition =='SELLABLE':
                qty=sellable_line_dict.get(odoo_product,0.0)
                sellable_line_dict.update({odoo_product:qty+float(row.get('Quantity Available',0.0))})
            else :
                qty=unsellable_line_dict.get(odoo_product,0.0)
                unsellable_line_dict.update({odoo_product:qty+float(row.get('Quantity Available',0.0))})
        return sellable_line_dict,unsellable_line_dict
    
    @api.multi 
    def process_fba_live_stock_report(self):
        self.ensure_one()
        if not self.attachment_id:
            raise Warning("There is no any report are attached with this record.")
        imp_file = StringIO(base64.decodestring(self.attachment_id.datas).decode())
        reader = csv.DictReader(imp_file,delimiter='\t')
        amazon_process_job_log_obj=self.env['amazon.process.log.book']
        inventory_obj=self.env['stock.inventory']
        job=amazon_process_job_log_obj.create({'application':'stock_report','operation_type':'import'})#,'seller_id':self.seller_id and self.seller_id.id or False})
        
        sellable_line_dict,unsellable_line_dict = self.fill_dictionary_from_file(reader,job,self.id)

        warehouse = self.seller_id.warehouse_ids and self.seller_id.warehouse_ids[0] or False
        if warehouse:
            inventory_obj.create_stock_inventory_from_amazon_live_report(sellable_line_dict,unsellable_line_dict, warehouse, self.id, seller = self.seller_id,job=job)#inv_mismatch_details_sellable_list,inv_mismatch_details_unsellable_list,
        self.write({'state':'processed'})
    
    @api.model
    def default_get(self, fields):
        res = super(amazon_live_stock_report_ept, self).default_get(fields)
        if not fields:
            return res
        res.update({'report_type' : '_GET_AFN_INVENTORY_DATA_',
                    })
        return res
    
    @api.multi
    def request_report(self):
        seller,report_type,start_date,end_date = self.seller_id,self.report_type,self.start_date,self.end_date
        if not seller:
            raise Warning('Please select Seller')
        
        if start_date:
            db_import_time = time.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            db_import_time = time.strftime("%Y-%m-%dT%H:%M:%S",db_import_time)
            start_date = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(db_import_time,"%Y-%m-%dT%H:%M:%S"))))
            start_date = str(start_date)+'Z'
        else:
            today = datetime.now()
            earlier = today - timedelta(days=30)
            earlier_str = earlier.strftime("%Y-%m-%dT%H:%M:%S")
            start_date = earlier_str+'Z'
            
        if end_date:
            db_import_time = time.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            db_import_time = time.strftime("%Y-%m-%dT%H:%M:%S",db_import_time)
            end_date = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(db_import_time,"%Y-%m-%dT%H:%M:%S"))))
            end_date = str(end_date)+'Z'
        else:
            today = datetime.now()
            earlier_str = today.strftime("%Y-%m-%dT%H:%M:%S")
            end_date = earlier_str+'Z'
        proxy_data=seller.get_proxy_server()
        mws_obj = Reports(access_key=str(seller.access_key),secret_key=str(seller.secret_key),account_id=str(seller.merchant_id),region=seller.country_id.amazon_marketplace_code or seller.country_id.code,proxies=proxy_data)
        instances = self.env['amazon.instance.ept'].search([('seller_id','=',seller.id)])
        
        marketplaceids = tuple(map(lambda x: x.market_place_id,instances))
        try:
            result = mws_obj.request_report(report_type, start_date=start_date, end_date=end_date, marketplaceids=marketplaceids)
            self.update_report_history(result)
        except Exception as e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message',{}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)  
            else:
                error_value = str(e)
            raise Warning(error_value)

        return True  
    
    @api.model
    def update_report_history(self,request_result):
        result = request_result.parsed
        report_info = result.get('ReportInfo',{})
        report_request_info = result.get('ReportRequestInfo',{})
        request_id = report_state = report_id = False
        if report_request_info:
            request_id = str(report_request_info.get('ReportRequestId',{}).get('value',''))
            report_state = report_request_info.get('ReportProcessingStatus',{}).get('value','_SUBMITTED_')
            report_id = report_request_info.get('GeneratedReportId',{}).get('value',False)
        elif report_info:
            report_id = report_info.get('ReportId',{}).get('value',False)
            request_id = report_info.get('ReportRequestId',{}).get('value',False)
        
        if report_state =='_DONE_' and not report_id:
            self.get_report_list()
        vals = {}
        if not self.report_request_id and request_id:
            vals.update({'report_request_id':request_id}) 
        if report_state:
            vals.update({'state':report_state})
        if report_id:
            vals.update({'report_id':report_id})
        self.write(vals)
        return True
    @api.multi
    def get_report_request_list(self):
        self.ensure_one()
        seller = self.seller_id
        if not seller:
            raise Warning('Please select Seller')
        
        proxy_data=seller.get_proxy_server()
        mws_obj = Reports(access_key=str(seller.access_key),secret_key=str(seller.secret_key),account_id=str(seller.merchant_id),region=seller.country_id.amazon_marketplace_code or seller.country_id.code,proxies=proxy_data)
        if not self.report_request_id:
            return True
        try:
            result = mws_obj.get_report_request_list(requestids = (self.report_request_id,))
            self.update_report_history(result)
            
        except Exception as e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message',{}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)  
            else:
                error_value = str(e)
            raise Warning(error_value)
        list_of_wrapper=[]
        list_of_wrapper.append(result)
        has_next = result.parsed.get('HasNext',{}).get('value','false')
        while has_next =='true':
            next_token = result.parsed.get('NextToken',{}).get('value')
            try:
                result=mws_obj.get_report_request_list_by_next_token(next_token)
                self.update_report_history(result)

            except Exception as e:
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)
                raise Warning(error_value)
            
            has_next = result.parsed.get('HasNext',{}).get('value','')
            list_of_wrapper.append(result)
        
        return True
    
    @api.model
    def update_report_history_via_cron(self,request_result,report_info_records,seller):
        result = request_result.parsed
        report_info = result.get('ReportInfo',{})
        if isinstance(result.get('ReportInfo',[]),list):
            report_info=result.get('ReportInfo',[])
        else:
            report_info.append(result.get('ReportInfo',{}))
        report_request_info=[]     
        if isinstance(result.get('ReportRequestInfo',[]),list):
            report_request_info=result.get('ReportRequestInfo',[])
        else:
            report_request_info.append(result.get('ReportRequestInfo',{}))
        for info in report_request_info:                
            request_id = str(info.get('ReportRequestId',{}).get('value',''))
            report_state = info.get('ReportProcessingStatus',{}).get('value','_SUBMITTED_')
            report_id = info.get('GeneratedReportId',{}).get('value',False)
            report_record=report_info_records.get(request_id)
            vals = {}
            if report_state:
                vals.update({'state':report_state})
            if report_id:
                vals.update({'report_id':report_id})
            report_record and report_record.write(vals)
        return True


    @api.multi
    def get_report_request_list_via_cron(self,seller):
        if not seller:
            raise Warning('Please select Seller')
        proxy_data=seller.get_proxy_server()
        mws_obj = Reports(access_key=str(seller.access_key),secret_key=str(seller.secret_key),account_id=str(seller.merchant_id),region=seller.country_id.amazon_marketplace_code or seller.country_id.code,proxies=proxy_data)
        request_ids=[report.report_request_id for report in self]
        report_info_records={report.report_request_id:report for report in self}
        if not request_ids:
            return True            
        try:
            result = mws_obj.get_report_request_list(requestids =request_ids)
            self.update_report_history_via_cron(result,report_info_records,seller)
            
        except Exception as e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message',{}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)  
            else:
                error_value = str(e)
            raise Warning(error_value)
        list_of_wrapper=[]
        list_of_wrapper.append(result)
        has_next = result.parsed.get('HasNext',{}).get('value','false')
        while has_next =='true':
            next_token = result.parsed.get('NextToken',{}).get('value')
            try:
                result=mws_obj.get_report_request_list_by_next_token(next_token)
                self.update_report_history_via_cron(result,report_info_records,seller)

            except Exception as e:
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)
                raise Warning(error_value)
            
            has_next = result.parsed.get('HasNext',{}).get('value','')
            list_of_wrapper.append(result)
        
        return True
    
    @api.multi
    def get_report(self):
        self.ensure_one()
        seller = self.seller_id
        if not seller:
            raise Warning('Please select seller')
        
        proxy_data=seller.get_proxy_server()
        mws_obj = Reports(access_key=str(seller.access_key),secret_key=str(seller.secret_key),account_id=str(seller.merchant_id),region=seller.country_id.amazon_marketplace_code or seller.country_id.code,proxies=proxy_data)
        if not self.report_id:
            return True
        try:
            result = mws_obj.get_report(report_id=self.report_id)
        except Exception as e:
            if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                error = mws_obj.parsed_response_error.parsed or {}
                error_value = error.get('Message',{}).get('value')
                error_value = error_value if error_value else str(mws_obj.response.content)  
            else:
                error_value = str(e)
            raise Warning(error_value)
        result = base64.b64encode(result.parsed)
        file_name = "Fba_Live_report_" + time.strftime("%Y_%m_%d_%H%M%S") + '.csv'
        
        attachment = self.env['ir.attachment'].create({
                                           'name': file_name,
                                           'datas': result,
                                           'datas_fname': file_name,
                                           'res_model': 'mail.compose.message',
                                           'type': 'binary'
                                         })
        self.message_post(body=_("<b>Live Inventory Report Downloaded</b>"),attachment_ids=attachment.ids)
        self.write({'attachment_id':attachment.id})
        
        return True
