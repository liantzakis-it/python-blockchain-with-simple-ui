"""
class relevant to the functionality of the node
will include the app routes for the HTTP request
(will handle later on Vue.js with axios)

For every route we will handle the requests (GET/POST/DELETE) and
we will return a response where it's due


HTTP REST status codes for reference:

200 - OK (success)
201 - Created (success)
400 - Bad Request (client error)
409 - Conflict (client error)
500 - Internal Server Error (server error)
501 - Not Implemented (server error)

"""

from wallet import Wallet
from blockchain import Blockchain
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


#home page, sort of, the page of the node
@app.route('/', methods=['GET'])
def get_node_ui():
    return send_from_directory('ui', 'node.html')

#the second possible page, the one of the network
@app.route('/network', methods=['GET'])
def get_network_ui():
    return send_from_directory('ui', 'network.html')


#POST request
#could have been named /createwallet, but it's fine cause it's the only /wallet POST method so there's no name collision
@app.route('/wallet', methods=['POST'])
def create_keys():
    wallet.create_keys()
    #try to save
    if wallet.save_keys():
        global blockchain #we need the GLOBAL blockchain, need to declare it like this otherwise it will be treated like a local variable
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201 #success
    else:
        response = {
            'message': 'An error occurred while saving the wallet.'
        }
        return jsonify(response), 500 #fail, internal server error


#GET request that loads an existing wallet
@app.route('/wallet', methods=['GET'])
def load_keys():
    if wallet.load_keys():
        global blockchain #GLOBAL blockchain again, important
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201 #success
    else:
        response = {
            'message': 'An error occurred while loading your wallet.'
        }
        return jsonify(response), 500 #fail


