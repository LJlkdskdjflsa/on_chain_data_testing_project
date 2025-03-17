import requests
import json
from config import HELIUS_RPC_ENDPOINT

def get_transaction_sender(tx_signature: str) -> str:
    """
    Get the sender's address from a Solana transaction using Helius RPC.
    
    Args:
        tx_signature (str): The transaction signature to look up
        
    Returns:
        str: The sender's address or error message
    """
    # Prepare the RPC request
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            tx_signature,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }
    
    try:
        # Make the RPC request
        response = requests.post(HELIUS_RPC_ENDPOINT, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the response
        result = response.json()
        
        # Check for errors in the response
        if "error" in result:
            return f"Error: {result['error']['message']}"
        
        # Extract the sender (first signer) from the transaction
        if result["result"]:
            transaction_data = result["result"]
            # The first signer in the transaction is typically the sender
            sender = transaction_data["transaction"]["message"]["accountKeys"][0]
            return sender
        else:
            return "Error: Transaction not found"
            
    except requests.exceptions.RequestException as e:
        return f"Error making request: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"Error parsing response: {str(e)}"
    except json.JSONDecodeError:
        return "Error: Invalid JSON response"

def main():
    # Get transaction signature from user input
    tx_signature = input("Enter the transaction signature: ")
    
    # Get and display the sender
    sender = get_transaction_sender(tx_signature)
    
    # Print the result
    if sender.startswith("Error"):
        print(f"\n❌ {sender}")
    else:
        print(f"\n✅ Transaction sender: {sender}")

if __name__ == "__main__":
    main() 