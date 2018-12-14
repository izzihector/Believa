from odoo import models, fields,api
# mapping invoice type to journal type

class amazon_transaction_type(models.Model):
    _inherit="amazon.transaction.type"
    

    is_reimbursement=fields.Boolean("REIMBURSEMENT ?",default=False)