#GET request that returns to the user his/her balance
@app.route('/balance', methods=['GET'])
def get_balance():
    balance = blockchain.get_balance()
    if balance != None:
        response = {
            'message': 'Fetched balance successfully.',
            'funds': balance
        }
        return jsonify(response), 200 #success
    else:
        #wallet_set_up is a boolean-ish indicator to show if the wallet has been created and is good to use
        response = {
            'messsage': 'Loading balance failed.',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500 #fail...


#POST request that broadcasts a transaction to the peer nodes
@app.route('/broadcast-transaction', methods=['POST'])
def broadcast_transaction():

    values = request.get_json()
    #check if we received any data
    if not values:
        response = {
            'message': 'No data received.'
        }
        return jsonify(response), 400 #fail on user's end
    #required fields below, they need to be in the data we received to have a valid transaction
    required = ['sender', 'recipient', 'amount', 'signature']
    #checks if all the required fields are in the values we received
    if not all(key in values for key in required):
        response = {
            'message': 'Insufficient transaction data received.'
        }
        return jsonify(response), 400 #fail cause not all values included

    #if checks above are ok, we move on trying to add the tranksaction
    success = blockchain.add_transaction(values['recipient'], values['sender'], values['signature'], values['amount'], is_receiving=True)
    if success:
        response = {
            'message': 'Transaction was added successfully!',
            'transaction': {
                'sender': values['sender'],
                'recipient': values['recipient'],
                'amount': values['amount'],
                'signature': values['signature']
            }
        }
        return jsonify(response), 201 #success!
    else:
        response = {
            'message': 'An error occurred while creating the transaction.'
        }
        return jsonify(response), 500 #internal server error


#POST request that broadcasts a block to the peers, similar to the transaction broadcasting above
@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():

    values = request.get_json()
    #check if we received any data
    if not values:
        response = {'message': 'No data received.'}
        return jsonify(response), 400 #fail
    #we don't need a required fields list here, we are just looking for 'block'
    if 'block' not in values:
        response = {'message': 'Insufficient block data received.'}
        return jsonify(response), 400 #fail

    #if all flows well, we move on
    block = values['block']
    if block['index'] == blockchain.chain[-1].index + 1:
        if blockchain.add_block(block):
            response = {
                'message': 'Block has been successfully added!'
            }
            return jsonify(response), 201 #Success!
        else:
            response = {
                'message': 'Corrupt block, signs of conflicts that need resolving. Could not add it.'
            }
            return jsonify(response), 409 #fail, CONFLICT

    elif block['index'] > blockchain.chain[-1].index:
        response = {
            'message': 'Local blockchain is shorter than the one broadcasting the block. Could not add it.'
        }
        blockchain.resolve_conflicts = True
        return jsonify(response), 200 #seems successful, but this is what we send to the BROADCASTING block, not US
        #the mistake is in OUR block, not the broadcasting one, therefore we send 200 and not any error code, yet we still indicate there was some error in the message

    else: 
        response = {
            'message': 'Broadcasting blockchain is shorther than the local one. Incoming block has not been accepted.'
        }
        return jsonify(response), 409 #error, fonflicts need to be resolved imminently



#POST request to add a transaction
@app.route('/transaction', methods=['POST'])
def add_transaction():
    #checks for wallet existence
    if wallet.public_key == None:
        response = {
            'message': 'There is no wallet created.'
        }
        return jsonify(response), 400 #fail on user's end

    values = request.get_json()
    #is there any data
    if not values:
        response = {
            'message': 'No data was found.'
        }
        return jsonify(response), 400 #fail on user's end again

    #basic required fields to form a transaction
    required_fields = ['recipient', 'amount']
    #check if all req fields exist in our transaction values
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Insufficient transaction data.'
        }
        return jsonify(response), 400 #fail on user's end...

    #if all is well above, we move on
    recipient = values['recipient']
    amount = values['amount']
    signature = wallet.sign_transaction(wallet.public_key, recipient, amount)
    success = blockchain.add_transaction(recipient, wallet.public_key, signature, amount)
    if success:
        response = {
            'message': 'Transaction has been successfully added.',
            'transaction': {
                'sender': wallet.public_key,
                'recipient': recipient,
                'amount': amount,
                'signature': signature
            },
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201 #success!!
    else:
        response = {
            'message': 'An error occurred while creating the transaction.'
        }
        return jsonify(response), 500 #fail, internal server error



#POST request that mines a new block for the blockchain
@app.route('/mine', methods=['POST'])
def mine():

    #we start by testing to see if we have any ongoing conflicts that need resolving
    if blockchain.resolve_conflicts:
        response = {
            'message': 'Failed to mine a new block. There are ongoing conflicts that need to be resolved.'
        }
        return jsonify(response), 409 #fail, conflicts...

    #if there aren't any conflicts, move on
    block = blockchain.mine_block()
    if block != None:
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [trans.__dict__ for trans in dict_block['transactions']]
        response = {
            'message': 'Block added successfully.',
            'block': dict_block,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201 #success
    else:
        #couldn't mine a block
        response = {
            'message': 'An error occurred while mining a block.',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500 #fail, internal server error


#POST request to resolve conflicts when needed
@app.route('/resolve-conflicts', methods=['POST'])
def resolve_conflicts():
    #checking if the function in the blockchain.py file returns true or false (if our local chain was replaced or not)
    replaced = blockchain.resolve()
    if replaced:
        response = {
            'message': 'Conflicts resolved. Local chain was replaced.'
        }
    else:
        response = {'message': 'Conflicts resolved. Local chain was kept.'}
    return jsonify(response), 200 #success either way


#simple GET request that returns the pending transactions
@app.route('/transactions', methods=['GET'])
def get_open_transaction():
    #no error handling
    transactions = blockchain.get_open_transactions()
    #transactions to dict
    dict_transactions = [trans.__dict__ for trans in transactions]
    return jsonify(dict_transactions), 200 #success


#simple GET request to get the chain
@app.route('/chain', methods=['GET'])
def get_chain():
    #get a snapshot of our chain
    chain_snapshot = blockchain.chain
    #to dict
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    for dict_block in dict_chain:
        #transactions to dict for every block in the chain
        dict_block['transactions'] = [trans.__dict__ for trans in dict_block['transactions']]
    return jsonify(dict_chain), 200 #success


#POST request that adds a node to our peer_nodes list
@app.route('/node', methods=['POST'])
def add_node():
    values = request.get_json()
    #check if we got anything
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400 #fail on user's end

    #basic check for required field 'node' in our values
    if 'node' not in values:
        response = {
            'message': 'Insufficient node data provided.'
        }
        return jsonify(response), 400 #fail on user's end

    #moving on to add the node
    node = values['node']
    blockchain.add_peer_node(node)
    response = {
        'message': 'Node has been successfully added in your peer list.',
        'all_nodes': blockchain.get_peer_nodes()
    }
    return jsonify(response), 201 #success in adding the node


#the only DELETE request here, that deletes a node from our peer list, based on a node_url that we provide it with
@app.route('/node/<node_url>', methods=['DELETE'])
def remove_node(node_url):
    #if node is blank or non-existant
    if node_url == '' or node_url == None:
        response = {
            'message': 'No such node exists. Please try again.'
        }
        return jsonify(response), 400 #fail on user's end

    blockchain.remove_peer_node(node_url)
    response = {
        'message': 'The selected node has been successfully removed.',
        'all_nodes': blockchain.get_peer_nodes()
    }
    return jsonify(response), 200 #success


#simple GET request to get all the nodes in our peer list
@app.route('/nodes', methods=['GET'])
def get_nodes():
    nodes = blockchain.get_peer_nodes()
    response = {
        'all_nodes': nodes
    }
    return jsonify(response), 200 #success


#what to run
if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    #user can run the programme creating a new node via the desired port e.g. "python node.py -p 7501"
    parser.add_argument('-p', '--port', type=int, default=7500)
    args = parser.parse_args()
    port = args.port
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key, port)
    app.run(host='0.0.0.0', port=port)
