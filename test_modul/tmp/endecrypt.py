from Crypto import Random
from Crypto.Cipher import AES
import base64

BLOCK_SIZE=16

def encrypt(message, passphrase='aaaabbbbccccdddd'):
    # passphrase MUST be 16, 24 or 32 bytes long, how can I do that ?
    IV = Random.new().read(BLOCK_SIZE)
    aes = AES.new(passphrase, AES.MODE_CFB, IV)
    return base64.b64encode(aes.encrypt(message))

def decrypt(encrypted, passphrase='aaaabbbbccccdddd'):
    IV = Random.new().read(BLOCK_SIZE)
    aes = AES.new(passphrase, AES.MODE_CFB, IV)
    return aes.decrypt(base64.b64decode(encrypted))
