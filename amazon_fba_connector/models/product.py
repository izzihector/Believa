from odoo import models,api,fields
from ...amazon_ept.amazon_emipro_api.mws import Feeds
from . import api as Amazon_api
from odoo.exceptions import Warning
import time

class amazon_product_ept(models.Model):
    _inherit ="amazon.product.ept"
    
    fulfillment_by = fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')
    prep_instruction_ids = fields.Many2many("prep.instruction","amazon_prep_instruction_rel","amazon_product_id","prep_instruction_id",string="Prep Instruction",help="Amazon FBA: Prep Instruction")
    barcode_instruction = fields.Selection([('AMAZON','Amazon'),('SELLER','Seller')],string="Barcode Instruction",help="Amazon FBA: Barcode Instruction")
    quantity_in_case = fields.Float(string="Quantity In Case",default=0.0,help="Amazon FBA: Quantity In Case")  
    
    @api.multi
    def get_switch_product_header(self,instnace):
        return """<?xml version="1.0"?>
            <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
            <Header>        
                <DocumentVersion>1.01</DocumentVersion>
                <MerchantIdentifier>%s</MerchantIdentifier>
            </Header>
            <MessageType>Inventory</MessageType>
        """%(instnace.merchant_id)
        
    def switch_feed_submit(self,instance,data):
        proxy_data=instance.seller_id.get_proxy_server()
        mws_obj=Feeds(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code,proxies=proxy_data)
        results=mws_obj.submit_feed(data.encode('utf-8'),'_POST_INVENTORY_AVAILABILITY_DATA_',marketplaceids=[instance.market_place_id])
        time.sleep(120)
        results=results.parsed
        last_feed_submission_id=False
        if results.get('FeedSubmissionInfo',{}).get('FeedSubmissionId',{}).get('value',False):
            last_feed_submission_id=results.get('FeedSubmissionInfo',{}).get('FeedSubmissionId',{}).get('value',False)
            try:
                submission_results=mws_obj.get_feed_submission_result(last_feed_submission_id)
                error=submission_results._response_dict.get('Message',{}).get('ProcessingReport',{}).get('ProcessingSummary',{}).get('MessagesWithError',{}).get('value','1')
            except Exception as e:
                if hasattr(mws_obj, 'parsed_response_error') and type(mws_obj.parsed_response_error) !=type(None):
                    error = mws_obj.parsed_response_error.parsed or {}
                    error_value = error.get('Message',{}).get('value')
                    error_value = error_value if error_value else str(mws_obj.response.content)  
                else:
                    error_value = str(e)
                raise Warning(error_value)                
                
        return last_feed_submission_id

    @api.multi
    def switch_product_from_afn_to_mfn(self,instance,amazon_products):
        message=1
        msg=''
        msgs=''
        location_id=instance.warehouse_id.lot_stock_id.id
        for product in amazon_products:
            if instance.stock_field:
                stock=self.get_stock(product,product.product_id.id,location_id,instance.stock_field.id)
            else:
                stock=self.get_stock(product,product.product_id.id,location_id)
                
            msg=""" 
            <Message>
                <MessageID>%s</MessageID>
                <OperationType>Update</OperationType>
                <Inventory>
                    <SKU>%s</SKU>
                    <FulfillmentCenterID>DEFAULT</FulfillmentCenterID>
                    <Quantity>%s</Quantity>
                    <SwitchFulfillmentTo>MFN</SwitchFulfillmentTo>
                </Inventory>            
            </Message>            
            """%(message,int(stock),product.seller_sku)
            message=message+1
            msgs="%s %s"%(msgs,msg)
            
        data="%s %s </AmazonEnvelope>"%(self.get_switch_product_header(instance),msgs)
        last_feed_submission_id=self.switch_feed_submit(instance,data)  
        amazon_products.write({'fulfillment_by':'MFN','last_feed_submission_id':last_feed_submission_id})
        return True  
    @api.multi
    def switch_product_from_mfn_to_afn(self,instance,amazon_products):
        message=1
        msg=''
        msgs=''
        amazon_fulfillment_center_id="AMAZON_%s"%(instance.country_id.code)
        
        amazon_fulfillment_center_id=amazon_fulfillment_center_id.upper()
        for product in amazon_products:
            
            msg=""" 
            <Message>
                <MessageID>%s</MessageID>
                <OperationType>Update</OperationType>
                <Inventory>
                    <SKU>%s</SKU>
                    <FulfillmentCenterID>%s</FulfillmentCenterID>
                    <Lookup>FulfillmentNetwork</Lookup>
                    <SwitchFulfillmentTo>AFN</SwitchFulfillmentTo>
                </Inventory>            
            </Message>            
            """%(message,amazon_fulfillment_center_id,product.seller_sku)
            message=message+1
            msgs="%s %s"%(msgs,msg)
            
        data="%s %s </AmazonEnvelope>"%(self.get_switch_product_header(instance),msgs)
        last_feed_submission_id=self.switch_feed_submit(instance,data)  
        amazon_products.write({'fulfillment_by':'AFN','last_feed_submission_id':last_feed_submission_id})
        return True  

    @api.multi
    def get_product_prep_instructions(self, instance, amazon_products):
        """
            Get product Prep-Instructions from the amazon.
            @return: True
        """
        amazon_product_ept_obj = self.env['amazon.product.ept']
        prep_instruction_obj = self.env['prep.instruction']
        
        proxy_data = instance.seller_id.get_proxy_server()
        mws_obj = Amazon_api.InboundShipments_Extend(access_key=str(instance.access_key),secret_key=str(instance.secret_key),account_id=str(instance.merchant_id),region=instance.country_id.amazon_marketplace_code or instance.country_id.code,proxies=proxy_data)
        ship_to_country_code = instance.country_id.amazon_marketplace_code or instance.country_id.code
        seller_sku_list = []
        for amazon_product in amazon_products:
            if amazon_product.seller_sku:
                seller_sku_list.append(amazon_product.seller_sku)
        
        try:
            results = mws_obj.GetPrepInstructionsForSKU(seller_sku_list,ship_to_country_code)
            results = results.parsed
        except Exception as e:
            raise Warning(str(e))
        
        sku_prep_instructions_list = results.get("SKUPrepInstructionsList",{})
        sku_pre_instructions = sku_prep_instructions_list.get('SKUPrepInstructions',{})
        if not isinstance(sku_pre_instructions, list):
            sku_pre_instructions = [sku_pre_instructions]
            
        for sku_pre_instruction in sku_pre_instructions:
            seller_sku = sku_pre_instruction.get('SellerSKU',{}).get('value','')
            amazon_product_record = amazon_product_ept_obj.search([('seller_sku','=',seller_sku),('instance_id','=',instance.id),('fulfillment_by','=','AFN')],limit=1)
            if amazon_product_record:
                barcode_instruction=False
                barcode_instruction = sku_pre_instruction.get("BarcodeInstruction",{}).get("value","")
                if barcode_instruction == "RequiresFNSKULabel":
                    barcode_instruction = "AMAZON"
                elif barcode_instruction == "CanUseOriginalBarcode":
                    barcode_instruction = "SELLER"
                prep_instruction_list = sku_pre_instruction.get('PrepInstructionList',{})
                prep_instruction_value_list = prep_instruction_list.get('PrepInstruction',{})
                if not isinstance(prep_instruction_value_list, list):
                    prep_instruction_value_list = [prep_instruction_value_list]
                prep_instructions = prep_instruction_obj.search([('name','in',[prep_instruction_value_dict.get("value","") for prep_instruction_value_dict in prep_instruction_value_list])]) or []
                amazon_product_record.write({'barcode_instruction':barcode_instruction,'prep_instruction_ids':[(6,0,prep_instructions and prep_instructions.ids)]})
        return True
        
        
        
        
        
        
        