"""
a ckass to provide us with certain verification methods
"""

from blocktools.hashing_functions import hash_string_256, hash_block
from wallet import Wallet

class Verifier:

    @staticmethod
    #checks if proof is valid based on the 2 starting characters of the hash
    def valid_proof(transactions, last_hash, proof):

        guess = (str([trans.to_ordered_dict() for trans in transactions]) + str(last_hash) + str(proof)).encode()
        guess_hash = hash_string_256(guess)

        return guess_hash[0:2] == '00' #true if it starts with 2 leading zeros
        
    @classmethod
    #checks if the chain is valid or not
    def verify_chain(cls, blockchain):
        for (index, block) in enumerate(blockchain):
            if index == 0:
                continue
            if block.previous_hash != hash_block(blockchain[index - 1]):
                return False
            if not cls.valid_proof(block.transactions[:-1], block.previous_hash, block.proof):
                print('Corrupt proof of work detected.')
                return False
        return True

    @staticmethod
    #check_funds is a boolean that indicates if we want to check the sender's funds or not (sufficiency)
    def verify_transaction(transaction, get_balance, check_funds=True):
        if check_funds:
            sender_balance = get_balance(transaction.sender)
            return sender_balance >= transaction.amount and Wallet.verify_transaction(transaction)
        else:
            return Wallet.verify_transaction(transaction)

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        return all([cls.verify_transaction(trans, get_balance, False) for trans in open_transactions])