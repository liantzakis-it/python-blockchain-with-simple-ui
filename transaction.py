"""
a simple class representing a transaction
inherits printable for printing reasons
"""

from blocktools.printable import Printable
from collections import OrderedDict


class Transaction(Printable):
    def __init__(self, sender, recipient, signature, amount):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.signature = signature #the signature is created in the wallet.py file

    #transaction to dictionary
    def to_ordered_dict(self):
        return OrderedDict([('sender', self.sender), ('recipient', self.recipient), ('amount', self.amount)])
