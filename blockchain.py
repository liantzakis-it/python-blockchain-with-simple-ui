"""
class relevant to the functionality of the chain


HTTP REST status codes for reference:

200 - OK (success)
201 - Created (success)
400 - Bad Request (client error)
409 - Conflict (client error)
500 - Internal Server Error (server error)
501 - Not Implemented (server error)

"""

from block import Block
from transaction import Transaction
from wallet import Wallet
from blocktools.hashing_functions import hash_block
from blocktools.verifier import Verifier
import json
import requests
from functools import reduce


# The amount of UoM-Coins the miner is rewarded with
MINING_REWARD = 50

print(__name__)


class Blockchain:
    def __init__(self, public_key, node_id):
        #initializing block (genesis)
        genesis_block = Block(0, '', [], 100, 0)
        #blockchain initialization with the geneis block
        self.chain = [genesis_block]

        self.__open_transactions = []
        self.public_key = public_key
        self.__peer_nodes = set()
        self.node_id = node_id
        self.resolve_conflicts = False
        self.load_data()

    #something like a getter
    #honestly i did not understand the functionality of this thing that much but apparently it's needed
    @property
    def chain(self):
        return self.__chain[:]

    @chain.setter
    def chain(self, val):
        self.__chain = val

    #pending transaction getter
    def get_open_transactions(self):
        return self.__open_transactions[:]

    #initializes the bchain and loads data from corresponding files
    def load_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as fi:
                file_content = fi.readlines()
                blockchain = json.loads(file_content[0][:-1])

                updated_blockchain = []

                for block in blockchain:
                    #forms the transactions objects
                    converted_trans = [Transaction(trans['sender'], trans['recipient'], trans['signature'], trans['amount']) for trans in block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], converted_trans, block['proof'], block['timestamp'])
                    updated_blockchain.append(updated_block)
                self.chain = updated_blockchain
                open_transactions = json.loads(file_content[1][:-1])
                updated_transactions = []
                for trans in open_transactions:
                    updated_transaction = Transaction(trans['sender'], trans['recipient'], trans['signature'], trans['amount'])
                    updated_transactions.append(updated_transaction)
                self.__open_transactions = updated_transactions
                peer_nodes = json.loads(file_content[2])
                self.__peer_nodes = set(peer_nodes)
        except (IOError, IndexError):
            pass
        finally:
            print('Finished the load_data function.')

    #saves the current blockchain to a file with the corresponding name based on the node
    #AND the currently pending transactions
    def save_data(self):
        try:
            #opens the file with the appropriate name each time (based on the node port)
            with open('blockchain-{}.txt'.format(self.node_id), mode='w') as fi:
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash, [
                    trans.__dict__ for trans in block_el.transactions], block_el.proof, block_el.timestamp) for block_el in self.__chain]]
                fi.write(json.dumps(saveable_chain))
                fi.write('\n')
                saveable_trans = [trans.__dict__ for trans in self.__open_transactions]
                fi.write(json.dumps(saveable_trans))
                fi.write('\n')
                fi.write(json.dumps(list(self.__peer_nodes)))

        except IOError:
            print('Saving failed!')


    #PoW generator
    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0 #initial
        #loops until it gets a valid PoW (a total hash with 2 leading zeros)
        while not Verifier.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof


    #balance calculator for a blockchain user
    def get_balance(self, sender=None):
        #checks to see if it is us or another sender, and sees if the public key exists
        if sender == None:
            if self.public_key == None:
                return None
            user = self.public_key
        else:
            user = sender

        #check all amounts sent in transactions of the user
        trans_sender = [[trans.amount for trans in block.transactions if trans.sender == user] for block in self.__chain]

        #chech amounts sent that are in OPEN transactions (it matters cause these are "reserved" coins)
        open_trans_sender = [trans.amount for trans in self.__open_transactions if trans.sender == user]
        trans_sender.append(open_trans_sender)
        print(trans_sender)
        #using a lambda to calculate it to avoid more functions
        amount_sent = reduce(lambda trans_sum, trans_amt: trans_sum + sum(trans_amt) if len(trans_amt) > 0 else trans_sum + 0, trans_sender, 0)

        #check our received amounts through transactions
        #we obviously don't check open transactions here cause it's money we don't really have, yet
        trans_recipient = [[trans.amount for trans in block.transactions if trans.recipient == user] for block in self.__chain]
        #another lambda function
        amount_received = reduce(lambda trans_sum, trans_amt: trans_sum + sum(trans_amt) if len(trans_amt) > 0 else trans_sum + 0, trans_recipient, 0)

        #total balance of the user
        return amount_received - amount_sent


    #returns the last documented state of our blockchain
    def get_last_blockchain_value(self):
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]


    #the is_receiving boolean variable will help later on while transmitting the transactions to other peer nodes
    def add_transaction(self, recipient, sender, signature, amount=1.0, is_receiving=False):

        transaction = Transaction(sender, recipient, signature, amount)
        if Verifier.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast-transaction'.format(node)
                    try:
                        response = requests.post(url, json={'sender': sender, 'recipient': recipient, 'amount': amount, 'signature': signature})
                        if response.status_code == 400 or response.status_code == 500:
                            print('An error occurred while adding the transaction. Conflict resolving is required.')
                            return False
                    #exception
                    #could handle more exceptions here than connection error (possible thing to do?)
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        return False

    #mine a new block and get a reward
    def mine_block(self):

        #need to have a wallet
        if self.public_key == None:
            return None
        #get the last block of our chain
        last_block = self.__chain[-1]

        #checking validity of block/proof
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()

        #rewarding the miner
        reward_transaction = Transaction('SYSTEM', self.public_key, '', MINING_REWARD)

        #starting here by working with a copied version of our transactions, because if something goes wrong
        #and we are working with the original list, we will lose all the open transactions
        #sounds like a calamitous event..
        copied_transactions = self.__open_transactions[:] #copy
        for trans in copied_transactions:
            if not Wallet.verify_transaction(trans):
                return None
        copied_transactions.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)
        self.__chain.append(block)
        self.__open_transactions = [] #emptying the open transactions list since we just added them in the new block
        self.save_data()

        #broadcast our new block to our peers
        for node in self.__peer_nodes:
            url = 'http://{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['transactions'] = [trans.__dict__ for trans in converted_block['transactions']]
            try:
                response = requests.post(url, json={'block': converted_block})
                if response.status_code == 400 or response.status_code == 500:
                    print('Block declined, needs resolving')
                #conflict below
                if response.status_code == 409:
                    #conflict code
                    #setting resolve conflicts to True so we need to resolve conflicts BEFORE doing anything else e.g. mining more blocks
                    self.resolve_conflicts = True
            #exceptions
            except requests.exceptions.ConnectionError:
                continue
        return block




    #verify the validity of a block and add it to our local blockchain, after having received it from a peer
    def add_block(self, block):


        transactions = [Transaction(trans['sender'], trans['recipient'], trans['signature'], trans['amount']) for trans in block['transactions']]

        #is the proof valid
        proof_is_valid = Verifier.valid_proof(transactions[:-1], block['previous_hash'], block['proof'])

        #check integrity of hashes
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False

        #moving on if nothing's gone wrong so far
        converted_block = Block( block['index'], block['previous_hash'], transactions, block['proof'], block['timestamp'])
        self.__chain.append(converted_block)
        stored_transactions = self.__open_transactions[:]

        #checking our open transactions to see if any of them were added in the newly received block from the peer
        #if so, we remove them
        for rec_trans in block['transactions']:
            for open_trans in stored_transactions:
                if open_trans.sender == rec_trans['sender'] and open_trans.recipient == rec_trans['recipient'] and open_trans.amount == rec_trans['amount'] and open_trans.signature == rec_trans['signature']:
                    try:
                        self.__open_transactions.remove(open_trans)
                    except ValueError:
                        print('Error. The transaction has already been removed.')
        self.save_data()
        return True


    #resolving conflicts
    #what matters here is the LENGTH
    def resolve(self):

        chain_to_remain = self.chain
        replaced = False

        #Basically what we do here is that we compare the length of our local chain, which is declared for now as the chain to remain
        #and if the other chains are longer, we replace the chain to remain with the longer chain

        for node in self.__peer_nodes:
            url = 'http://{}/chain'.format(node)
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(block['index'], block['previous_hash'], [Transaction(trans['sender'], trans['recipient'], trans['signature'], trans['amount']) for trans in block['transactions']], block['proof'], block['timestamp']) for block in node_chain]
                node_chain_length = len(node_chain)
                local_chain_length = len(chain_to_remain)

                if node_chain_length > local_chain_length and Verifier.verify_chain(node_chain):
                    chain_to_remain = node_chain
                    replace = True
            #exceptions
            except requests.exceptions.ConnectionError:
                continue

        #we are done with it so it's back to False
        self.resolve_conflicts = False

        #local chai neither stays the same or gets replaced
        self.chain = chain_to_remain
        if replaced:
            self.__open_transactions = [] #if it was replaced, then we empty the open transactions
        self.save_data()
        return replaced


    #just adds a node to our peers
    def add_peer_node(self, node):
        self.__peer_nodes.add(node)
        self.save_data()

    #removes a nodes from our peers
    def remove_peer_node(self, node):
        self.__peer_nodes.discard(node)
        self.save_data()

    #simple getter for our peer nodes
    def get_peer_nodes(self):
        return list(self.__peer_nodes)
