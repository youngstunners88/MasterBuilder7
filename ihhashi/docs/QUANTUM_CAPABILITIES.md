# Quantum Capabilities for iHhashi

## Vision

**"Quantum" = Instant Data Synthesis** - The ability to extract, structure, and populate data from minimal input using AI-powered web scraping and intelligent data extraction.

---

## Part 1: Merchant Quantum Onboarding

### Problem
Merchants struggle to:
- Manually enter 50-100+ menu items
- Upload product images one by one
- Set prices, descriptions, categories
- Add contact details, social links, hours

### Solution: Quantum Onboarding Flow

```
Merchant Input (minimal):
┌─────────────────────────────────────────────┐
│ Option A: Website URL                       │
│   https://restaurantname.co.za              │
│                                             │
│ Option B: Store Name + Location             │
│   "Spur Steak Ranch, Sandton City Mall"     │
│                                             │
│ Option C: Google Maps / TripAdvisor URL     │
│   maps.google.com/place/...                 │
└─────────────────────────────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  QUANTUM ENGINE     │
         │  (AI Extraction)    │
         └─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ Auto-populated Merchant Profile:            │
│                                             │
│ ✓ Business name, logo, branding            │
│ ✓ Contact: phone, email, address            │
│ ✓ Social: Instagram, Facebook, WhatsApp     │
│ ✓ Operating hours                           │
│ ✓ Full menu/product catalog with:           │
│   - Product names                           │
│   - Prices (converted to ZAR)               │
│   - Descriptions                            │
│   - Images                                  │
│   - Categories                              │
│ ✓ Delivery radius estimate                  │
└─────────────────────────────────────────────┘
                    │
                    ▼
         Merchant reviews & confirms
                    │
                    ▼
              ONE-CLICK PUBLISH
```

### Technical Architecture

#### Layer 1: Data Discovery
| Input Type | Discovery Method |
|------------|------------------|
| Website URL | Firecrawl/Scrapfly extraction |
| Store Name + Location | Google Places API → website discovery |
| Google Maps URL | Google Places API direct |
| TripAdvisor URL | Scrapfly structured extraction |

#### Layer 2: Intelligent Extraction
```python
# Quantum Extraction Pipeline
class QuantumExtractor:
    """
    Multi-source extraction with fallback chain
    """
    
    async def extract_merchant_profile(self, input: str) -> MerchantProfile:
        # 1. Identify input type
        input_type = self.detect_input_type(input)
        
        # 2. Route to appropriate extractor
        match input_type:
            case "website_url":
                return await self.extract_from_website(input)
            case "store_name_location":
                return await self.extract_from_google_places(input)
            case "google_maps_url":
                return await self.extract_from_google_maps(input)
    
    async def extract_from_website(self, url: str) -> MerchantProfile:
        """
        Website extraction pipeline:
        1. Firecrawl → structured JSON (products, prices, contact)
        2. Fallback: Scrapfly AI extraction
        3. Fallback: Playwright + LLM extraction
        """
        pass
    
    async def extract_from_google_places(self, query: str) -> MerchantProfile:
        """
        Google Places pipeline:
        1. Places API → business info + website URL
        2. If website exists → extract menu/products
        3. If no website → use Places data only
        """
        pass
```

#### Layer 3: Data Normalization
```python
class DataNormalizer:
    """Convert extracted data to iHhashi schema"""
    
    def normalize_price(self, raw_price: str) -> float:
        # Handle: "R150", "R 150.00", "150 ZAR", "$10", etc.
        # Convert to ZAR if needed
        pass
    
    def categorize_product(self, name: str, description: str) -> str:
        # AI categorization: Burgers, Pizza, Groceries, etc.
        pass
    
    def extract_operating_hours(self, raw_hours: str) -> dict:
        # Parse various formats to standard schedule
        pass
```

### API Endpoints

```python
# New routes for quantum onboarding

@router.post("/merchant/quantum-discover")
async def quantum_discover(input: str):
    """
    Step 1: Discover merchant from URL or name+location
    Returns: preview of extracted data (not saved)
    """
    pass

@router.post("/merchant/quantum-onboard")
async def quantum_onboard(input: str, edits: dict = None):
    """
    Step 2: Create merchant with extracted data
    Allows merchant to review/edit before saving
    """
    pass

@router.post("/merchant/quantum-refresh")
async def quantum_refresh(merchant_id: str):
    """
    Re-extract data from original source
    Useful for menu updates, price changes
    """
    pass
```

