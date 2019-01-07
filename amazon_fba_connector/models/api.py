from ...amazon_ept.amazon_emipro_api.mws import InboundShipments, OutboundShipments, DictWrapper
import time
# import sys
class OutboundShipments_Extend(OutboundShipments):
    URI = "/FulfillmentOutboundShipment/2010-10-01"
    VERSION = '2010-10-01'
    NS = '{http://mws.amazonaws.com/FulfillmentOutboundShipment/2010-10-01}'
    
    def GetPackageTrackingDetails(self,package_number):
        data={}
        data.update({'Action':'GetPackageTrackingDetails','PackageNumber':package_number})
        return self.make_request(data)
    
    def ListAllFulfillmentOrders(self,start_date_time=False):
        data={}
        data.update({'Action':'ListAllFulfillmentOrders'})
        if start_date_time:
            data.update({'QueryStartDateTime':start_date_time})
        return self.make_request(data)

    def ListAllFulfillmentOrdersByNextToken(self,token):
        data={}
        data.update({'Action':'ListAllFulfillmentOrdersByNextToken','NextToken':token})
        return self.make_request(data)

    def GetFullfillmentOrder(self,order):
        data={}
        data.update({'Action':'GetFulfillmentOrder','SellerFulfillmentOrderId':order.name})
        return self.make_request(data)
        
    
    def CancelFulfillmentOrder(self,order):
        data={}
        data.update({'Action':'CancelFulfillmentOrder','SellerFulfillmentOrderId':order.name})
        return self.make_request(data)
    def get_data(self,order):
        currency_code=order.amz_instance_id.company_id.currency_id.name 

        data={}
        data.update({
                    'SellerFulfillmentOrderId':order.name,
                    'DisplayableOrderId':order.amazon_reference,
                    'ShippingSpeedCategory':order.amz_shipment_service_level_category,                     
                     })
        if order.amz_delivery_start_time and order.amz_delivery_end_time:
            start_date = time.strptime(order.amz_delivery_start_time, "%Y-%m-%d %H:%M:%S")
            start_date = time.strftime("%Y-%m-%dT%H:%M:%S",start_date)
            start_date = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(start_date,"%Y-%m-%dT%H:%M:%S"))))
            start_date = str(start_date)+'Z'

            end_date = time.strptime(order.amz_delivery_end_time, "%Y-%m-%d %H:%M:%S")
            end_date = time.strftime("%Y-%m-%dT%H:%M:%S",end_date)
            end_date = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(time.strptime(end_date,"%Y-%m-%dT%H:%M:%S"))))
            end_date = str(start_date)+'Z'

            data.update({
                         'DeliveryWindow.StartDateTime':start_date,
                         'DeliveryWindow.EndDateTime':end_date,
                         })

        data.update({
                'DestinationAddress.Name':str(order.partner_shipping_id.name),
                'DestinationAddress.Line1':str(order.partner_shipping_id.street or ''),
                'DestinationAddress.Line2':str(order.partner_shipping_id.street2 or ''),
                'DestinationAddress.CountryCode':str(order.partner_shipping_id.country_id.code or ''),
                'DestinationAddress.City':str(order.partner_shipping_id.city or ''),                
                'DestinationAddress.StateOrProvinceCode':str(order.partner_shipping_id.state_id and order.partner_shipping_id.state_id.code or ''),
                'DestinationAddress.PostalCode':str(order.partner_shipping_id.zip or ''),                
                })
        if order.note:
            data.update({'DisplayableOrderComment':str(order.note)})
        data.update({
                     'DisplayableOrderDateTime':order.amz_displayable_date_time,
                     'FulfillmentAction':str(order.amz_fulfillment_action),
                     
                     })   
        count=1
        for line in order.order_line:
            if line.product_id and line.product_id.type=='service':
                continue
            key="Items.member.%s.DisplayableComment"%(count)
            line.amz_displayable_comment and data.update({key:str(line.amz_displayable_comment)}) 
            key="Items.member.%s.GiftMessage"%(count)
            line.amz_gift_message and  data.update({key:str(line.amz_gift_message)}) 
            key="Items.member.%s.PerUnitDeclaredValue.CurrencyCode"%(count)
            line.amz_per_unit_declared_value and data.update({key:(currency_code)})
            key="Items.member.%s.PerUnitDeclaredValue"%(count)
            line.amz_per_unit_declared_value and data.update({key:(str(line.amz_per_unit_declared_value))})
            key="Items.member.%s.Quantity"%(count)               
            data.update({key:str(int(line.product_uom_qty))})
            key="Items.member.%s.SellerSKU"%(count)               
            data.update({key:str(line.amazon_product_id.seller_sku)})
            key="Items.member.%s.SellerFulfillmentOrderItemId"%(count)
            data.update({key:str(line.amazon_product_id.seller_sku)})
            count=count+1
        if order.notify_by_email:
            count=1
            for follower in order.message_follower_ids:
                if follower.email:
                    key="NotificationEmailList.member.%s"%(count) 
                    data.update({'key':str(follower.email)})
                    count=count+1
        return data
        
    def CreateFulfillmentOrder(self,order):
        data=self.get_data(order)
        data.update({
                'Action':'CreateFulfillmentOrder',
             })

        return self.make_request(data)
    
    def UpdateFulfillmentOrder(self,order):
        partner=order.partner_shipping_id
        currency_code=partner and partner.company_id and partner.company_id.currency_id.name or False
        currency_code=not currency_code and order.amz_instance_id.company_id.currency_id.name 
        data=self.get_data(order)
        data.update({
                'Action':'UpdateFulfillmentOrder',
             })
        return self.make_request(data)
        
    
               
    
