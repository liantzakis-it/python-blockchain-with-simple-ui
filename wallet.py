"""
simple class representing a user's wallet
Users will be able to create a wallet, load a wallet, and also sign transactions using their keys
"""

import binascii
import Crypto.Random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5


class Wallet:
    #initialize as None
    def __init__(self, node_id):
        self.private_key = None
        self.public_key = None
        self.node_id = node_id


    #FUNCTIONS RELEVANT TO KEYS SECTION

    #key pair generator using RSA
    def generate_keys(self):
        private_key = RSA.generate(1024, Crypto.Random.new().read)
        public_key = private_key.publickey()
        #DER binary encoding
        return (binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'), binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii'))

    def create_keys(self):
        #create the pair (basically creating a wallet)
        private_key, public_key = self.generate_keys()
        self.private_key = private_key
        self.public_key = public_key

    def save_keys(self):
        if self.public_key != None and self.private_key != None:
            try:
                with open('wallet-{}.txt'.format(self.node_id), mode='w') as fi:
                    fi.write(self.public_key)
                    fi.write('\n')
                    fi.write(self.private_key)
                return True
            #handle exceptions
            except (IOError, IndexError):
                print('An error occurred while saving your wallet.')
                return False

    def load_keys(self):
        try:
            with open('wallet-{}.txt'.format(self.node_id), mode='r') as fi:
                keys = fi.readlines()
                public_key = keys[0][:-1]
                private_key = keys[1]
                self.public_key = public_key
                self.private_key = private_key
            return True
        except (IOError, IndexError):
            print('An error occurred while loading your wallet.')
            return False


    #FUNCTIONS RELEVANT TO SIGNATURES SECTION


    def sign_transaction(self, sender, recipient, amount):
        signer = PKCS1_v1_5.new(RSA.importKey(binascii.unhexlify(self.private_key)))
        data_hash = SHA256.new((str(sender) + str(recipient) + str(amount)).encode('utf8'))
        signature = signer.sign(data_hash)
        return binascii.hexlify(signature).decode('ascii')

    @staticmethod
    #verifies the signature of a transaction
    def verify_transaction(transaction):
        public_key = RSA.importKey(binascii.unhexlify(transaction.sender))
        verifier = PKCS1_v1_5.new(public_key)
        data_hash = SHA256.new((str(transaction.sender) + str(transaction.recipient) + str(transaction.amount)).encode('utf8'))
        return verifier.verify(data_hash, binascii.unhexlify(transaction.signature))