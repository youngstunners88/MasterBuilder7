# The Pivot: Boober → iHhashi

## Timeline

| Date | Event |
|------|-------|
| 2025 | Boober started - ride-hailing app for South Africa |
| 2026-02-25 | **PIVOT** to iHhashi - food delivery platform |

## Why We Pivoted

1. **Regulatory Barriers** - Ride-hailing requires transport licenses, insurance, driver vetting
2. **Faster Revenue** - Food delivery has quicker onboarding for merchants vs drivers
3. **Market Gap** - Order.in dominates but has poor UX; Uber Eats limited to cities
4. **Lower Risk** - No passenger safety liability

## What Stayed the Same

- Tech stack (FastAPI + MongoDB + React)
- South Africa focus
- Location-based matching
- Mobile-first approach
- Team and vision

## What Changed

| Boober | iHhashi |
|--------|---------|
| Drivers | Riders (delivery) |
| Passengers | Customers |
| Trips | Orders |
| Fare calculation | Order totals + delivery fees |
| Vehicle types | Delivery methods (bike, car, walker) |

## Legacy Files

The following directories contain **archived Boober code** - DO NOT use for iHhashi:
- `/home/workspace/Boober/`
- `/home/workspace/rideshare/Boober-main/`
- `/home/workspace/Boober_*.zip` files
- `/home/workspace/boober-posthog-guide.md`

**Current active project**: `/home/workspace/iHhashi/`

## For AI Assistants

When working on this project:
- You are building a **food delivery app**, NOT a ride-hailing app
- Use terminology: Order, Merchant, Rider, Customer (NOT Trip, Driver, Passenger)
- Reference iHhashi docs, not Boober
- The matching service is for assigning riders to deliveries, not drivers to passengers
