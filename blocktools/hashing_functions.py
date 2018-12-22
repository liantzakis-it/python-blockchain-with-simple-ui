import hashlib
import json


def hash_string_256(string):
    #string through sha256
    return hashlib.sha256(string).hexdigest()


def hash_block(block):
    #block through sha256 using hash_string_256
    hashable_block = block.__dict__.copy()
    hashable_block['transactions'] = [trans.to_ordered_dict() for trans in hashable_block['transactions']]
    return hash_string_256(json.dumps(hashable_block, sort_keys=True).encode())