class InboundShipments_Extend(InboundShipments):
    URI = "/FulfillmentInboundShipment/2010-10-01"
    VERSION = '2010-10-01'
    NS = '{http://mws.amazonaws.com/FulfillmentInboundShipment/2010-10-01}'
    
    def create_inbound_shipment_plan(self,name,addressline1='',addressline2='',city='',stateOrprovincecode='',postalcode='',
                                         countrycode='',ship_to_countrycode=None,labelpreppreference='SELLER_LABEL',sku_qty_dict={},sku_prep_details_dict={}):
        data = {"Action" : "CreateInboundShipmentPlan",
                "ShipFromAddress.Name": str(name),
                "ShipFromAddress.AddressLine1" : str(addressline1),
                "ShipFromAddress.AddressLine2" : str(addressline2),
                "ShipFromAddress.City" : str(city),
                "ShipFromAddress.StateOrProvinceCode" : str(stateOrprovincecode),
                "ShipFromAddress.PostalCode" : postalcode,
                "ShipFromAddress.CountryCode" : countrycode,
                "LabelPrepPreference" : labelpreppreference
            }
        if ship_to_countrycode:
            data.update({"ShipToCountryCode":ship_to_countrycode})
            
        count = 1                            
        for sku,list_quantity in sku_qty_dict.items():
            data.update({'InboundShipmentPlanRequestItems.member.%s.SellerSKU'%(str(count)) : sku})
            data.update({'InboundShipmentPlanRequestItems.member.%s.Quantity'%(str(count)) : list_quantity[0]})
            data.update({'InboundShipmentPlanRequestItems.member.%s.QuantityInCase'%(str(count)) : list_quantity[1]})
            
            if sku_prep_details_dict and sku_prep_details_dict.get(sku):
                prep_owner = sku_prep_details_dict.get(sku,{}).get("prep_owner","")
                prep_details_list = sku_prep_details_dict.get(sku,{}).get("prep_instuction","") or []
                for prep_detail_count,prep_detail in enumerate(prep_details_list,1):
                    data.update({'InboundShipmentPlanRequestItems.member.%s.PrepDetailsList.member.%s.PrepOwner'%(str(count),str(prep_detail_count)): prep_owner})
                    data.update({'InboundShipmentPlanRequestItems.member.%s.PrepDetailsList.member.%s.PrepInstruction'%(str(count),str(prep_detail_count)): prep_detail})
            count +=1            
        return self.make_request(data)
                
    def update_inbound_shipment(self,shipment_name,shipment_id,dest_fulfill_id,name,
                                addressline1='',addressline2='',city='',stateOrprovincecode='',
                                postalcode='',countrycode='',labelpreppreference='SELLER_LABEL',
                                shipment_status='WORKING',inbound_box_content_status='NONE',sku_qty_dict={},is_are_cases_required=False,sku_prep_details_dict={}):
        
        data = {"Action" : "UpdateInboundShipment",
                "ShipmentId":shipment_id,
                "InboundShipmentHeader.ShipmentName":shipment_name,
                "InboundShipmentHeader.ShipFromAddress.Name": str(name),
                "InboundShipmentHeader.ShipFromAddress.AddressLine1" : str(addressline1),
                "InboundShipmentHeader.ShipFromAddress.AddressLine2" : str(addressline2),
                "InboundShipmentHeader.ShipFromAddress.City" : str(city),
                "InboundShipmentHeader.ShipFromAddress.StateOrProvinceCode" : stateOrprovincecode,
                "InboundShipmentHeader.ShipFromAddress.PostalCode" : postalcode,
                "InboundShipmentHeader.ShipFromAddress.CountryCode" : countrycode,
                "InboundShipmentHeader.DestinationFulfillmentCenterId": dest_fulfill_id,
                "InboundShipmentHeader.ShipmentStatus" : shipment_status,
                "InboundShipmentHeader.IntendedBoxContentsSource":inbound_box_content_status,
                "InboundShipmentHeader.LabelPrepPreference" : labelpreppreference,
                "InboundShipmentHeader.AreCasesRequired" : str(is_are_cases_required).lower(),                 
               }
        
        count = 1                            
        for sku,list_quantity in sku_qty_dict.items():
            data.update({'InboundShipmentItems.member.%s.SellerSKU'%(str(count)) : sku})
            if isinstance(list_quantity,list):
                data.update({'InboundShipmentItems.member.%s.QuantityShipped'%(str(count)) : list_quantity[0]})
                data.update({'InboundShipmentItems.member.%s.QuantityInCase'%(str(count)) : list_quantity[1]})
            else:
                data.update({'InboundShipmentItems.member.%s.QuantityShipped'%(str(count)) : list_quantity})                
            if sku_prep_details_dict and sku_prep_details_dict.get(sku):
                prep_owner = sku_prep_details_dict.get(sku,{}).get("prep_owner","")
                prep_details_list = sku_prep_details_dict.get(sku,{}).get("prep_instuction","") or []
                for prep_detail_count,prep_detail in enumerate(prep_details_list,1):
                    data.update({'InboundShipmentItems.member.%s.PrepDetailsList.member.%s.PrepOwner'%(str(count),str(prep_detail_count)): prep_owner})
                    data.update({'InboundShipmentItems.member.%s.PrepDetailsList.member.%s.PrepInstruction'%(str(count),str(prep_detail_count)): prep_detail})
            count +=1
        return self.make_request(data)        

    
    def create_inbound_shipment(self,shipment_name,shipment_id,dest_fulfill_id,name,
                                addressline1='',addressline2='',city='',stateOrprovincecode='',
                                postalcode='',countrycode='',labelpreppreference='SELLER_LABEL',
                                shipment_status='WORKING',inbound_box_content_status='NONE',sku_qty_dict={},is_are_cases_required=False,sku_prep_details_dict={}):
        
        data = {"Action" : "CreateInboundShipment",
                "ShipmentId":shipment_id,
                "InboundShipmentHeader.ShipmentName":shipment_name,
                "InboundShipmentHeader.ShipFromAddress.Name": str(name),
                "InboundShipmentHeader.ShipFromAddress.AddressLine1" : str(addressline1),
                "InboundShipmentHeader.ShipFromAddress.AddressLine2" : str(addressline2),
                "InboundShipmentHeader.ShipFromAddress.City" : str(city),
                "InboundShipmentHeader.ShipFromAddress.StateOrProvinceCode" : stateOrprovincecode,
                "InboundShipmentHeader.ShipFromAddress.PostalCode" : postalcode,
                "InboundShipmentHeader.ShipFromAddress.CountryCode" : countrycode,
                "InboundShipmentHeader.DestinationFulfillmentCenterId": dest_fulfill_id,
                "InboundShipmentHeader.ShipmentStatus" : shipment_status,
                "InboundShipmentHeader.IntendedBoxContentsSource":inbound_box_content_status,
                "InboundShipmentHeader.LabelPrepPreference" : labelpreppreference,
                "InboundShipmentHeader.AreCasesRequired" : str(is_are_cases_required).lower(),              
               }
        
        count = 1                            
        for sku,list_quantity in sku_qty_dict.items():
            data.update({'InboundShipmentItems.member.%s.SellerSKU'%(str(count)) : str(sku)})
            data.update({'InboundShipmentItems.member.%s.QuantityShipped'%(str(count)) : list_quantity[0]})
            data.update({'InboundShipmentItems.member.%s.QuantityInCase'%(str(count)) : list_quantity[1]})
            
            if sku_prep_details_dict and sku_prep_details_dict.get(sku):
                prep_owner = sku_prep_details_dict.get(sku,{}).get("prep_owner","")
                prep_details_list = sku_prep_details_dict.get(sku,{}).get("prep_instuction","") or []
                for prep_detail_count,prep_detail in enumerate(prep_details_list,1):
                    data.update({'InboundShipmentItems.member.%s.PrepDetailsList.member.%s.PrepOwner'%(str(count),str(prep_detail_count)): prep_owner})
                    data.update({'InboundShipmentItems.member.%s.PrepDetailsList.member.%s.PrepInstruction'%(str(count),str(prep_detail_count)): prep_detail})
            count +=1
        return self.make_request(data)        
        
    def GetPrepInstructionsForSKU(self,sku_list,ship_country_code):
        data = {"Action" : "GetPrepInstructionsForSKU",
                "ShipToCountryCode":ship_country_code
                }
        data.update(self.enumerate_param('SellerSKUList.Id.', sku_list))
        return self.make_request(data)

    def GetPrepInstructionsForASIN(self,asin_list,ship_country_code):
        data = {"Action" : "GetPrepInstructionsForASIN",
                "ShipToCountryCode":ship_country_code
                }
        data.update(self.enumerate_param('ASINList.Id.', asin_list))
        return self.make_request(data)
        
    # Need Improvement, still not completed
    def put_transport_content(self,data={}):
        data.update({
                "Action" : "PutTransportContent",
                })
        return self.make_request(data)
    
    #Only use for Amazon-partnered carrier program
    def EstimateTransportRequest(self,shipment_id):
        data = {
                "Action" : "EstimateTransportRequest",
                "ShipmentId" : shipment_id
                }
        return self.make_request(data)

    def GetTransportContent(self,shipment_id):
        data ={
               "Action" : "GetTransportContent",
               "ShipmentId" : shipment_id
               }
        return self.make_request(data)
    
    #Only use for Amazon-partnered carrier program
    def ConfirmTransportRequest(self,shipment_id):
        data = {
                "Action" : "ConfirmTransportRequest",
                "ShipmentId" : shipment_id
                }
        return self.make_request(data)
    
    #Only use for Amazon-partnered carrier program
    def VoidTransportRequest(self,shipment_id):
        data = {
                "Action" : "VoidTransportRequest",
                "ShipmentId" : shipment_id
                }
        return self.make_request(data)
       
    def GetPackageLabels(self,shipment_id,page_type,number_of_packages=0):
        data ={
               "Action" : "GetPackageLabels",
               "ShipmentId" : shipment_id,
               "PageType" : page_type,
               }
        if number_of_packages:
            data.update({"NumberOfPackages":number_of_packages})
            
        return self.make_request(data)
    
    def GetPalletLabels(self,shipment_id,page_type,number_of_pallet=0):
        data ={
               "Action" : "GetPalletLabels",
               "ShipmentId" : shipment_id,
               "PageType" : page_type,
               }
        if number_of_pallet:
            data.update({"NumberOfPallets":number_of_pallet})
            
        return self.make_request(data)

    def GetUniquePackageLabels(self,shipment_id,page_type,list_box_no):
        data ={
               "Action" : "GetUniquePackageLabels",
               "ShipmentId" : shipment_id,
               "PageType" : page_type,
               }
        count=1
        for box_no in list_box_no:
            data.update({'PackageLabelsToPrint.member.%s'%(count):box_no})
            count=count+1
        return self.make_request(data)

    #Only use for Amazon-partnered carrier program
    # Return PdfDocument
    def GetBillOfLading(self,shipment_id):
        data ={
               "Action" : "GetBillOfLading",
               "ShipmentId" : shipment_id
               }
        return self.make_request(data)

    def ListInboundShipments(self,ship_status_list=[],ship_id_list=[],
                             last_updated_after=None,last_updated_before=None):
        if not ship_status_list and not ship_id_list:
            raise Warning("You must need to provide either shipment status list or shipment IDs or Both")
        
        data ={
               "Action" : "ListInboundShipments",
               }
        if ship_status_list:
            data.update(self.enumerate_param('ShipmentStatusList.member.', ship_status_list))
        if ship_id_list:
            data.update(self.enumerate_param('ShipmentIdList.member.', ship_id_list))
                
        return self.make_request(data)
        
    def ListInboundShipmentsByNextToken(self,next_token):
        data ={
               "Action" : "ListInboundShipmentsByNextToken",
               "NextToken" : next_token
               }
        return self.make_request(data)
    
    def ListInboundShipmentItems(self,ship_id='',
                             last_updated_after=None,last_updated_before=None):
        if not ship_id and not (last_updated_after and last_updated_before):
            raise Warning("You must need to provide either shipment ID or LastUpdatedAfter and LastUpdatedBefore value")
        
        data ={
               "Action" : "ListInboundShipmentItems",
               }
        if ship_id:
            data.update({'ShipmentId':ship_id})
            
        if last_updated_after and last_updated_before:
            data.update({'LastUpdatedAfter':last_updated_after,'LastUpdatedBefore':last_updated_before})
                
        return self.make_request(data)
    
    def ListInboundShipmentItemsByNextToken(self,next_token):
        data ={
               "Action" : "ListInboundShipmentItemsByNextToken",
               "NextToken" : next_token
               }
        return self.make_request(data)