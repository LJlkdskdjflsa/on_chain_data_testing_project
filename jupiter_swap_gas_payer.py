import httpx
import requests
from solana.rpc.api import Client
import solders
from solders.keypair import Keypair
from solders.null_signer import NullSigner
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from dotenv import load_dotenv
import os
import base64

# Load environment variables
load_dotenv()


def main():
    # Set up connection and wallet
    connection = Client(
        f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}"
    )
    wallet = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))
    payer = Keypair.from_base58_string(os.getenv("PRIVATE_KEY_TrueNorthTest_2"))

    try:
        # 1. Get quote for swap
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
            "userPublicKey": str(wallet.pubkey()),
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
        raw_tx = VersionedTransaction.from_bytes(
            base64.b64decode(transaction_base64)
        )

        # 第一步：由 fee_payer 先簽名，使用 NullSigner 為 wallet 預留簽名位置
        # 找到 wallet 的簽名索引位置
        wallet_pubkey = wallet.pubkey()
        account_keys = raw_tx.message.account_keys
        
        wallet_sig_index = next(
            i for i, key in enumerate(account_keys) if key == wallet_pubkey
        )
        
        # 為 wallet 創建一個 NullSigner
        message_bytes = to_bytes_versioned(raw_tx.message)
        null_signer = NullSigner(wallet.pubkey())
        
        # 使用 payer 和 NullSigner 創建部分簽名的交易
        signers = [payer, null_signer]
        
        # 創建部分簽名的交易
        partially_signed_tx = VersionedTransaction(raw_tx.message, signers)
        
        # 將部分簽名的交易序列化並編碼為 base64
        partially_signed_base64 = base64.b64encode(bytes(partially_signed_tx)).decode("utf-8")
        print("✅ Transaction partially signed by fee_payer")
        
        # 這裡模擬將部分簽名的交易發送給 wallet 持有者
        # 在實際應用中，你可能會將 partially_signed_base64 保存或發送
        
        # 第二步：模擬 wallet 持有者接收並完成簽名
        # 反序列化部分簽名的交易
        received_tx = VersionedTransaction.from_bytes(
            base64.b64decode(partially_signed_base64)
        )
        
        # 找到 wallet 在反序列化交易中的簽名索引位置
        account_keys = received_tx.message.account_keys
        wallet_sig_index = next(
            i for i, key in enumerate(account_keys) if key == wallet_pubkey
        )
        
        # wallet 簽名
        wallet_signature = wallet.sign_message(to_bytes_versioned(received_tx.message))
        
        # 獲取當前簽名列表
        sigs = list(received_tx.signatures)
        
        # 替換 null 簽名為真實簽名
        sigs[wallet_sig_index] = wallet_signature
        
        # 更新簽名
        fully_signed_tx = VersionedTransaction.populate(received_tx.message, sigs)
        
        # 將完全簽名的交易編碼為 base64
        encoded_tx = base64.b64encode(bytes(fully_signed_tx)).decode("utf-8")
        print("✅ Transaction fully signed by wallet")

        # 4. 發送交易
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

        tx_response = httpx.post(
            f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}",
            headers=headers,
            json=data,
        )

        print("✅ Transaction sent")
        print(f"Transaction signature: {tx_response.json()['result']}")

    except Exception as e:
        print(f"❌ Error during swap: {str(e)}")


if __name__ == "__main__":
    main()