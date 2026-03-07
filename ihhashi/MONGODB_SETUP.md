# MongoDB Atlas Setup for iHhashi

## ✅ MongoDB Connection Configured

Your MongoDB Atlas database is now configured with these settings:

| Setting | Value |
|---------|-------|
| **Connection String** | `mongodb+srv://teacherchris37_db_user:iHhashi1!!!@cluster0.ai5z7wq.mongodb.net/ihhashi?retryWrites=true&w=majority` |
| **Database Name** | `ihhashi` |
| **Cluster** | cluster0.ai5z7wq.mongodb.net |
| **Username** | teacherchris37_db_user |

---

## 📁 Environment Files Created

The following files have been created with your MongoDB connection:

| File | Purpose |
|------|---------|
| `backend/.env` | Main environment file (used for local & production) |
| `backend/.env.production` | Production-specific settings |
| `backend/.env.development` | Development-specific settings |

---

## 🚀 Deploy with MongoDB

### Option 1: Automatic Setup Script

```bash
# Run this to configure MongoDB in Railway
./deployment/scripts/setup-mongodb.sh
```

### Option 2: Manual Railway Dashboard

1. Go to https://railway.app
2. Select your project
3. Go to **Variables** tab
4. Add these variables:

```
MONGODB_URL=mongodb+srv://teacherchris37_db_user:iHhashi1!!!@cluster0.ai5z7wq.mongodb.net/ihhashi?retryWrites=true&w=majority
MONGODB_URI=mongodb+srv://teacherchris37_db_user:iHhashi1!!!@cluster0.ai5z7wq.mongodb.net/ihhashi?retryWrites=true&w=majority
DB_NAME=ihhashi
```

5. Click **Deploy** to restart the service

---

## 🔒 IMPORTANT: MongoDB Atlas Network Access

### Allow Railway to Connect

You MUST configure MongoDB Atlas to allow connections from Railway:

1. Go to https://cloud.mongodb.com
2. Select your cluster
3. Click **Network Access** (left sidebar)
4. Click **Add IP Address**
5. Choose one of these options:

**Option A - Allow from anywhere (easiest, less secure):**
- Click **Allow Access from Anywhere**
- Click **Confirm**

**Option B - Allow specific IPs (more secure):**
- Find Railway's outbound IP ranges
- Add them one by one
- Or use Railway's provided static IP (if on Pro plan)

---

## 🧪 Test the Connection

### Local Test
```bash
cd backend

# Install MongoDB shell (if not installed)
npm install -g mongosh

# Test connection
mongosh "mongodb+srv://teacherchris37_db_user:iHhashi1!!!@cluster0.ai5z7wq.mongodb.net/ihhashi"
```

### After Railway Deploy
```bash
# Check health endpoint
curl https://your-app.up.railway.app/health

# Should return:
# {
#   "status": "healthy",
#   "database": {"status": "healthy"},
#   ...
# }
```

---

## 📊 MongoDB Atlas Dashboard

Monitor your database at:
- **URL**: https://cloud.mongodb.com/v2/5f8f8f8f8f8f8f8f8f8f8f8f
- **Metrics**: Database performance, connections, storage
- **Collections**: View your data

---

## 🆘 Troubleshooting

### "Connection refused" or "Network timeout"
→ Check Network Access settings in MongoDB Atlas (see above)

### "Authentication failed"
→ Verify username/password in connection string

### "Database not found"
→ The database will be created automatically on first write

### Railway deployment fails
```bash
# Check logs
railway logs

# Redeploy
railway up
```

---

## 🔧 Advanced: Separate Databases

If you want separate databases for different environments:

| Environment | Database Name |
|-------------|---------------|
| Production | `ihhashi` |
| Staging | `ihhashi_staging` |
| Development | `ihhashi_dev` |

Update the `DB_NAME` environment variable accordingly.

---

**Last Updated**: March 2026  
**MongoDB Version**: 7.0 (Atlas)
