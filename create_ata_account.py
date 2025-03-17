import os
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
)
from solana.rpc.commitment import Confirmed
from dotenv import load_dotenv
import base64
from solders.message import MessageV0, to_bytes_versioned
import httpx

# Load environment variables
load_dotenv()

# 設定 RPC 連線
client = Client(
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}"
)
payer = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))

# 目標用戶（Owner）
owner = Pubkey.from_string(os.getenv("WALLET_ADDRESS_TrueNorthTest_2"))

async def create_ata_if_not_exists(mint: str) -> str:
    # 計算目標用戶的 ATA 地址
    mint_pubkey = Pubkey.from_string(mint)
    ata_address = get_associated_token_address(owner, mint_pubkey)

    print("目標用戶的 ATA 地址:", ata_address)

    # 檢查 ATA 是否已存在
    ata_info = client.get_account_info(ata_address, commitment=Confirmed)

    if ata_info.value is None:
        print("ATA 不存在，正在創建...")

        # 創建 ATA 指令
        instruction = create_associated_token_account(
            payer=payer.pubkey(),  # 由你的錢包支付交易
            owner=owner,  # 設置為目標用戶
            mint=mint_pubkey,  # 代幣 mint 地址
        )

        # 創建 MessageV0
        message = MessageV0.try_compile(
            payer.pubkey(),
            [instruction],
            [],  # address lookup tables
            client.get_latest_blockhash().value.blockhash
        )

        # 創建並簽名 VersionedTransaction
        tx = VersionedTransaction(message, [payer])

        # Encode transaction
        encoded_tx = base64.b64encode(bytes(tx)).decode("utf-8")

        # Send transaction with proper configuration
        headers = {"Content-Type": "application/json"}
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                encoded_tx,
                {
                    "skipPreflight": True,
                    "preflightCommitment": "finalized",
                    "encoding": "base64",
                    "maxRetries": None,
                    "minContextSlot": None,
                },
            ],
        }

        response = httpx.post(
            f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}",
            headers=headers,
            json=data,
        )
        
        print("ATA 創建成功:", response.json()['result'])
    else:
        print("ATA 已存在")

# 執行
import asyncio

asyncio.run(create_ata_if_not_exists(mint="Dfh5DzRgSvvCFDoYc2ciTkMrbDfRKybA4SoFbPmApump"))
