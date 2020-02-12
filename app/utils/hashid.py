from flask import current_app
from hashids import Hashids

hashids = Hashids(salt=current_app.config["HASHIDS_SALT"], min_length=16)


def encode_id_to_str(id):
    return hashids.encode(id)


def decode_str_to_id(str):
    try:
        return hashids.decode(str)[0]
    except IndexError:
        return
