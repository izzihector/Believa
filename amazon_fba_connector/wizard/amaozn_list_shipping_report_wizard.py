from odoo import models,fields,api
import time
from datetime import datetime
from odoo.addons.amazon_ept.amazon_emipro_api.mws import Reports
from odoo.exceptions import Warning

class amazon_list_shipping_report_wizard(models.TransientModel):
    _name="amazon.list.shipping.report.wizard"
    _description = 'amazon.list.shipping.report.wizard'
    
    seller_id = fields.Many2one("amazon.seller.ept","Seller")
    report_type = fields.Char(size=256, string='Report Type',default='_GET_AMAZON_FULFILLED_SHIPMENTS_DATA_')
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')
        
    @api.model
    def default_get(self,fields):
        res = super(amazon_list_shipping_report_wizard,self).default_get(fields)
        if 'default_instance_id' in self._context:
            instance_id = self._context.get('default_instance_id')
            if instance_id:
                instance = self.env['amazon.instance.ept'].browse(instance_id)
                res.update({'seller_id':instance.seller_id.id})
        return res
    
    @api.onchange('seller_id')
    def on_change_seller_id(self):
        value = {}
        if self.seller_id:
            value.update({'start_date':self.seller_id.shipping_report_last_sync_on,'end_date':datetime.now()})
        return {'value': value }
    
    @api.multi
    def _check_duration(self):
        if self.end_date < self.start_date:
            return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe start date must be precede its end date.', ['start_date','end_date'])
    ]

    @api.multi
    def get_shipping_report(self):
        instance_obj=self.env['amazon.instance.ept']
        instances=instance_obj.search([('seller_id','=',self.seller_id.id)])
        seller_ids=[]
        for instance in instances:
            if instance.seller_id.is_another_soft_create_fba_shipment:
                proxy_data= instance.seller_id.get_proxy_server()
                mws_obj = Reports(access_key=str(instance.seller_id.access_key),secret_key=str(instance.seller_id.secret_key),account_id=str(instance.seller_id.merchant_id),region=instance.seller_id.country_id.amazon_marketplace_code or instance.seller_id.country_id.code,proxies=proxy_data)
                start_date=self.start_date
                end_date=self.end_date
                db_import_time = time.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                db_import_time = time.strftime("%Y-%m-%dT%H:%M:%S",db_import_time)
                start_date = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(db_import_time,"%Y-%m-%dT%H:%M:%S"))))
                start_date = str(start_date)+'Z'
                db_import_time = time.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                db_import_time = time.strftime("%Y-%m-%dT%H:%M:%S",db_import_time)
                end_date = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(db_import_time,"%Y-%m-%dT%H:%M:%S"))))
                end_date = str(end_date)+'Z'
                result=mws_obj.get_report_request_list(types=('_GET_AMAZON_FULFILLED_SHIPMENTS_DATA_',),fromdate=start_date, todate=end_date)
                list_of_wrapper=[]
                list_of_wrapper.append(result)
                has_next = result.parsed.get('HasNext',{}).get('value',False)
                while has_next =='true':
                    next_token=result.parsed.get('NextToken',{}).get('value')
                    try:
                        time.sleep(10)
                        result = mws_obj.get_report_request_list_by_next_token(next_token)
                        list_of_wrapper.append(result)
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
                
                shipping_report_req_history_obj=self.env['shipping.report.request.history']
                odoo_report_ids = []
                list_of_wrapper.reverse()
                for result in list_of_wrapper:
                    reports=[]
                    if not isinstance(result.parsed.get('ReportRequestInfo',[]),list):
                        reports.append(result.parsed.get('ReportRequestInfo',[])) 
                    else:
                        reports=result.parsed.get('ReportRequestInfo',[]) 
                        reports.reverse()              
                    for report in reports:
                        start_date=report.get('StartDate','').get('value','')
                        end_date=report.get('EndDate','').get('value','')
                        submited_date=report.get('SubmittedDate','').get('value','')
                        report_id=report.get('GeneratedReportId',{}).get('value','')
                        request_id = report.get('ReportRequestId',{}).get('value','')
                        report_type = report.get('ReportType',{}).get('value','')
                        state=report.get('ReportProcessingStatus',{}).get('value','')
                        report_exist = shipping_report_req_history_obj.search(['|',('report_request_id','=',request_id),('report_id','=',report_id),('report_type','=',report_type)])
                        if report_exist:
                            report_exist= report_exist[0]
                            odoo_report_ids.append(report_exist.id) 
                            continue
                        try:
                            sequence=self.env.ref('amazon_fba_connector.seq_import_shipping_report_job')
                            if sequence:
                                report_name=sequence.next_by_id()
                            else:
                                report_name='/'
                        except:
                            report_name='/'
        
                        vals = {
                                'name':report_name,
                                'report_type':report_type,
                                'report_request_id':request_id,
                                'report_id':report_id,
                                'start_date':start_date,
                                'end_date':end_date,
                                'requested_date':submited_date,
                                'state':state,
                                'seller_id':instance.seller_id.id,
                                'user_id':self._uid,
                            }
                            
                        report_rec = shipping_report_req_history_obj.create(vals)
                        odoo_report_ids.append(report_rec.id)
                instance.seller_id.write({'shipping_report_last_sync_on':end_date})
            else:
                if instance.seller_id.id not in seller_ids:
                    ship_report = self.env['shipping.report.request.history'].create({'report_type' : '_GET_AMAZON_FULFILLED_SHIPMENTS_DATA_',
                             'seller_id':instance.seller_id.id,
                             'start_date' : self.start_date,
                             'end_date' : self.end_date,
                             'state' :'draft',
                             })
                                    
                    ship_report.request_report()      
                    seller_ids.append(instance.seller_id.id)
                    