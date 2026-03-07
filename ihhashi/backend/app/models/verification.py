from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class VehicleMode(str, Enum):
    """Multi-modal delivery options for South Africa"""
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    SCOOTER = "scooter"
    ON_FOOT = "on_foot"  # Walking delivery


class DocumentType(str, Enum):
    """Document types for verification"""
    # Vendor documents
    ID_DOCUMENT = "id_document"
    COMPANY_REGISTRATION = "company_registration"
    BUSINESS_LICENSE = "business_license"
    TAX_CLEARANCE = "tax_clearance"
    PROOF_OF_ADDRESS = "proof_of_address"
    
    # Delivery serviceman documents
    DRIVERS_LICENSE = "drivers_license"
    VEHICLE_REGISTRATION = "vehicle_registration"
    NUMBER_PLATE_PHOTO = "number_plate_photo"
    
    # Common
    PROFILE_PHOTO = "profile_photo"


class VerificationDocument(BaseModel):
    """A document submitted for verification"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    document_type: DocumentType
    file_url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None  # Admin user ID
    rejection_reason: Optional[str] = None


class BlueHorseVerification(BaseModel):
    """Blue Horse verification status - SA's blue tick equivalent"""
    is_verified: bool = False
    verification_level: int = 0  # 0=unverified, 1=basic, 2=full, 3=premium
    
    # Required documents based on verification level
    documents: List[VerificationDocument] = []
    
    # Verification scoring
    identity_verified: bool = False
    business_verified: bool = False
    location_verified: bool = False
    
    # Timestamps
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    @property
    def has_blue_horse(self) -> bool:
        """Blue Horse badge appears when verification_level >= 2"""
        return self.verification_level >= 2


class VendorVerification(BaseModel):
    """Vendor-specific verification for Blue Horse status"""
    vendor_id: str
    
    # Document requirements for Blue Horse
    id_document: Optional[VerificationDocument] = None
    company_registration: Optional[VerificationDocument] = None
    business_license: Optional[VerificationDocument] = None
    proof_of_address: Optional[VerificationDocument] = None
    
    # Business details
    business_name: str
    business_address: str
    business_city: str
    business_province: str
    business_coordinates: Optional[dict] = None  # {lat, lng}
    
    # Verification status
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    blue_horse: BlueHorseVerification = BlueHorseVerification()
    
    # Ranking boost (verified vendors appear higher)
    ranking_score: float = 0.0
    
    @property
    def verification_percentage(self) -> float:
        """Calculate verification completeness"""
        docs = [self.id_document, self.company_registration, self.business_license, self.proof_of_address]
        completed = sum(1 for d in docs if d is not None)
        return (completed / 4) * 100


class DeliveryServicemanVerification(BaseModel):
    """Delivery serviceman verification for Blue Horse status"""
    serviceman_id: str
    
    # Document requirements
    id_document: Optional[VerificationDocument] = None
    drivers_license: Optional[VerificationDocument] = None
    vehicle_registration: Optional[VerificationDocument] = None
    number_plate_photo: Optional[VerificationDocument] = None
    profile_photo: Optional[VerificationDocument] = None
    
    # Vehicle/transport details
    vehicle_mode: VehicleMode = VehicleMode.ON_FOOT
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_color: Optional[str] = None
    number_plate: Optional[str] = None
    
    # Verification status
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    blue_horse: BlueHorseVerification = BlueHorseVerification()
    
    # Ranking based on verification
    ranking_score: float = 0.0
    
    @property
    def verification_percentage(self) -> float:
        """Calculate verification completeness"""
        docs = [self.id_document, self.profile_photo]
        if self.vehicle_mode != VehicleMode.ON_FOOT:
            docs.extend([self.drivers_license, self.vehicle_registration, self.number_plate_photo])
        completed = sum(1 for d in docs if d is not None)
        return (completed / len(docs)) * 100


class CustomerVerification(BaseModel):
    """Light KYC for customers"""
    customer_id: str
    
    # Light KYC documents
    id_document: Optional[VerificationDocument] = None
    profile_photo: Optional[VerificationDocument] = None
    
    # Vehicle details (if they want to be delivery serviceman)
    vehicle_mode: Optional[VehicleMode] = None
    vehicle_details: Optional[dict] = None
    number_plate: Optional[str] = None
    
    # Verification status
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    blue_horse: BlueHorseVerification = BlueHorseVerification()
    
    @property
    def verification_percentage(self) -> float:
        docs = [self.id_document, self.profile_photo]
        completed = sum(1 for d in docs if d is not None)
        return (completed / 2) * 100


# Alias for backwards compatibility
Verification = VendorVerification