"""
AP2 Payment Service
Handles Agent Payments Protocol (AP2) mandate creation and verification with cryptographic signatures.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from database.models import PaymentMandate, NegotiationSession, Supplier


class AP2Service:
    """Handles AP2 payment mandate creation with cryptographic signatures."""

    def __init__(self, db: Session, private_key_pem: Optional[str] = None):
        self.db = db

        # In production, load from secure key storage (Azure Key Vault)
        # For today: Generate ephemeral RSA-2048 key pair
        if private_key_pem:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
        else:
            # Generate new key pair (ephemeral for demo)
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

        self.public_key = self.private_key.public_key()

    def create_mandate(
        self,
        supplier_id: str,
        amount: float,
        currency: str,
        order_details: Dict[str, Any],
        session_id: Optional[str] = None,
        po_number: Optional[str] = None,
        user_consent: bool = False
    ) -> Dict[str, Any]:
        """
        Create AP2 payment mandate with cryptographic signature.

        Args:
            supplier_id: Supplier/merchant ID
            amount: Payment amount
            currency: Currency code (e.g., 'USD')
            order_details: Order line items and metadata
            session_id: Optional negotiation session ID for linking
            po_number: Optional purchase order number for linking
            user_consent: User has provided consent (required)

        Returns:
            Dict with mandate_id, signed_mandate, and metadata
        """

        if not user_consent:
            raise ValueError("User consent required for payment mandate creation (user_consent=True)")

        # Validate supplier
        supplier = self.db.query(Supplier).filter_by(supplier_id=supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        mandate_id = f"ap2-{uuid.uuid4().hex[:10]}"

        # Create AP2 checkout mandate payload (SD-JWT format)
        # Based on Google's AP2 spec: https://developers.google.com/agent-payments
        mandate_payload = {
            # Standard JWT claims
            "iss": "SupplyMind",  # Issuer (our system)
            "sub": supplier_id,   # Subject (merchant/supplier)
            "aud": "ap2-payment-gateway",  # Audience (payment processor)
            "iat": int(datetime.utcnow().timestamp()),  # Issued at
            "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),  # Expires in 24 hours
            "jti": mandate_id,  # JWT ID (unique identifier)

            # AP2-specific claims
            "mandate_id": mandate_id,
            "mandate_type": "checkout",
            "amount": amount,
            "currency": currency,
            "order_details": order_details,

            # Optional links
            "session_id": session_id,
            "po_number": po_number,

            # Consent tracking
            "user_consent": user_consent,
            "consent_timestamp": datetime.utcnow().isoformat()
        }

        # Sign with JWS (JWT with RS256 signature algorithm)
        # RS256 = RSA Signature with SHA-256
        signed_mandate = jwt.encode(
            mandate_payload,
            self.private_key,
            algorithm="RS256",
            headers={"kid": "supplymind-key-001"}  # Key ID for verification
        )

        # Store in database
        mandate = PaymentMandate(
            mandate_id=mandate_id,
            session_id=session_id,
            po_number=po_number,
            supplier_id=supplier_id,
            amount=amount,
            currency=currency,
            mandate_type="checkout",
            signed_mandate_json=signed_mandate,
            signature_algorithm="RS256",
            public_key_id="supplymind-key-001",
            status="created",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        self.db.add(mandate)
        self.db.commit()

        return {
            "mandate_id": mandate_id,
            "signed_mandate": signed_mandate,
            "amount": amount,
            "currency": currency,
            "supplier_id": supplier_id,
            "expires_at": mandate.expires_at.isoformat(),
            "status": "created",
            "session_id": session_id,
            "po_number": po_number
        }

    def verify_mandate(
        self,
        mandate_id: str,
        merchant_authorization: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify payment mandate signature and validity.

        Args:
            mandate_id: Payment mandate ID to verify
            merchant_authorization: Optional merchant's signed authorization response

        Returns:
            Dict with verification status and decoded payload
        """

        mandate = self.db.query(PaymentMandate).filter_by(mandate_id=mandate_id).first()
        if not mandate:
            raise ValueError(f"Mandate {mandate_id} not found")

        # Check expiry
        if datetime.utcnow() > mandate.expires_at:
            mandate.status = "expired"
            self.db.commit()
            return {
                "mandate_id": mandate_id,
                "valid": False,
                "error": "Mandate expired",
                "expired_at": mandate.expires_at.isoformat()
            }

        # Verify JWT signature
        try:
            decoded = jwt.decode(
                mandate.signed_mandate_json,
                self.public_key,
                algorithms=["RS256"],
                audience="ap2-payment-gateway"
            )

            # Verify merchant authorization if provided
            if merchant_authorization:
                # In production: Verify merchant's signature with their public key
                # For today: Just store it
                mandate.merchant_authorization_json = merchant_authorization
                mandate.status = "verified"
                self.db.commit()

            return {
                "mandate_id": mandate_id,
                "valid": True,
                "decoded_payload": decoded,
                "status": mandate.status,
                "amount": float(mandate.amount),
                "currency": mandate.currency,
                "supplier_id": mandate.supplier_id
            }

        except jwt.ExpiredSignatureError:
            mandate.status = "expired"
            mandate.error_message = "JWT signature expired"
            self.db.commit()
            return {
                "mandate_id": mandate_id,
                "valid": False,
                "error": "Signature expired"
            }
        except jwt.InvalidSignatureError:
            mandate.status = "failed"
            mandate.error_message = "Invalid JWT signature"
            self.db.commit()
            return {
                "mandate_id": mandate_id,
                "valid": False,
                "error": "Invalid signature"
            }
        except Exception as e:
            mandate.status = "failed"
            mandate.error_message = str(e)
            self.db.commit()
            return {
                "mandate_id": mandate_id,
                "valid": False,
                "error": f"Verification error: {str(e)}"
            }

    def execute_payment(
        self,
        mandate_id: str,
        po_number: str
    ) -> Dict[str, Any]:
        """
        Execute payment using verified mandate.

        In production, this would:
        1. Call payment gateway API with signed mandate
        2. Wait for confirmation
        3. Update status

        For today: Mark as executed after verification check.

        Args:
            mandate_id: Payment mandate ID to execute
            po_number: Purchase order number to link

        Returns:
            Dict with execution status
        """

        mandate = self.db.query(PaymentMandate).filter_by(mandate_id=mandate_id).first()
        if not mandate:
            raise ValueError(f"Mandate {mandate_id} not found")

        if mandate.status != "verified":
            # Auto-verify if status is "created" (for simpler demo flow)
            if mandate.status == "created":
                verify_result = self.verify_mandate(mandate_id)
                if not verify_result.get("valid"):
                    raise ValueError(f"Mandate verification failed: {verify_result.get('error')}")
            else:
                raise ValueError(
                    f"Mandate must be verified before execution. "
                    f"Current status: {mandate.status}"
                )

        # In production: Call payment gateway API here
        # POST https://payment-gateway.example.com/ap2/execute
        # Headers: { "Authorization": "Bearer {signed_mandate}" }
        # Body: { "mandate_id": mandate_id, "po_number": po_number }

        # For today: Mark as executed
        mandate.status = "executed"
        mandate.executed_at = datetime.utcnow()
        mandate.po_number = po_number

        self.db.commit()

        return {
            "mandate_id": mandate_id,
            "status": "executed",
            "amount": float(mandate.amount),
            "currency": mandate.currency,
            "supplier_id": mandate.supplier_id,
            "po_number": po_number,
            "executed_at": mandate.executed_at.isoformat(),
            "message": "Payment executed successfully (simulated)"
        }

    def get_public_key_pem(self) -> str:
        """
        Get public key in PEM format for sharing with suppliers.

        Suppliers need this to verify our signed mandates.
        """
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
