import httpx
import requests
from solana.rpc.api import Client
import solders
from solders.keypair import Keypair
from dotenv import load_dotenv
import os
import base64
from solders.keypair import Keypair

# Load environment variables
load_dotenv()


def main():
    # Set up connection and wallet
    connection = Client(
        f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}"
    )
    wallet = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))

    try:
        # 1. Get quote for swap
        quote_url = "https://api.jup.ag/swap/v1/quote"
        params = {
            "inputMint": "So11111111111111111111111111111111111111112",  # SOL
            # "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "outputMint": "Dfh5DzRgSvvCFDoYc2ciTkMrbDfRKybA4SoFbPmApump",  # Pipin
            "amount": "10000",  # 0.01 SOL in lamports
            "slippageBps": "50",
            "restrictIntermediateTokens": "false",
            "platformFeeBps": "20",  # 0.2% fee
            # "dynamicSlippage": True,  # Enable dynamic slippage
            # "dynamicComputeUnitLimit": True  # Enable dynamic compute unit limit
        }

        quote_response = requests.get(quote_url, params=params).json()
        print("✅ Quote received")

        # 2. Create swap transaction with priority fee estimation
        swap_url = "https://api.jup.ag/swap/v1/swap"
        swap_payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(wallet.pubkey()),
            # "feeAccount": os.getenv("FEE_ACCOUNT"),
            # "feeAccount": "9mFXMkSBEjMySfTjWwc3zZvYSYom2j6pG9tz5SYbfTqo",
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {
                    "maxLamports": 5000,  # 0.01 SOL max priority fee
                    "global": False,  # Use local fee market
                    "priorityLevel": "veryHigh"  # 75th percentile
                }
            }
        }

        swap_response = requests.post(
            swap_url, json=swap_payload, headers={"Content-Type": "application/json"}
        ).json()
        print("✅ Swap created")

        # 3. Execute swap
        # Decode the base64 transaction data
        transaction_base64 = swap_response["swapTransaction"]


        raw_tx = solders.transaction.VersionedTransaction.from_bytes(
            base64.b64decode(transaction_base64)
        )

        signature = wallet.sign_message(solders.message.to_bytes_versioned(raw_tx.message))

        signed_tx = solders.transaction.VersionedTransaction.populate(
            raw_tx.message, [signature]
        )


        encoded_tx = base64.b64encode(bytes(signed_tx)).decode("utf-8")

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

        # Convert base64 to binary buffer and deserialize to Transaction
        # transaction_data = base64.b64decode(transaction_base64)
        # transaction = Transaction.deserialize(transaction_data)
        print("Transaction deserialized successfully")
        print(tx_response.json()['result'])



    except Exception as e:
        print(f"❌ Error during swap: {str(e)}")


if __name__ == "__main__":
    main()
