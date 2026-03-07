"""
Paystack payment service for South Africa
Handles payment initialization, verification, and webhooks
"""
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from app.config import settings


class PaystackService:
    """Paystack API integration for payments"""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.paystack_secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def initialize_payment(
        self,
        email: str,
        amount: float,  # Amount in ZAR
        reference: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initialize a payment transaction
        
        Args:
            email: Customer email
            amount: Amount in ZAR (will be converted to cents)
            reference: Unique transaction reference
            callback_url: URL to redirect after payment
            metadata: Additional data to store
        
        Returns:
            Payment initialization response with authorization_url
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transaction/initialize",
                headers=self.headers,
                json={
                    "email": email,
                    "amount": int(amount * 100),  # Convert to cents
                    "reference": reference,
                    "callback_url": callback_url,
                    "metadata": metadata or {},
                    "currency": "ZAR"
                }
            )
            return response.json()
    
    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """
        Verify a payment transaction
        
        Args:
            reference: Transaction reference to verify
        
        Returns:
            Verification response with transaction details
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers
            )
            return response.json()
    
    async def refund_payment(
        self,
        reference: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Initiate a refund for a transaction
        
        Args:
            reference: Transaction reference to refund
            amount: Amount to refund (full refund if None)
        
        Returns:
            Refund response
        """
        payload = {"transaction": reference}
        if amount:
            payload["amount"] = int(amount * 100)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/refund",
                headers=self.headers,
                json=payload
            )
            return response.json()
    
    async def verify_account_number(
        self,
        account_number: str,
        bank_code: str
    ) -> Dict[str, Any]:
        """
        Verify bank account details
        
        Args:
            account_number: Bank account number
            bank_code: Bank code
        
        Returns:
            Account verification response with account name
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/bank/resolve",
                headers=self.headers,
                params={
                    "account_number": account_number,
                    "bank_code": bank_code
                }
            )
            return response.json()
    
    async def create_transfer_recipient(
        self,
        account_number: str,
        bank_code: str,
        name: str
    ) -> Dict[str, Any]:
        """
        Create a transfer recipient for payouts
        
        Args:
            account_number: Bank account number
            bank_code: Bank code (e.g., '050' for Standard Bank)
            name: Account holder name
        
        Returns:
            Recipient code for transfers
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transferrecipient",
                headers=self.headers,
                json={
                    "type": "nuban",
                    "name": name,
                    "account_number": account_number,
                    "bank_code": bank_code,
                    "currency": "ZAR"
                }
            )
            return response.json()
    
    async def initiate_transfer(
        self,
        amount: float,
        recipient_code: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Initiate a transfer to a recipient (for payouts)
        
        Args:
            amount: Amount in ZAR
            recipient_code: Recipient code from create_transfer_recipient
            reason: Reason for transfer
        
        Returns:
            Transfer initiation response
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/transfer",
                headers=self.headers,
                json={
                    "amount": int(amount * 100),
                    "recipient": recipient_code,
                    "reason": reason,
                    "currency": "ZAR"
                }
            )
            return response.json()
    
    async def list_banks(self, country: str = "south africa") -> list:
        """Get list of supported banks"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/bank",
                headers=self.headers,
                params={"country": country, "currency": "ZAR"}
            )
            return response.json().get("data", [])


# Bank codes for South African banks
SA_BANK_CODES = {
    "ABSA": "632005",
    "Capitec": "470010",
    "FNB": "250655",
    "Nedbank": "198765",
    "Standard Bank": "051001",
    "Investec": "580105",
    "African Bank": "430000",
    "Bidvest Bank": "462005",
    "Discovery Bank": "490091",
    "TymeBank": "231087"
}
