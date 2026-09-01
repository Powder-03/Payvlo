"""Application Layer Data Transfer Objects (DTOs) & Pydantic v2 Schemas.

Clean Architecture layer: Application.
Modularized schema definitions for Catalog, Quotes, Checkout, Audit, UAP, Merchant, and Auth.
"""
from .catalog import (
    ProductDTO,
    CatalogSearchInputDTO,
    CatalogSearchResultDTO,
    DirectProductInputDTO,
)
from .quote import (
    QuoteRequestItemDTO,
    QuoteRequestInputDTO,
    QuoteItemDTO,
    QuoteResponseDTO,
)
from .checkout import (
    AddressDTO,
    CheckoutInputDTO,
    CheckoutResponseDTO,
)
from .audit import (
    AuditInspectInputDTO,
    AuditEntryDTO,
    AuditInspectResponseDTO,
)
from .uap import (
    UAPAgentCardDTO,
    UAPNegotiateRequestDTO,
    UAPNegotiateResponseDTO,
    UAPTransactRequestDTO,
    UAPTransactResponseDTO,
)
from .merchant import (
    CatalogSyncConfigDTO,
    MerchantProfileDTO,
    MerchantOnboardInputDTO,
    MerchantOnboardResponseDTO,
    CatalogSyncTriggerDTO,
    CatalogSyncResponseDTO,
    MerchantListResponseDTO,
)
from .auth import (
    UserSignupInputDTO,
    UserLoginInputDTO,
    UserProfileDTO,
    UserAuthResponseDTO,
    SavedAddressInputDTO,
    SavedAddressResponseDTO,
    UserApiKeyResponseDTO,
    MyStoreResponseDTO,
)

__all__ = [
    # Catalog
    "ProductDTO",
    "CatalogSearchInputDTO",
    "CatalogSearchResultDTO",
    "DirectProductInputDTO",
    # Quote
    "QuoteRequestItemDTO",
    "QuoteRequestInputDTO",
    "QuoteItemDTO",
    "QuoteResponseDTO",
    # Checkout
    "AddressDTO",
    "CheckoutInputDTO",
    "CheckoutResponseDTO",
    # Audit
    "AuditInspectInputDTO",
    "AuditEntryDTO",
    "AuditInspectResponseDTO",
    # UAP
    "UAPAgentCardDTO",
    "UAPNegotiateRequestDTO",
    "UAPNegotiateResponseDTO",
    "UAPTransactRequestDTO",
    "UAPTransactResponseDTO",
    # Merchant
    "CatalogSyncConfigDTO",
    "MerchantProfileDTO",
    "MerchantOnboardInputDTO",
    "MerchantOnboardResponseDTO",
    "CatalogSyncTriggerDTO",
    "CatalogSyncResponseDTO",
    "MerchantListResponseDTO",
    # Auth
    "UserSignupInputDTO",
    "UserLoginInputDTO",
    "UserProfileDTO",
    "UserAuthResponseDTO",
    "SavedAddressInputDTO",
    "SavedAddressResponseDTO",
    "UserApiKeyResponseDTO",
    "MyStoreResponseDTO",
]

