from typing import List
import base64
import os
import requests
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction, CompiledInstruction
from solders.keypair import Keypair
from solders.message import MessageV0, to_bytes_versioned
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

payer = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_TrueNorthTest_2"))
tx_sender = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))

def convert_message_v0_to_instructions(message_v0: MessageV0) -> List[Instruction]:
    """
    将 MessageV0 中的所有 CompiledInstruction 转换为 Instruction 列表
    
    Args:
        message_v0: 包含指令的 MessageV0 对象
        
    Returns:
        List[Instruction]: 转换后的 Instruction 列表
    """
    instructions = []
    
    # 遍历所有编译过的指令
    for compiled_instruction in message_v0.instructions:
        # 获取程序 ID
        program_id = message_v0.account_keys[compiled_instruction.program_id_index]
        
        # 获取账户 MetaData 列表
        accounts = []
        for account_idx in compiled_instruction.accounts:
            # 将字节转换为整数索引（如果需要）
            if isinstance(account_idx, bytes) or isinstance(compiled_instruction.accounts, bytes):
                # 如果 accounts 是字节串，我们需要逐个处理每个字节
                idx = account_idx if isinstance(account_idx, int) else int(account_idx)
            else:
                idx = account_idx
            
            # 获取公钥
            pubkey = message_v0.account_keys[idx]
            
            # 判断是否是签名者
            is_signer = message_v0.is_signer(idx)
            
            # 判断是否可写
            is_writable = message_v0.is_maybe_writable(idx)
            
            # 创建账户元数据
            account_meta = AccountMeta(pubkey, is_signer, is_writable)
            accounts.append(account_meta)
        
        # 创建 Instruction 并添加到列表
        instruction = Instruction(program_id, compiled_instruction.data, accounts)
        instructions.append(instruction)
    
    return instructions

def versioned_tx_to_instructions(tx: VersionedTransaction) -> List[Instruction]:
    """
    Extract Instructions from a VersionedTransaction
    
    Args:
        tx: The VersionedTransaction
        
    Returns:
        list: List of Instructions
    """
    message = tx.message
    account_keys = message.account_keys
    
    instructions = []
    for compiled_ix in message.instructions:
        # Determine which accounts are signers and writable based on message header
        signers_set = set()
        for i in range(message.header.num_required_signatures):
            signers_set.add(i)
        
        writables_set = set()
        for i in range(message.header.num_required_signatures - message.header.num_readonly_signed_accounts):
            writables_set.add(i)
        
        for i in range(message.header.num_required_signatures, 
                       message.header.num_required_signatures + message.header.num_readonly_unsigned_accounts):
            writables_set.add(i)
        
        # Reconstruct account metas
        accounts = []
        for idx in compiled_ix.accounts:
            pubkey = account_keys[idx]
            is_signer = idx in signers_set
            is_writable = idx in writables_set
            accounts.append(AccountMeta(pubkey, is_signer, is_writable))
        
        # Create the instruction
        program_id = account_keys[compiled_ix.program_id_index]
        instruction = Instruction(program_id, compiled_ix.data, accounts)
        instructions.append(instruction)
    
    return instructions


quote_url = "https://api.jup.ag/swap/v1/quote"
params = {
    "inputMint": "So11111111111111111111111111111111111111112",  # SOL
    "outputMint": "Dfh5DzRgSvvCFDoYc2ciTkMrbDfRKybA4SoFbPmApump",  # Pipin
    "amount": "100",  # 0.01 SOL in lamports
    "slippageBps": "50",
    "restrictIntermediateTokens": "false",
}

quote_response = requests.get(quote_url, params=params).json()
print("✅ Quote received")
# 2. Create swap transaction with priority fee estimation
swap_url = "https://api.jup.ag/swap/v1/swap"
swap_payload = {
    "quoteResponse": quote_response,
    "userPublicKey": str(tx_sender.pubkey()),
    "prioritizationFeeLamports": {
        "priorityLevelWithMaxLamports": {
            "maxLamports": 10000,  # 0.01 SOL max priority fee
            "global": False,  # Use local fee market
            "priorityLevel": "veryHigh"  # 75th percentile
        }
    }
}
swap_response = requests.post(
    swap_url, json=swap_payload, headers={"Content-Type": "application/json"}
).json()
print("✅ Swap created")
# 3. Decode the base64 transaction
transaction_base64 = swap_response["swapTransaction"]

# get instruction from transaction_base64
versioned_tx = VersionedTransaction.from_bytes(
    base64.b64decode(transaction_base64)
)

message: MessageV0 = versioned_tx.message
instructions = convert_message_v0_to_instructions(message)
# instructions: List[CompiledInstruction] = versioned_tx.message.instructions
# instructions = versioned_tx_to_instructions(versioned_tx)

# change the instruction to payer
# instructions[0].program_id = payer.pubkey()

# ix = Instruction(
#     program_id=Pubkey.new_unique(),
#     data=b"",
#     accounts=[AccountMeta(tx_sender.pubkey(), True, False)]
# )


new_message = MessageV0.try_compile(
    payer=payer.pubkey(),
    instructions=instructions,
    address_lookup_table_accounts=message.address_table_lookups,
    recent_blockhash=Hash.default()
)
# sign with a real signer and a null signer
signers = (payer, NullSigner(tx_sender.pubkey()))
partially_signed = VersionedTransaction(new_message, signers)
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
fully_signed = VersionedTransaction(new_message, [payer, tx_sender])
assert deserialized.signatures == fully_signed.signatures
assert deserialized == fully_signed
assert bytes(deserialized) == bytes(fully_signed)