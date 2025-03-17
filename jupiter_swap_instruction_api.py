import httpx
import requests
from solana.rpc.api import Client
import solders
from solders.keypair import Keypair
from dotenv import load_dotenv
import os
import base64
from solders.keypair import Keypair

        # Create the message
from solders.message import Message, MessageV0
from solders.transaction import VersionedTransaction

# Load environment variables
load_dotenv()


def main():
    # Set up connection and wallet
    client = Client(
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
        swap_url = "https://api.jup.ag/swap/v1/swap-instructions"
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

        instructions_response = requests.post(
            swap_url, json=swap_payload, headers={"Content-Type": "application/json"}
        ).json()
        print("✅ Swap created")

        # Convert the response from string to dictionary if needed
        if isinstance(instructions_response, str):
            import json
            instructions_response = json.loads(instructions_response)

        # Create a list to hold all our instructions
        all_instructions = []
        
        # Helper function to convert account metas
        def convert_account_metas(accounts):
            from solders.instruction import AccountMeta
            from solders.pubkey import Pubkey
            return [
                AccountMeta(
                    pubkey=Pubkey.from_string(acc['pubkey']),
                    is_signer=acc['isSigner'],
                    is_writable=acc['isWritable']
                )
                for acc in accounts
            ]

        # Add compute budget instructions
        for compute_instruction in instructions_response['computeBudgetInstructions']:
            from solders.instruction import Instruction
            from solders.pubkey import Pubkey
            
            compute_ix = Instruction(
                program_id=Pubkey.from_string(compute_instruction['programId']),
                accounts=convert_account_metas(compute_instruction.get('accounts', [])),
                data=base64.b64decode(compute_instruction['data'])
            )
            all_instructions.append(compute_ix)

        # Add setup instructions
        for setup_instruction in instructions_response['setupInstructions']:
            setup_ix = Instruction(
                program_id=Pubkey.from_string(setup_instruction['programId']),
                accounts=convert_account_metas(setup_instruction['accounts']),
                data=base64.b64decode(setup_instruction['data'])
            )
            all_instructions.append(setup_ix)

        # Add swap instruction
        swap_ix = Instruction(
            program_id=Pubkey.from_string(instructions_response['swapInstruction']['programId']),
            accounts=convert_account_metas(instructions_response['swapInstruction']['accounts']),
            data=base64.b64decode(instructions_response['swapInstruction']['data'])
        )
        all_instructions.append(swap_ix)

        # Add cleanup instruction if present
        if instructions_response.get('cleanupInstruction'):
            cleanup_ix = Instruction(
                program_id=Pubkey.from_string(instructions_response['cleanupInstruction']['programId']),
                accounts=convert_account_metas(instructions_response['cleanupInstruction']['accounts']),
                data=base64.b64decode(instructions_response['cleanupInstruction']['data'])
            )
            all_instructions.append(cleanup_ix)

        
        # Get the blockhash from the response
        # blockhash_bytes = bytes(instructions_response['blockhashWithMetadata']['blockhash'])
        # recent_blockhash = solders.hash.Hash(blockhash_bytes)

        # Create the message
        message = MessageV0.try_compile(
            payer=wallet.pubkey(),
            instructions=all_instructions,
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
        
        print(f"✅ Transaction sent: {response.json()}")

        # Wait for confirmation

    except Exception as e:
        print(f"❌ Error during swap: {str(e)}")


if __name__ == "__main__":
    main()
