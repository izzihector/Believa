#!/usr/bin/python3
from odoo import models, fields,api
from odoo.exceptions import Warning
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading

class ebay_category(models.Model):
    _name="ebay.category.master.ept"
    _description = "eBay Master Category"
    
    @api.one
    def _complete_name(self):        
        """ 
            Forms complete name of location from parent location to child location.
        """
        for m in self:
            names = [m.name]            
            parent = m.ebay_category_parent_id
            parent = True
            if m.parent_id:
                rec=m.parent_id
            else:
                parent=False
            while parent:                
                names.append(rec.name)
                if not rec.parent_id:
                    parent = False
                    continue
                rec=rec.parent_id
                parent = rec.ebay_category_parent_id
            m.ept_complete_name = '/'.join(reversed(names))


    name = fields.Char(size=256, string='Category Name', required=True)
    ept_complete_name = fields.Char(compute=_complete_name, string='Name',store=False)
    ebay_category_id = fields.Char(string='Category ID')    
    parent_id=fields.Many2one("ebay.category.master.ept","Parent")
    category_level = fields.Integer(string='Category Level')
    ebay_category_parent_id = fields.Char(string='Parent Category')
    site_id = fields.Many2one('ebay.site.details', string='Site')
    active = fields.Boolean("Active",default=True)
    attribute_ids = fields.One2many('ebay.attribute.master', 'categ_id', 'Attributes')
    instance_id=fields.Many2one("ebay.instance.ept",string="Instance")
    item_specifics = fields.Boolean("Item Specific Enabled",default=False)
    condition_enabled = fields.Boolean("Condition Enabled",default=False)
    variation_enabled=fields.Boolean("VariationsEnabled",default=False)
    leaf_category = fields.Boolean("Leaf Category",default=False)
    ebay_condition_ids = fields.One2many("ebay.condition.ept","category_id","eBay Condition")

    auto_pay_enabled = fields.Boolean("Auto Pay Enable",default=False)
    set_return_policy = fields.Boolean("Return Policy",default=False)    
    best_offer_enabled = fields.Boolean("Best Offer Enabled",default=False)    
    galary_plus_enabled = fields.Boolean("FreeGalleryPlusEnabled",default=False)
    offer_accept_enabled = fields.Boolean("BestOfferAutoAcceptEnabled",default=False)                    
    handling_time_enabled=fields.Boolean("HandlingTimeEnabled",default=False)    
    
    paypal_required=fields.Boolean('PayPalRequired',default=False)
    digital_good_delivery_enabled=fields.Boolean("DigitalGoodDeliveryEnabled",default=False)
    is_store_category=fields.Boolean("Is Store Category ?",default=False)
    odoo_product_category = fields.Many2one("product.category",string="Odoo Category",help="Select odoo product category.")
    
    @api.multi
    def import_store_category(self,instances,level_limit=0,only_leaf_categories=True):
        for instance in instances:
            cat = {}
            site_id = instance.site_id and instance.site_id.site_id or False
            
            api = instance.get_trading_api_object()
            para = {'DetailLevel': 'ReturnAll'}
            if level_limit>0:
                para.update({'LevelLimit':level_limit})
            if site_id:                
                para.update({'CategorySiteID':site_id})
            if only_leaf_categories:
                para.update({'ViewAllNodes':'false'})
            else:
                para.update({'ViewAllNodes':'true'})
            try:
                api.execute('GetStore', para)
                cat = api.response.dict()
            except Exception as e :
                raise Warning(('%s')%(str(e)))
            
            categories = []
            custom_category=cat.get('Store',{}).get('CustomCategories',{})
            if custom_category and custom_category.get('CustomCategory',[]):
                if isinstance(custom_category.get('CustomCategory',[]),list):
                    categories = custom_category.get('CustomCategory',[])
                else:
                    categories = [custom_category.get('CustomCategory',[])]            
            for categ in categories:
                name = categ.get('Name')
                categoryid = categ.get('CategoryID')
                categ_record = self.search([('ebay_category_id','=',categoryid),('instance_id','=',instance.id)],limit=1) 
                if categ_record:
                    categ_record.write({'name':name})           
                else:
                    categ_record=self.create({
                        'name':name,
                        'ebay_category_id':categoryid,
                        'site_id':instance.site_id and instance.site_id.id or False,
                        'instance_id':instance.id,
                        'is_store_category':True
                    })
                child_categs=categ.get('ChildCategory',[])
                if not isinstance(child_categs,list):
                    child_categs=[child_categs]
                
                for child in child_categs:
                    name = child.get('Name')
                    categoryid = child.get('CategoryID')

                    child_record = self.search([('ebay_category_id','=',categoryid),('site_id','=',instance.site_id.id),('is_store_category','=',True),('instance_id','=',instance.id)],limit=1) 
                    if child_record:
                        child_record.write({'name':name})           
                    else:
                        child_record = self.create({
                            'name':name,
                            'ebay_category_id':categoryid,
                            'site_id':instance.site_id and instance.site_id.id or False,
                            'instance_id':instance.id,
                            'is_store_category':True,
                            'ebay_category_parent_id':categ_record.ebay_category_id,
                            'parent_id':categ_record.id
                        })
                        
                    #Added By Dimpal 25/12/2017
                    sub_child_categs = child.get('ChildCategory',[])
                    if not isinstance(sub_child_categs, list):
                        sub_child_categs = [sub_child_categs]
                    for sub_child in sub_child_categs:
                        name = sub_child.get('Name')
                        categoryid = sub_child.get('CategoryID')
                         
                        sub_child_record = self.search([('ebay_category_id','=',categoryid),('site_id','=',instance.site_id.id),('is_store_category','=',True),('instance_id','=',instance.id)],limit=1)
                        if sub_child_record:
                            sub_child_record.write({'name' : name})
                        else:
                            self.create({
                                'name':name,
                                'ebay_category_id':categoryid,
                                'site_id':instance.site_id and instance.site_id.id or False,
                                'instance_id':instance.id,
                                'is_store_category':True,
                                'ebay_category_parent_id':child_record.ebay_category_id,
                                'parent_id':child_record.id
                            })          
            self._cr.commit()
        return True
    
    @api.multi
    def import_category(self,instances,level_limit=0,only_leaf_categories=True,is_import_get_item_condition=False):
        for instance in instances:
            cat = {}
            site_id = instance.site_id and instance.site_id.site_id or False 
            api = instance.get_trading_api_object()
            para = {'DetailLevel': 'ReturnAll'}
            if level_limit>0:
                para.update({'LevelLimit':level_limit})
            if site_id:                
                para.update({'CategorySiteID':site_id})
            if only_leaf_categories:
                para.update({'ViewAllNodes':'false'})
            else:
                para.update({'ViewAllNodes':'true'})
            try:
                api.execute('GetCategories', para)
                cat = api.response.dict()
            except Exception as e:
                raise Warning(('%s')%(str(e)))
            categories = []
            if cat.get('CategoryArray',{}) and cat['CategoryArray'].get('Category',[]):
                categories = cat['CategoryArray']['Category'] #returns list of dictionary 
            if isinstance(categories,dict): 
                categories=[categories]
            
            for categ in categories:
                name = categ.get('CategoryName')
                CategoryID = categ.get('CategoryID')
                AutoPayEnabled = categ.get('AutoPayEnabled')
                CategoryLevel = categ.get('CategoryLevel')
                CategoryParentID = categ.get('CategoryParentID')
                LSD = categ.get('LSD')
                LeafCategory = categ.get('LeafCategory',"false")
                BestOfferEnabled = categ.get('BestOfferEnabled',"false")
                
                if LeafCategory == 'true':
                    LeafCategory = True
                else:
                    LeafCategory = False
                if LSD == 'true':
                    LSD = True
                else:
                    LSD = False
                if BestOfferEnabled == 'true':
                    BestOfferEnabled = True
                else:
                    BestOfferEnabled = False
                if CategoryID == CategoryParentID:
                        CategoryParentID =False
                categs = self.search([('ebay_category_id','=',CategoryID),('site_id','=',instance.site_id.id)],limit=1)            
                parent=self.search([('ebay_category_id','=',CategoryParentID),('site_id','=',instance.site_id.id)],limit=1)
                if not categs:
                    self.create({
                        'name':name,
                        'ebay_category_id':CategoryID,
                        'site_id':instance.site_id and instance.site_id.id or False,
                        'leaf_category':LeafCategory,
                        'ebay_category_parent_id':CategoryParentID,
                        'category_level':CategoryLevel,
                        'auto_pay_enabled':AutoPayEnabled,
                        'best_offer_enabled':BestOfferEnabled,
                        'parent_id':parent and parent.ids[0] or False
                    })
                else:
                    categs.write({
                        'name':name,
                        'ebay_category_id':CategoryID,
                        'site_id':instance.site_id and instance.site_id.id or False,
                        'leaf_category':LeafCategory,
                        'ebay_category_parent_id':CategoryParentID,
                        'category_level':CategoryLevel,
                        'auto_pay_enabled':AutoPayEnabled,
                        'best_offer_enabled':BestOfferEnabled,
                        'parent_id':parent and parent.ids[0] or False
                    })
                if is_import_get_item_condition:
                    """
                        :Function get_item_conditions: This function call to category wise import get item condition.   
                    """
                    self.get_item_conditions(import_category_id=CategoryID)
                    
            return True
        
    @api.multi
    def get_attributes(self, max_name_levels, max_value_per_name):
        attribute_master_obj=self.env['ebay.attribute.master']
        attribute_value_obj=self.env['ebay.attribute.value']
        instance_obj=self.env['ebay.instance.ept']
        
        results = False
        category = self
        category_code = category.ebay_category_id

        instances = instance_obj.search([('site_id','=',category.site_id.id),('state','=','confirmed')])
        if not instances:
            return True
        instance = instances[0] 
        if category_code:
            api = instance.get_trading_api_object()
            para = {'CategoryID':category.ebay_category_id}
            if max_name_levels :
                para.update({'MaxNames' : max_name_levels})
            if max_value_per_name :
                para.update({'MaxValuesPerName' : max_value_per_name})
            results = api.execute('GetCategorySpecifics', para)
            list_of_result=[]
            if isinstance(results.dict().get('Recommendations',{}).get('NameRecommendation',[]),list):
                list_of_result=results.dict().get('Recommendations',{}).get('NameRecommendation',[])
            else:
                list_of_result.append(results.dict().get('Recommendations',{}).get('NameRecommendation',[]))
            for line in list_of_result:                
                attribute_name=line.get('Name')
                attribute_record=attribute_master_obj.search([('name','=',attribute_name),('categ_id','=',category.id)])
                if not attribute_record:
                    attribute_record=attribute_master_obj.create({'name':attribute_name,'categ_id':category.id})
                list_of_value=[]
                if isinstance(line.get('ValueRecommendation',[]),list):
                    list_of_value=line.get('ValueRecommendation',[])
                else:
                    list_of_value.append(line.get('ValueRecommendation',{}))
                for value in list_of_value:                                        
                    attribute_value=attribute_value_obj.search([('name','=',value.get('Value')),('attribute_id','=',attribute_record.id)])
                    if not attribute_value:
                        attribute_value_obj.create({'name':value.get('Value'),'attribute_id':attribute_record.id})
            """for line in list_of_result:
                child_categs=self.search([('parent_id','=',category.id)])
                while child_categs:
                    for child in child_categs:
                        child_record=attribute_master_obj.search([('name','=',attribute_name),('categ_id','=',child.id)])
                        if not child_record:
                            child_record=attribute_master_obj.create({'name':attribute_name,'categ_id':child.id})
                        for value in line.get('ValueRecommendation',[]):                                        
                            child_value=attribute_value_obj.search([('name','=',value.get('Value')),('att_master_id','=',child_record.id)])
                            if not child_value:
                                attribute_value_obj.create({'name':value.get('Value'),'att_master_id':child_record.id})
                        
                    child_categs=self.search([('parent_id','in',child_categs.ids)])"""                                                        
                
        return True
    
    @api.multi
    def get_item_conditions(self, import_category_id=None):
        condition_obj=self.env['ebay.condition.ept']
        instance_obj=self.env['ebay.instance.ept']
        category = None
    
        if not self and import_category_id:
            category = self.search([('ebay_category_id','=',import_category_id)],limit=1)
        else:   
            category = self
            
        category_code = category.ebay_category_id
        instances = instance_obj.search([('site_id','=',category.site_id.id),('state','=','confirmed')])
        if not instances:
            return True
        instance = instances[0] 
        if category_code:
            api = instance.get_trading_api_object()
            
            para = {'ViewAllNodes': True, 'DetailLevel': 'ReturnAll', 'AllFeaturesForCategory': True, 'CategoryID': category.ebay_category_id}
            api.execute('GetCategoryFeatures', para)

            results1 = api.response.dict()
            if results1:
                category_default = results1.get('SiteDefaults',{})
                category_val = results1.get('Category',{})
                
                item_sp_en = category_val.get('ItemSpecificsEnabled',False) or category_default.get('ItemSpecificsEnabled',False)
                condition_enabled = category_val.get('ConditionEnabled',False) or category_default.get('ConditionEnabled',False)
                galary_plus_enabled=category_val.get('FreeGalleryPlusEnabled',False) or category_default.get('FreeGalleryPlusEnabled',False)
                offer_accept_enabled=category_val.get('BestOfferAutoAcceptEnabled',False) or category_default.get('BestOfferAutoAcceptEnabled',False)
                set_return_policy=category_val.get("ReturnPolicyEnabled",False) or category_default.get('ReturnPolicyEnabled',False)
                digital_good_delivery_enabled = category_val.get('DigitalGoodDeliveryEnabled',False) or category_default.get('DigitalGoodDeliveryEnabled',False)
                paypal_required=category_val.get("PayPalRequired",False) or category_default.get('PayPalRequired',False)
                variation_enabled=category_val.get("VariationsEnabled",False) or category_default.get('VariationsEnabled',False)
                handling_time_enabled=category_val.get("HandlingTimeEnabled",False) or category_default.get('HandlingTimeEnabled',False)
                
                offer_accept_enabled=False if offer_accept_enabled=='false' else True
                galary_plus_enabled=False if galary_plus_enabled=='false' else True
                set_return_policy=False if set_return_policy=='false' else True
                item_sp_en = True if item_sp_en == 'Enabled' else False
                digital_good_delivery_enabled=False if digital_good_delivery_enabled== 'false' else True
                condition_enabled =True  if condition_enabled == 'Required' else False

                paypal_required=False if paypal_required=='false' else True
                variation_enabled=True if variation_enabled=='true' else False
                handling_time_enabled=True if handling_time_enabled=='true' else False
                category.write({'item_specifics':item_sp_en,'condition_enabled':condition_enabled,
                                'offer_accept_enabled':offer_accept_enabled,'galary_plus_enabled':galary_plus_enabled,
                                'set_return_policy':set_return_policy,'variation_enabled':variation_enabled,'handling_time_enabled':handling_time_enabled,
                                'digital_good_delivery_enabled':digital_good_delivery_enabled,'paypal_required':paypal_required                               
                                })
                
                
                condition_values = category_val.get('ConditionValues',False)
                if condition_values:
                    if isinstance(condition_values.get('Condition',[]),dict):
                        condition_values=[condition_values.get('Condition',[])]
                    else:
                        condition_values=condition_values.get('Condition',[])
                        
                    for each_val in condition_values:
                        condition_name = each_val.get('DisplayName',False)
                        condition_id = each_val.get('ID',False)
                        if condition_name and condition_id:
                            search_conditions = condition_obj.search([('condition_id','=',condition_id),('category_id','=',category.id),('name','=',condition_name)])
                            if not search_conditions:
                                condition_vals = {'name':condition_name,'condition_id':condition_id,'category_id':category.id}
                                condition_obj.create(condition_vals)
                    
                    if not category.leaf_category and category.ebay_condition_ids:
                        child_categ = self.env['ebay.category.master.ept'].search([('parent_id','=',category.id)])
                        while True:
                            for child in child_categ:
                                for condition in  category.ebay_condition_ids:
                                    search_conditions = condition_obj.search([('condition_id','=',condition.condition_id),('category_id','=',child.id),('name','=',condition.name)])                                                                
                                    if not search_conditions:
                                        condition_vals = {'name':condition.name,'condition_id':condition.condition_id,'category_id':child.id}
                            child_categ = self.env['ebay.category.master.ept'].search([('parent_id','in',child_categ.ids)]) 
                            if not child_categ:
                                break                                                                
        return True
             


