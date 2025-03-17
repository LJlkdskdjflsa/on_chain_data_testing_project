from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solana.rpc.api import Client
from spl.token.client import Token
import os

client = Client("https://api.mainnet-beta.solana.com")

# 你的主錢包（owner）
wallet = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_TrueNorthTest_2"))

# USDC的Mint Address
USDC_MINT = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

# SPL Token Program ID
SPL_TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# 正確初始化 token client
token_client = Token(
    conn=client,
    program_id=SPL_TOKEN_PROGRAM_ID,
    pubkey=USDC_MINT,
    payer=wallet,
)

# 創建 USDC Token Account
usdc_account = token_client.create_associated_token_account(owner=wallet.pubkey())

print(f"✅ USDC Token Account Created: {usdc_account}")
