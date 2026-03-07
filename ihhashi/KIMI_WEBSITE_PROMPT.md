# iHhashi Food Delivery Web App - Complete Build Prompt

## Overview
Build a food delivery web application for South Africa called "iHhashi" with a black and yellow/gold color scheme. This is a mobile-first PWA with three user roles: customers, merchants/vendors, and delivery riders.

## Color Scheme (CRITICAL - Use Exactly)
- **Primary**: Gold/Yellow `#FFD700` 
- **Secondary/Background**: Black `#1A1A1A`
- **Text on Dark**: White `#FFFFFF`
- **Text on Light**: Black `#1A1A1A`
- **Gray Background**: `#F5F5F5` or `bg-gray-50`
- **Success Green**: `#22C55E`
- **Card Shadow**: `0 2px 8px rgba(0, 0, 0, 0.08)`

## Typography
- **Font Family**: Inter (Google Fonts)
- **Sizes**: 12px (small), 14px (body), 16px (medium), 18px (large), 20px (heading), 24px (hero)

## App Structure

### 1. Splash Screen (First Load)
- Full screen gold/yellow background (`bg-yellow-400` or `#FFD700`)
- Centered logo: Large yellow circle with black "H" letter, text "iHhashi" in black
- Tagline: "Food Delivery SA" in black text below
- Three bouncing dots loading indicator (black)
- Auto-fades after 1.8 seconds

### 2. Home Page (Customer View)

#### Header (Sticky, Black Background)
- Logo on left: Yellow rounded square with black "H" + "iHhashi" in white
- "Sign In" or "Profile" link on right (white text)
- Search bar below: White background, rounded-xl, placeholder "Search food, groceries, fruits..."

#### Hero Banner
- Gold/yellow gradient background
- Text: "Fast delivery in 30-45 mins" (bold, black)
- Subtext: "Food, groceries, fruits & vegetables delivered fresh"
- Button: Black background, gold text, "Start Shopping" with chevron icon

#### Categories Section (Horizontal Scroll)
- Title: "Categories" with "See all" link
- 5 category cards with icons:
  - 🍔 Food (orange-100 background)
  - 🛒 Groceries (green-100 background) 
  - 🍎 Fruits (red-100 background)
  - 🥬 Veggies (emerald-100 background)
  - 🥛 Dairy (blue-100 background)
- Each: 70px wide, 14px emoji, 12px label below

#### Popular Merchants Section
- Title: "Popular Near You" with "See all" link
- Merchant cards (vertical list):
  - Left: Square image (placeholder colored boxes)
  - Right: Name (bold), category (gray), star rating badge (gold), delivery time, delivery fee
  - Card: White background, rounded-2xl, subtle shadow

#### Featured Products Section
- Title: "Featured Items" with "See all" link
- 2-column grid of product cards:
  - Square product image (placeholder)
  - Product name, merchant name (gray)
  - Price in gold/yellow (R format: R149)
  - "Add" button (black background, gold text, rounded-lg)

#### Bottom Navigation (Fixed)
- 4 icons: Home (active - gold), Browse/Search, Orders/Cart, Profile
- White background, border-top gray
- Active state: Gold icon + text

### 3. Products/Catalog Page
- Header with back arrow, search bar
- Category filter chips (horizontal scroll)
- Product grid (2 columns)
- Each product card same as home page featured items

### 4. Merchant Detail Page
- Hero image at top (colored placeholder)
- Merchant name, rating, delivery info
- Menu categories tabs
- Product list with add buttons
- Sticky "View Cart" button at bottom when items added

### 5. Cart Page
- Header with back arrow, "Cart" title
- List of cart items with quantity controls (+/-)
- Item image, name, price
- Delivery fee, service fee lines
- Total (bold)
- Checkout button (full width, black bg, gold text)

### 6. Auth/Sign In Page
- Gold header with logo
- Phone number input (South Africa format)
- "Send OTP" button (black bg, gold text)
- OR divider
- "Continue as Guest" link

### 7. Orders Page
- Tabs: Active, Past
- Order cards with:
  - Merchant name, order number
  - Status badge (color coded)
  - Items summary
  - Total, "Track Order" or "Reorder" button

