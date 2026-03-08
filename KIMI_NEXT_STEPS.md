# 🎯 KIMI: Next Steps - Finish MasterBuilder7

## ✅ WHAT'S DONE (Zo completed)
- REAL_BUILDER.py - Uses subprocess.run(), no more sleep()
- REAL_ORCHESTRATOR.py - Real deployment orchestration
- ship script - One command: `./ship all`

## 🔧 WHAT YOU (Kimi) MUST FIX

### 1. Google Play Store Deployment
**File to create**: `google_play_deploy.py`
**Must do**:
- Use Google Play Developer API v3
- Upload AAB to internal track
- Support promotion to alpha/beta/production
- Handle service account auth

**Code skeleton**:
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

def upload_to_play(aab_path, package_name, track="internal"):
    credentials = service_account.Credentials.from_service_account_file(
        'service-account.json',
        scopes=['https://www.googleapis.com/auth/androidpublisher']
    )
    service = build('androidpublisher', 'v3', credentials=credentials)
    
    # Create edit
    edit = service.edits().insert(packageName=package_name).execute()
    edit_id = edit['id']
    
    # Upload bundle
    with open(aab_path, 'rb') as f:
        service.edits().bundles().upload(
            packageName=package_name,
            editId=edit_id
        ).execute()
    
    # Commit
    service.edits().commit(
        packageName=package_name,
        editId=edit_id
    ).execute()
```

### 2. Add Error Recovery
**File to modify**: `REAL_ORCHESTRATOR.py`
**Add**:
- Retry logic (3 attempts with exponential backoff)
- Checkpoint after each successful step
- Rollback on failure
- State persistence to disk

### 3. Durable State (Redis/JSON)
**File to create**: `state_manager.py`
**Must do**:
- Save build state to JSON file
- Load state on restart
- Prevent duplicate deployments

### 4. Integration Test
**Command to run**:
```bash
cd /home/workspace/iHhashi
../MasterBuilder7/ship android
```

**Expected**: Actually runs npm install, gradle build, produces AAB

## 🚀 CRITERIA FOR "DONE"
- [ ] Running `./ship android` builds real iHhashi AAB
- [ ] Running `./ship backend` deploys to Render
- [ ] Running `./ship icp` deploys to Internet Computer
- [ ] Running `./ship all` does all three
- [ ] Each step shows REAL output (not sleep + mock)
- [ ] Failures show actual error messages

## 📝 COMMIT MESSAGE
```
🔥 PRODUCTION: Real deployment pipeline
- Google Play Store API integration
- Render deployment working
- ICP deployment working
- Error recovery + retries
- Durable state persistence
```

## ⚡ URGENCY
This must work TODAY. No more mock data. Real commands only.

**Test after every change.**
