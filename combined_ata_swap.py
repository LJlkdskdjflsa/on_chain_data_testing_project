import os
import base64
import time
import httpx
import requests
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import MessageV0, to_bytes_versioned
from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup RPC connection
client = Client(
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}"
)
wallet = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))

async def create_ata_if_not_exists(mint: str, owner_address: str) -> str:
    """Create ATA if it doesn't exist. Returns True if ATA exists or was created successfully."""
    # Calculate target user's ATA address
    owner = Pubkey.from_string(owner_address)
    mint_pubkey = Pubkey.from_string(mint)
    ata_address = get_associated_token_address(owner, mint_pubkey)

    print(f"Checking ATA address: {ata_address}")

    # Check if ATA exists
    ata_info = client.get_account_info(ata_address, commitment=Confirmed)

    if ata_info.value is None:
        print("ATA doesn't exist, creating...")

        # Create ATA instruction
        instruction = create_associated_token_account(
            payer=wallet.pubkey(),
            owner=owner,
            mint=mint_pubkey,
        )

        # Create MessageV0
        message = MessageV0.try_compile(
            payer=wallet.pubkey(),
            instructions=[instruction],
            address_lookup_table_accounts=[],
            recent_blockhash=client.get_latest_blockhash().value.blockhash
        )

        # Create and sign VersionedTransaction
        tx = VersionedTransaction(message, [wallet])

        # Encode transaction
        encoded_tx = base64.b64encode(bytes(tx)).decode("utf-8")

        # Send transaction
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
        
        print("ATA creation response:", response.json()['result'])
        # wait 1 second to make sure the ATA is created
        time.sleep(1)
        return ata_address
    else:
        print("ATA already exists")
        return ata_address

async def perform_swap():
    # First check/create ATA for the fee account
    output_token = "Dfh5DzRgSvvCFDoYc2ciTkMrbDfRKybA4SoFbPmApump"  # Pipin token
    # output_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC token
    
    # Check/create ATA for fee account
    fee_account_ata_address = await create_ata_if_not_exists(mint=output_token, owner_address=os.getenv("FEE_ACCOUNT"))

    # Check/create ATA for wallet

    
    
    try:
        # Get quote for swap
        quote_url = "https://api.jup.ag/swap/v1/quote"
        params = {
            "inputMint": "So11111111111111111111111111111111111111112",  # SOL
            "outputMint": output_token,  # Pipin
            "amount": "10000",  # 0.000001 SOL in lamports
            "slippageBps": "50",
            "restrictIntermediateTokens": "false",
            "platformFeeBps": "50",  # 0.5% fee
        }

        quote_response = requests.get(quote_url, params=params).json()
        print("✅ Quote received")

        # Create swap transaction with priority fee estimation
        swap_url = "https://api.jup.ag/swap/v1/swap"
        swap_payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(wallet.pubkey()),
            "feeAccount": str(fee_account_ata_address),
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {
                    "maxLamports": 5000,
                    "global": False,
                    "priorityLevel": "veryHigh"
                }
            }
        }

        swap_response = requests.post(
            swap_url, json=swap_payload, headers={"Content-Type": "application/json"}
        ).json()
        print("✅ Swap created")

        # Execute swap
        transaction_base64 = swap_response["swapTransaction"]
        raw_tx = VersionedTransaction.from_bytes(base64.b64decode(transaction_base64))
        signature = wallet.sign_message(to_bytes_versioned(raw_tx.message))
        signed_tx = VersionedTransaction.populate(raw_tx.message, [signature])
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

        print("Transaction result:", tx_response.json()['result'])

    except Exception as e:
        print(f"❌ Error during swap: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(perform_swap()) 