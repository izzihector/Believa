#!/usr/bin/python3
from odoo import models,fields,api

class ebay_log_book(models.Model):
    _name = "ebay.log.book"
    _description = "eBay Log Book"
    _order = 'id desc' 
    
    _ebay_operation_type_list = [
        ('import','Import'),
        ('export','Export'),
        ('update','Update'),
        ('relist','Relist'),
        ('cancel','Cancel')
    ]
    
    _ebay_application_type_list = [
        ('export_products','Export Products'),
        ('update_products','Update Products'),
        ('relist_products','Relist Products'),
        ('sync_products','Import/Sync Products'),
        ('cancel_listing','Cancel Product'),
        ('update_product_stock','Update Product Stock'),
        ('update_product_price','Update Product Price'),
        ('sales','Sales'),
        ('product','Product'),
        ('price','Price'),
        ('image','Image'),
        ('refund','Refund'),
        ('other','Others')
    ]
    
    name = fields.Char("Name")
    create_date = fields.Datetime("Create Date")
    instance_id=fields.Many2one('ebay.instance.ept',string="Instance")
    transaction_log_ids = fields.One2many("ebay.transaction.line","job_id",string="Log")
    skip_process = fields.Boolean("Process Is Skipped ?")
    application = fields.Selection(_ebay_application_type_list,string="Application")
    operation_type = fields.Selection(_ebay_operation_type_list,string="Operation Type")    
    message = fields.Text("Log Message")
    
    @api.model
    def create(self,vals):
        ebay_log_book_seq = self.env['ir.sequence'].next_by_code('ebay.log.book')
        vals.update({'name':ebay_log_book_seq})
        return super(ebay_log_book,self).create(vals)
    
class ebay_transaction_line(models.Model):
    _name = 'ebay.transaction.line'
    _description = "eBay Transaction Line"

    message = fields.Text("Message")
    model_id = fields.Many2one("ir.model",string="Model")
    res_id = fields.Integer("Record ID")
    job_id = fields.Many2one("ebay.log.book",string="Job")
    log_type = fields.Selection([('not_found','NOT FOUND'),
                                ('mismatch','MISMATCH'),
                                ('error','Error'),
                                ('warning','Warning')],'Log Type')
    action_type = fields.Selection([('create','Created New'),
                                    ('skip_line','Line Skipped'),
                                    ('terminate_process_with_log','Terminate Process With Log')], 'Action')
    operation_type = fields.Selection([('import','Import'),('export','Export')],string="Operation",related="job_id.operation_type",store=False,readonly=True)
    not_found_value = fields.Char('Not Founded Value')
    create_date = fields.Datetime("Created Date")
    ebay_order_ref=fields.Char("eBay Order Ref")
    
    @api.model
    def get_model_id(self, model_name):
        model = self.env['ir.model'].search([('model','=',model_name)])
        if model:
            return model.id
        return False   