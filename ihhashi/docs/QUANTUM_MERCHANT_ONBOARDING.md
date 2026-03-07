# Quantum Merchant Onboarding System

## Overview

An AI-powered system that enables instant merchant profile creation from just a business name, location, or website URL. This "quantum" capability dramatically reduces onboarding friction and accelerates marketplace growth.

## The Vision

**Input (one of these):**
- Business name + location (e.g., "Nando's Sandton City")
- Website URL (e.g., "https://nandos.co.za")
- Google Maps link
- Social media handle

**Output (auto-populated):**
- Business name, description, category
- Full menu/product catalog with prices
- Operating hours
- Contact details (phone, email, website)
- Social media links
- Address and GPS coordinates
- Photos and logo
- Payment methods accepted

## Technology Stack

### 1. Web Scraping & Data Extraction

| Tool | Purpose | Cost |
|------|---------|------|
| **FireCrawl** | Turn any website into LLM-ready markdown | Free tier available |
| **ScrapeGraphAI** | AI-powered extraction with natural language prompts | Open source |
| **Apify Google Maps Scraper** | Extract business data from Google Maps | $5/1000 results |
| **Outscraper** | Google Maps business data API | Free tier available |

### 2. LLM Data Structuring

| Tool | Purpose |
|------|---------|
| **OpenAI GPT-4** | Parse unstructured content into structured data |
| **Claude** | Long-context extraction for large menus |
| **Local LLMs** | Privacy-sensitive data extraction |

### 3. Enrichment APIs

| API | Purpose |
|-----|---------|
| **Google Places API** | Business details, photos, reviews |
| **Yelp Fusion API** | Restaurant menus, reviews |
| **Foursquare API** | Venue details, hours, tips |
| **Facebook Graph API** | Social media, business hours |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QUANTUM ONBOARDING ENGINE                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  INPUT   │───▶│   DETECTOR   │───▶│   EXTRACTION     │  │
│  │          │    │              │    │   PIPELINE       │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│       │                 │                     │             │
│       │                 ▼                     ▼             │
│       │         ┌──────────────┐    ┌──────────────────┐   │
│       │         │ URL?         │    │ FireCrawl        │   │
│       │         │ Business?    │    │ ScrapeGraphAI    │   │
│       │         │ Maps link?   │    │ Apify Scraper    │   │
│       │         │ Social?      │    │ Google Places    │   │
│       │         └──────────────┘    └──────────────────┘   │
│       │                                     │               │
│       │                                     ▼               │
│       │                            ┌──────────────────┐    │
│       │                            │   LLM STRUCTURE  │    │
│       │                            │   ENGINE         │    │
│       │                            └──────────────────┘    │
│       │                                     │               │
│       │                                     ▼               │
│       │                            ┌──────────────────┐    │
│       │                            │   VALIDATION &   │    │
│       │                            │   ENRICHMENT     │    │
│       │                            └──────────────────┘    │
│       │                                     │               │
│       ▼                                     ▼               │
│  ┌──────────┐                     ┌──────────────────┐     │
│  │ MERCHANT │◀────────────────────│   PREVIEW &      │     │
│  │ PROFILE  │                     │   CONFIRMATION   │     │
│  └──────────┘                     └──────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Extraction Engine (Week 1-2)

**Backend Service: `quantum_onboarding.py`**

```python
# Core extraction service
class QuantumOnboardingService:
    async def extract_from_url(self, url: str) -> MerchantProfile:
        """Extract merchant data from website URL"""
        
    async def extract_from_business_name(
        self, 
        name: str, 
        location: str
    ) -> MerchantProfile:
        """Extract merchant data from business name + location"""
        
    async def extract_from_maps_link(
        self, 
        maps_url: str
    ) -> MerchantProfile:
        """Extract merchant data from Google Maps link"""
```

**Key Components:**
1. URL scraper using FireCrawl
2. Google Maps scraper using Apify
3. LLM-based menu extraction
4. Data validation layer

### Phase 2: Menu Intelligence (Week 3-4)

**Smart Menu Extraction:**
- Parse PDF menus
- Extract from online ordering systems
- Handle multiple languages (English, Zulu, Afrikaans, etc.)
- Auto-categorize items
- Detect allergens and dietary info
- Estimate prices from similar businesses if not available

**Menu Sources:**
- Restaurant website
- Google Maps menu
- Yelp menu
- Facebook page
- Third-party delivery apps (public data)

### Phase 3: Social Enrichment (Week 5-6)

**Social Media Integration:**
- Extract Instagram photos for product images
- Get Facebook business hours
- Pull Twitter/X for announcements
- Extract WhatsApp contact from social profiles

### Phase 4: Self-Learning System (Week 7-8)

