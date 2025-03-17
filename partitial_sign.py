import os
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0, to_bytes_versioned
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

payer = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_TrueNorthTest_2"))
tx_sender = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))
ix = Instruction(
    program_id=Pubkey.new_unique(),
    data=b"",
    accounts=[AccountMeta(tx_sender.pubkey(), True, False)]
)
message = MessageV0.try_compile(payer.pubkey(), [ix], [], Hash.default())
# sign with a real signer and a null signer
signers = (payer, NullSigner(tx_sender.pubkey()))
partially_signed = VersionedTransaction(message=message,keypairs=signers)
serialized = bytes(partially_signed)
deserialized = VersionedTransaction.from_bytes(serialized)
assert deserialized == partially_signed
deserialized_message = deserialized.message

# find the null signer in the deserialized transaction
keypair1_sig_index = next(
    i
    for i, key in enumerate(deserialized_message.account_keys)
    if key == tx_sender.pubkey()
)
sigs = deserialized.signatures
# replace the null signature with a real signature
sigs[keypair1_sig_index] = tx_sender.sign_message(
    to_bytes_versioned(deserialized_message)
)
deserialized.signatures = sigs
fully_signed = VersionedTransaction(message, [payer, tx_sender])
assert deserialized.signatures == fully_signed.signatures
assert deserialized == fully_signed
assert bytes(deserialized) == bytes(fully_signed)