### Supported Merchant Types

| Type | Primary Source | Secondary Sources |
|------|----------------|-------------------|
| Restaurants | Website menu, TripAdvisor | Google Places |
| Grocery Stores | Website catalog | Google Business |
| Spaza Shops | Manual (limited web presence) | WhatsApp catalog |
| Bakeries | Website, Instagram | Google Places |
| Butcheries | Website price list | Facebook page |

---

## Part 2: Quantum Capabilities for Zo (Myself)

### Problem
- I waste time on repetitive research tasks
- I don't have persistent "muscle memory" for extraction
- Each conversation starts fresh without learned patterns

### Solution: Embedded Quantum Skills

#### Skill 1: `quantum-extractor`
```typescript
// Skills/quantum-extractor/SKILL.md
/**
 * name: quantum-extractor
 * description: Instant structured data extraction from URLs
 * 
 * Usage:
 *   bun scripts/extract.ts --url "https://..." --schema "product"
 *   bun scripts/extract.ts --url "https://..." --prompt "Extract menu items"
 */

// Capabilities:
// - Extract products, prices, descriptions
// - Extract business contact info
// - Extract social media links
// - Extract operating hours
// - Convert to any schema
```

#### Skill 2: `quantum-research`
```typescript
// Skills/quantum-research/SKILL.md
/**
 * name: quantum-research
 * description: Autonomous research agent for competitive intelligence
 * 
 * Usage:
 *   bun scripts/research.ts --topic "Uber Eats pricing strategy in SA"
 *   bun scripts/research.ts --competitor "Mr D Food"
 */
```

#### Skill 3: `quantum-sync`
```typescript
// Skills/quantum-sync/SKILL.md
/**
 * name: quantum-sync
 * description: Keep external data in sync with local models
 * 
 * Usage:
 *   bun scripts/sync.ts --merchant "uuid" --refresh-menu
 *   bun scripts/sync.ts --watch --interval 3600
 */
```

### Implementation: Firecrawl Integration

Firecrawl is the best option for quantum extraction because:
1. **Agent-native**: Built for AI agents with MCP support
2. **Structured output**: Extract to JSON schema directly
3. **Search + Scrape**: Combined in single API
4. **Cost-effective**: ~$0.002/page vs competitors

```bash
# Install Firecrawl skill for Zo
npx -y firecrawl-cli@latest init --all --browser
```

### My Quantum Workflow

```
User Request: "Check competitor pricing"
         │
         ▼
┌─────────────────────────┐
│ 1. quantum-research     │
│    - Search competitors │
│    - Find pricing pages │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. quantum-extractor    │
│    - Extract pricing    │
│    - Normalize to ZAR   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. Analysis & Report    │
│    - Compare with iHhashi│
│    - Recommend actions  │
└─────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create `quantum-extractor` skill for myself
- [ ] Add Firecrawl API key to secrets
- [ ] Test extraction on 10 sample SA restaurant websites

### Phase 2: Backend Integration (Week 2)
- [ ] Add quantum routes to iHhashi backend
- [ ] Create MerchantProfile model with extraction fields
- [ ] Build extraction pipeline with fallbacks

### Phase 3: Frontend (Week 3)
- [ ] Merchant onboarding UI with "Import from URL" option
- [ ] Preview/edit extracted data before saving
- [ ] Progress indicator for extraction

### Phase 4: Polish (Week 4)
- [ ] Add Google Places integration
- [ ] Handle edge cases (no website, anti-scraping)
- [ ] Add refresh/sync capabilities

---

## Cost Estimates

| Service | Cost | Usage |
|---------|------|-------|
| Firecrawl | $0.002/page | 1000 extractions = $2 |
| Google Places API | $7/1000 calls | For name+location discovery |
| Scrapfly (fallback) | $0.005/page | When Firecrawl fails |

**Estimated monthly cost**: $20-50 for 10,000 merchant extractions

---

## Security & Ethics

1. **Rate Limiting**: Respect robots.txt and rate limits
2. **Data Ownership**: Merchants own their data, extraction is opt-in
3. **Attribution**: Link back to original sources where appropriate
4. **Updates**: Allow merchants to disconnect auto-sync anytime

---

## Quick Wins

### For Merchants (Immediate)
- Add "Import from URL" button to merchant signup
- Auto-populate business hours from Google
- Suggest categories based on business type

### For Me (Immediate)
- Install Firecrawl skill
- Create extraction templates for common use cases
- Add extraction memory to vault