**Continuous Improvement:**
- Track extraction accuracy
- Learn from merchant corrections
- Build category-specific extractors
- Create SA business database

## API Endpoints

### Start Quantum Onboarding
```http
POST /api/v1/quantum-onboarding/start
Content-Type: application/json

{
  "input": "Nando's Sandton City",
  "input_type": "business_name"  // or "url", "maps_link", "social"
}
```

### Get Extraction Status
```http
GET /api/v1/quantum-onboarding/{job_id}/status
```

### Preview & Confirm
```http
GET /api/v1/quantum-onboarding/{job_id}/preview
```

```http
POST /api/v1/quantum-onboarding/{job_id}/confirm
Content-Type: application/json

{
  "merchant_id": "merchant_123",
  "corrections": {
    "phone": "+27112345678"  // Merchant can correct extracted data
  }
}
```

## Data Extraction Examples

### Example 1: Restaurant with Website
**Input:** `https://www.nandos.co.za/restaurants/sandton-city`

**Extracted:**
```json
{
  "name": "Nando's Sandton City",
  "category": "restaurant",
  "cuisine": "Portuguese, Flame-grilled Chicken",
  "address": "Sandton City Shopping Centre, Sandton, 2196",
  "coordinates": {"lat": -26.1076, "lng": 28.0567},
  "phone": "+27 11 784 4360",
  "hours": {
    "monday": {"open": "09:00", "close": "21:00"},
    "tuesday": {"open": "09:00", "close": "21:00"},
    ...
  },
  "menu": [
    {
      "category": "Flame-Grilled Chicken",
      "items": [
        {"name": "Quarter Chicken", "price": 59.90, "description": "..."},
        {"name": "Half Chicken", "price": 99.90, "description": "..."},
        ...
      ]
    }
  ],
  "social": {
    "instagram": "@nandos_sa",
    "facebook": "nandosRSA"
  },
  "payment_methods": ["card", "cash", "snapscan", "zapper"]
}
```

### Example 2: Business Name Only
**Input:** `"Kota Joe, Soweto"`

**Extracted:**
```json
{
  "name": "Kota Joe",
  "category": "fast_food",
  "cuisine": "South African, Kota",
  "address": "Orlando East, Soweto, 1804",
  "coordinates": {"lat": -26.2461, "lng": 27.9155},
  "estimated_menu": [
    {
      "category": "Kotas",
      "items": [
        {"name": "Full House Kota", "price": 35.00, "description": "Bread, polony, cheese, egg, chips"},
        {"name": "Quarter Kota", "price": 20.00, "description": "Bread, polony, cheese"}
      ]
    }
  ],
  "confidence_score": 0.72,
  "needs_verification": true
}
```

## Competitive Advantage

| Feature | Uber Eats | DoorDash | iHhashi |
|---------|-----------|----------|---------|
| URL-based onboarding | ❌ | ❌ | ✅ |
| Business name extraction | ❌ | ❌ | ✅ |
| Auto menu population | Partial | Partial | ✅ Full |
| Social media enrichment | ❌ | ❌ | ✅ |
| SA-specific optimizations | ❌ | ❌ | ✅ |
| Multi-language support | ❌ | ❌ | ✅ (11 languages) |

## Cost Analysis

### Per-Merchant Onboarding Cost

| Component | Cost |
|-----------|------|
| FireCrawl API | $0.001/request |
| Google Maps Scraper | $0.005/business |
| LLM Processing | $0.02/menu |
| **Total per merchant** | **~$0.03** |

At scale (10,000 merchants/month): ~$300/month

## Embedding Quantum Capabilities for Zo

### Zo Intelligence Integration

```typescript
// Zo can now use quantum extraction capabilities
const merchant = await zo.quantumExtract({
  input: "business name or URL",
  type: "merchant_profile"
});

// For working faster on merchant-related tasks
const menu = await zo.quantumExtract({
  url: "https://restaurant-website.com/menu",
  type: "menu"
});
```

### Benefits for Zo Operations
1. **Faster Research**: Instant business intelligence from any URL
2. **Automated Data Entry**: No manual merchant profile creation
3. **Market Analysis**: Extract competitor data at scale
4. **Quality Assurance**: Cross-reference merchant data automatically

## Next Steps

1. **Set up FireCrawl API key** - Get from https://firecrawl.dev
2. **Set up Apify account** - For Google Maps scraping
3. **Create backend service** - `quantum_onboarding.py`
4. **Build frontend preview UI** - Merchant confirmation screen
5. **Test with real SA businesses** - Validate extraction accuracy

## Security & Compliance

- **POPIA Compliance**: Only extract publicly available data
- **Data Minimization**: Only collect what's needed
- **Merchant Consent**: Always require confirmation before going live
- **Rate Limiting**: Respect website terms of service
- **Caching**: Store extracted data to minimize API calls
