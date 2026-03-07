# Nduna Bot - Future Features Roadmap

> Last updated: 2026-03-04
> Current version: 0.5.0

## High Priority

### 1. Order Placement via Chat
**Status**: Planned
**Priority**: High
**Estimated effort**: 2-3 weeks

**Description**:
Enable Nduna to place orders directly through natural language conversation.

**Example commands**:
- "Get me a coke and a chicken burger from Thembis Chicken"
- "Order 2x milk and bread from the closest supermarket"
- "I want a large pepperoni pizza from Pizza Place"

**Requirements**:
- [ ] Natural language item parsing (extract items, quantities, modifiers)
- [ ] Merchant matching and verification
- [ ] Product availability checking
- [ ] Cart management (add/update/remove items)
- [ ] Checkout flow integration
- [ ] Payment gateway integration (PayStack/Yoco)
- [ ] Order confirmation and tracking
- [ ] Error handling (out of stock, closed, etc.)

**Technical approach**:
1. Add function calling tools: `add_to_cart`, `remove_from_cart`, `checkout`, `get_order_status`
2. Integrate with existing iHhashi order API
3. Add payment confirmation flow
4. Support both registered and guest users

**Dependencies**:
- Payment gateway setup
- Order API endpoints ready
- User authentication flow

---

### 2. South African Male Voice (TTS)
**Status**: Planned
**Priority**: Medium
**Estimated effort**: 1 week

**Description**:
Give Nduna a male South African voice for text-to-speech responses.

**Requirements**:
- [ ] Select TTS provider with SA accent support
- [ ] Configure male voice profile
- [ ] Integrate with Nduna response flow
- [ ] Add voice response endpoint
- [ ] Support WhatsApp voice notes

**Provider options**:

| Provider | SA Accent | Custom Voice | Cost |
|----------|-----------|--------------|------|
| ElevenLabs | Yes (can clone) | Yes | $$$ |
| Google TTS | Limited | No | $ |
| Azure TTS | Limited | Yes | $$ |
| Amazon Polly | No | No | $ |

**Recommended**: ElevenLabs
- Can clone a real SA male voice
- High quality natural speech
- API integration available
- Custom voice creation (~$5/month)

**Technical approach**:
1. Record or source SA male voice samples
2. Train custom voice on ElevenLabs
3. Add `/nduna/voice-response` endpoint
4. Return audio file with response
5. WhatsApp: send as voice note

---

### 3. Live Avatar - Real-time Conversational Agent
**Status**: Research & Planning
**Priority**: High
**Estimated effort**: 4-6 weeks

**Description**:
Transform Nduna into a live, interactive avatar that delivery servicemen, customers, and merchants can speak to in real time - similar to ChatGPT's Advanced Voice Mode or digital human assistants.

**User Experience**:
- User opens Nduna in app or WhatsApp
- Sees animated avatar (the Nduna character from branding)
- Speaks naturally - avatar responds with voice + lip-sync
- Real-time back-and-forth conversation
- Can handle orders, questions, support issues

**Technical Feasibility Analysis**:

#### Groq API Capabilities
| Component | Groq Support | Notes |
|-----------|--------------|-------|
| Speech-to-Text | ✓ Whisper-large-v3-turbo | Very fast, already integrated |
| LLM Inference | ✓ Llama 3.1/3.2 | Extremely fast on LPU |
| Text-to-Speech | ✗ Not available | Need external provider |
| Avatar Generation | ✗ Not available | Need external service |
| Streaming Audio | Partial | Can stream text, not audio |

**Conclusion**: Groq is excellent for the "brain" (STT + LLM) but cannot handle voice output or avatar rendering alone. We need a hybrid architecture.

---

**Architecture Options**:

#### Option A: Full Pipeline (Recommended for MVP)
```
[User Audio] → Groq Whisper (STT) → Groq Llama (LLM) → ElevenLabs (TTS) → D-ID/Sadalkar (Avatar) → [User]
```

**Latency**: 2-4 seconds per turn
**Cost**: Moderate ($0.02-0.05 per minute)
**Quality**: High

**Pros**:
- Uses existing Groq integration
- Best-in-class TTS (ElevenLabs with SA voice clone)
- Professional avatar generation (D-ID)
- Feasible with current tech

**Cons**:
- Not truly "real-time" - slight delay
- Multiple API calls = more points of failure
- Cost adds up at scale

---

#### Option B: Real-time Voice Mode (Lower Latency)
```
[User Audio Stream] → WebSocket → Groq Whisper → Groq Llama (streaming) → ElevenLabs (streaming TTS) → [Audio Stream]
```
Plus: Simple animated avatar (pre-rendered loops with basic lip-sync)

**Latency**: 1-2 seconds
**Cost**: Lower (no video generation)
**Quality**: Good voice, simpler avatar

**Pros**:
- Near real-time feel
- Lower cost
- Simpler infrastructure

