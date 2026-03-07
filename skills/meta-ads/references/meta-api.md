# Meta Marketing API Reference

Quick reference for the Meta Marketing API endpoints used by NullClaw Meta Ads Kit.

## Authentication

All requests require an access token with appropriate permissions:
- `ads_management` - Full ad management
- `ads_read` - Read-only access
- `pages_read_engagement` - Read page content

```bash
curl -X GET "https://graph.facebook.com/v21.0/{endpoint}?access_token={token}"
```

## Key Endpoints

### Ad Account

```
GET /{ad_account_id}
GET /{ad_account_id}/campaigns
GET /{ad_account_id}/adsets
GET /{ad_account_id}/ads
GET /{ad_account_id}/insights
POST /{ad_account_id}/campaigns
POST /{ad_account_id}/adsets
POST /{ad_account_id}/ads
POST /{ad_account_id}/adcreatives
```

### Campaigns

```bash
# Get active campaigns
GET /{ad_account_id}/campaigns?filtering=[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]

# Pause campaign
POST /{campaign_id}
{"status": "PAUSED"}

# Update budget
POST /{campaign_id}
{"daily_budget": 5000}  # in cents
```

### Insights

```bash
# Campaign-level insights
GET /{ad_account_id}/insights?level=campaign&date_preset=last_7d&fields=campaign_id,campaign_name,spend,impressions,clicks,actions,ctr,frequency

# Ad-level insights
GET /{ad_account_id}/insights?level=ad&date_preset=last_7d&fields=ad_id,ad_name,spend,actions,ctr,frequency

# Date presets
- today
- yesterday
- last_3d
- last_7d
- last_14d
- last_30d
- last_90d
- lifetime
```

### Ad Creative

```bash
# Create link ad creative
POST /{ad_account_id}/adcreatives
{
  "name": "Creative Name",
  "object_story_spec": {
    "page_id": "{page_id}",
    "link_data": {
      "message": "Ad body text",
      "link": "https://example.com",
      "name": "Headline",
      "description": "Link description",
      "call_to_action": {"type": "LEARN_MORE"},
      "image_hash": "{image_hash}"
    }
  }
}
```

### Create Ad

```bash
POST /{ad_account_id}/ads
{
  "name": "Ad Name",
  "adset_id": "{adset_id}",
  "creative": {"creative_id": "{creative_id}"},
  "status": "PAUSED"
}
```

## Key Fields

### Insights Fields

| Field | Description |
|-------|-------------|
| `spend` | Amount spent |
| `impressions` | Number of times ads shown |
| `clicks` | Total clicks |
| `ctr` | Click-through rate |
| `frequency` | Average times each person saw ad |
| `actions` | Array of action types and counts |
| `cost_per_action_type` | Cost per action |
| `cpc` | Cost per click |
| `cpm` | Cost per 1000 impressions |
| `reach` | Unique people reached |

### Action Types

| Type | Description |
|------|-------------|
| `purchase` | Purchases |
| `omni_purchase` | Cross-device purchases |
| `lead` | Lead forms submitted |
| `landing_page_view` | Landing page views |
| `link_click` | Link clicks |
| `video_view` | Video views |
| `page_engagement` | Page engagements |

## Rate Limits

- Standard: 200 calls/hour per ad account
- Insights: 60 calls/minute
- Use `filtering` to batch requests

## Best Practices

1. **Use date presets** instead of absolute dates when possible
2. **Batch requests** using `filtering` parameter
3. **Cache insights** - they don't change for past dates
4. **Handle pagination** with `limit` and `after` cursors
5. **Retry with backoff** on rate limit errors

## Error Handling

```json
{
  "error": {
    "message": "Invalid parameter",
    "type": "OAuthException",
    "code": 100,
    "error_subcode": 1885024
  }
}
```

Common error codes:
- 100: Invalid parameter
- 190: Access token expired
- 17: API limit reached
- 2: Temporary API error

## Resources

- [Meta Marketing API Docs](https://developers.facebook.com/docs/marketing-apis)
- [Marketing API Reference](https://developers.facebook.com/docs/marketing-api/reference)
- [Insights API](https://developers.facebook.com/docs/marketing-api/insights)
- [Ad Creative](https://developers.facebook.com/docs/marketing-api/creative)
