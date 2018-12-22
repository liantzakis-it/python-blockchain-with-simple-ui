"""
simple class to represent a block of our blockchain
inherits Printable
"""

from blocktools.printable import Printable
from time import time


class Block(Printable):

    def __init__(self, index, previous_hash, transactions, proof, time=time()):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.proof = proof
        self.timestamp = time