**Cons**:
- Avatar less impressive (2D animation vs video)
- More complex WebSocket handling

---

#### Option C: Full Digital Human (Premium)
Use specialized digital human platforms:
- **UneeQ** - Enterprise digital humans
- **Soul Machines** - AI avatars with emotional intelligence
- **D-ID** - Real-time avatar API

**Latency**: 1-3 seconds
**Cost**: High ($500-2000/month + usage)
**Quality**: Premium, enterprise-grade

**Pros**:
- Production-ready
- Professional appearance
- Full support

**Cons**:
- Expensive at scale
- Less customization
- Vendor lock-in

---

**Recommended Approach**: Hybrid (Option A + B)

**Phase 1**: Voice-first with simple avatar
- Groq Whisper for STT (already integrated)
- Groq Llama for fast inference
- ElevenLabs for TTS with SA male voice
- Simple 2D avatar animation (pre-rendered expressions)

**Phase 2**: Video avatar
- D-ID or Sadalkar for realistic lip-sync
- Full body avatar video
- Real-time rendering

**Phase 3**: Real-time streaming
- WebSocket for continuous audio
- Interruptible responses
- Full duplex conversation

---

**Technical Requirements**:

**Backend**:
- [ ] WebSocket server for real-time audio streaming
- [ ] Audio buffer management (handle interruptions)
- [ ] Streaming response generation
- [ ] Session state management
- [ ] Rate limiting per user

**External Services**:
- [ ] ElevenLabs account + SA voice clone
- [ ] D-ID or Sadalkar API access
- [ ] CDN for avatar video delivery

**Frontend (App)**:
- [ ] WebRTC or WebSocket audio capture
- [ ] Audio playback with visualization
- [ ] Avatar rendering component
- [ ] Offline mode fallback

**WhatsApp Integration**:
- [ ] Voice note processing (already exists)
- [ ] Send audio responses as voice notes
- [ ] Avatar video as MP4 (may have size limits)

---

**Cost Estimates** (per 1000 users, 5 min conversation each):

| Service | Cost Estimate |
|---------|---------------|
| Groq (STT + LLM) | ~$50 |
| ElevenLabs (TTS) | ~$100 |
| D-ID (Avatar) | ~$200 |
| **Total** | ~$350 per 1000 users |

*Note: Costs decrease with volume negotiations*

---

**Key Challenges**:

1. **Latency**: Minimizing delay between user speech and avatar response
   - Solution: Streaming at each step, parallel processing

2. **Data costs for users**: Video/audio uses significant data
   - Solution: Audio-only option, low-res avatar, WiFi preloading

3. **SA accent accuracy**: Getting natural SA voice
   - Solution: ElevenLabs voice cloning with SA voice samples

4. **Scale**: Handling many concurrent conversations
   - Solution: Queue system, load balancing, caching common responses

5. **WhatsApp limitations**: No real-time streaming on WhatsApp
   - Solution: Send voice notes, maybe short video clips

---

**Dependencies**:
- ElevenLabs integration (can start TTS without avatar)
- WebSocket infrastructure
- Avatar asset creation (video/animation files)

**Related Features**:
- South African Male Voice (Section 2) - prerequisite
- Multi-language Voice Support (Section 3)

---

## Medium Priority

### 4. Multi-language Voice Support
**Status**: Planned
**Priority**: Medium

Support voice input/output in all 11 SA languages:
- Zulu, Xhosa, Afrikaans, English
- Sepedi, Setswana, Sesotho
- Tsonga, Swati, Venda, Ndebele

### 5. Order History & Reordering
**Status**: Planned
**Priority**: Medium

- "Order the same as last time"
- "What did I order from [merchant] before?"
- Quick reorder buttons

### 6. Smart Suggestions
**Status**: Planned
**Priority**: Medium

Context-aware suggestions based on:
- Time of day (breakfast, lunch, dinner)
- Weather (cold drinks on hot days)
- Past orders
- Location

---

## Low Priority / Ideas

### 7. Group Ordering
Multiple people can add to same order via shared link

### 8. Subscription Orders
"Every Monday morning, order me a coffee from [place]"

### 9. Voice Ordering Flow
Full voice-first ordering experience:
1. User speaks order
2. Nduna confirms via voice
3. User confirms via voice
4. Payment via saved method
5. Status updates via voice notes

---

## Completed Features

| Feature | Version | Date |
|---------|---------|------|
| Basic chat with LLM | 0.1.0 | 2026-01 |
| WhatsApp integration | 0.2.0 | 2026-01 |
| Multi-language support (7 languages) | 0.3.0 | 2026-02 |
| Product browsing with function calling | 0.5.0 | 2026-02-19 |
| Voice input (STT) | 0.5.0 | 2026-02-19 |

---

## Notes

- Keep user experience simple - natural language should feel natural
- Voice features should complement text, not replace
- Payment integration is critical for order placement
- Consider data costs for voice features in SA market
