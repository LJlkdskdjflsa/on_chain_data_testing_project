from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from dotenv import load_dotenv
import os
import base58
import json

# Load environment variables
load_dotenv()


def setup_solana_connection():
    """
    Set up connection to Solana network
    """
    # You can use the default RPC endpoint for testing
    # For production, use a dedicated RPC provider like Helius
    connection = Client(f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}")
    return connection

def setup_wallet_from_env()-> Keypair:
    """
    Set up wallet using private key from environment variables
    """
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY not found in environment variables")
    
    # Create keypair directly from the base58 string
    keypair = Keypair.from_base58_string(private_key)
    return keypair

# def setup_wallet_from_file(file_path):
#     """
#     Set up wallet using private key from a file
#     """
#     try:
#         with open(file_path, 'r') as f:
#             private_key_array = json.load(f)
        
#         # Convert the array to Uint8Array
#         keypair = Keypair.from_secret_key(bytes(private_key_array))
#         return keypair
#     except Exception as e:
#         raise Exception(f"Error reading private key file: {str(e)}")

def main():
    # Set up connection
    connection = setup_solana_connection()
    print("✅ Connected to Solana network")

    # Example of setting up wallet from environment variable
    try:
        wallet = setup_wallet_from_env()
        print(f"✅ Wallet loaded from environment variables")
        print(f"Public Key: {wallet.pubkey()}")
    except ValueError as e:
        print(f"❌ Error loading wallet from environment: {str(e)}")

    # Example of setting up wallet from file
    # try:
    #     wallet = setup_wallet_from_file('/Users/user/.config/solana/id.json')
    #     print(f"✅ Wallet loaded from file")
    #     print(f"Public Key: {wallet.public_key}")
    # except Exception as e:
    #     print(f"❌ Error loading wallet from file: {str(e)}")

if __name__ == "__main__":
    main() 