### 8. Profile Page
- User info section (gold background)
- Menu items (white cards):
  - My Orders
  - Saved Addresses
  - Payment Methods
  - Settings
  - Help & Support
  - Logout (red text)

### 9. Merchant Dashboard (Different Layout)
- Stats cards row (Orders, Revenue, Rating)
- Tab navigation: Orders, Menu, Analytics
- Orders list with accept/reject buttons
- Green/red action buttons

### 10. Rider Dashboard (Different Layout)
- Online/Offline toggle
- Available orders list
- Map placeholder area
- Earnings stats
- "Accept Delivery" buttons

## Key UI Components to Build

### Buttons
1. **Primary**: Black background (`bg-secondary-600` or `#1A1A1A`), gold text (`text-primary` or `#FFD700`), rounded-xl, px-4 py-2
2. **Secondary**: Gold background, black text
3. **Add Button**: Small, black bg, gold text, rounded-lg, "Add" text
4. **Ghost**: Transparent with border

### Cards
- White background (`bg-white`)
- Border radius: `rounded-2xl` (16px)
- Shadow: `shadow-card` (0 2px 8px rgba(0,0,0,0.08))
- Hover: `shadow-card-hover`

### Inputs
- White background
- Rounded-xl
- Gray placeholder text
- Focus ring: gold/yellow

### Navigation
- Fixed bottom nav on mobile
- Sticky top header
- Back arrows on inner pages

## Responsive Behavior
- Mobile-first (max-width: 640px ideal)
- Max container width: 512px (max-w-lg)
- Center content on larger screens with gray background

## Animations
- Page transitions: fade in
- Cards: hover shadow lift
- Loading: bouncing dots
- Splash screen: fade out

## Placeholder Images
Use colored placeholders with text:
- Format: `https://placehold.co/{width}x{height}/{bgColor}/{textColor}?text={text}`
- Examples:
  - KFC: `https://placehold.co/200x120/FFD700/1A1A1A?text=KFC`
  - Fresh Market: `https://placehold.co/200x120/22C55E/white?text=Fresh`
  - Product: `https://placehold.co/200x200/FFD700/1A1A1A?text=🍗`

## Icons to Include
- Search (magnifying glass)
- Shopping Cart
- Home
- User/Profile
- Clock (delivery time)
- Star (rating)
- ChevronRight (navigation)
- Plus/Minus (quantity)
- MapPin (location)
- Phone
- Settings

## Technical Requirements
- Single HTML file output
- Tailwind CSS via CDN
- React via CDN (or vanilla JS if not possible)
- Mobile-responsive
- Smooth scrolling
- Touch-friendly tap targets (min 44px)

## Data to Mock
Sample merchants:
1. KFC Rosebank - Fast Food - 4.8★ - 20-30 min - R15 delivery
2. Fresh Market - Groceries - 4.6★ - 30-45 min - R20 delivery
3. Fruit Republic - Fruits - 4.9★ - 25-35 min - R12 delivery
4. Veggie King - Vegetables - 4.7★ - 35-50 min - R18 delivery

Sample products:
1. Chicken Bucket (8pc) - R149 - KFC
2. Fresh Apples (1kg) - R35 - Fruit Republic
3. Full Cream Milk (2L) - R42 - Fresh Market
4. Mixed Veggies Pack - R55 - Veggie King

## Page Routing (Single Page App)
Implement as SPA with hash routing or show each page as separate section:
- `#/` - Home
- `#/products` - Products catalog
- `#/merchant/:id` - Merchant detail
- `#/cart` - Shopping cart
- `#/auth` - Sign in
- `#/orders` - Orders
- `#/profile` - Profile
- `#/merchant-dashboard` - Merchant view
- `#/rider-dashboard` - Rider view

## Deliverable
Build a complete, working prototype that can be previewed. All buttons should be clickable and navigate between views. Use mock data for everything. The design should be pixel-perfect to the description above with the exact gold (#FFD700) and black (#1A1A1A) color scheme.
