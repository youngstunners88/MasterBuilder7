# ✅ iHhashi Setup Complete - Next Steps

Your MongoDB Atlas database is **configured and ready**!

---

## 🔥 QUICK START (Choose One)

### Option A: One-Command Deploy (Easiest)

```bash
./deployment/scripts/quick-start.sh
```

Then select **Option 1** for full deployment.

---

### Option B: Step-by-Step Commands

**Step 1: Install CLI Tools**

Open Terminal/Command Prompt and paste:

```bash
npm install -g @railway/cli netlify-cli
```

**Step 2: Login to Services**

```bash
# Login to Railway
railway login

# Login to Netlify
netlify login
```

**Step 3: Deploy Backend to Railway**

```bash
cd backend

# Link to your Railway project
railway link

# Set MongoDB connection (ALREADY CONFIGURED IN FILES)
railway variables set MONGODB_URL="mongodb+srv://teacherchris37_db_user:iHhashi1!!!@cluster0.ai5z7wq.mongodb.net/ihhashi?retryWrites=true&w=majority"

# Deploy
railway up
```

**Step 4: Deploy Frontend to Netlify**

```bash
cd ../frontend

# Install dependencies
npm install

# Build the app
npm run build

# Link to your Netlify site
netlify link

# Deploy
netlify deploy --prod --dir=dist
```

---

## ⚙️ CRITICAL: MongoDB Network Access

**You MUST do this or your app won't work:**

1. Go to https://cloud.mongodb.com
2. Click **Network Access** (left sidebar)
3. Click **Add IP Address**
4. Click **Allow Access from Anywhere**
5. Click **Confirm**

![MongoDB Network Access](https://i.imgur.com/example.png)

---

## 📋 Environment Variables Status

### ✅ Already Configured

| Variable | Status | Location |
|----------|--------|----------|
| `MONGODB_URL` | ✅ Set | `backend/.env` |
| `MONGODB_URI` | ✅ Set | `backend/.env` |
| `DB_NAME` | ✅ Set | `backend/.env` |
| `GLITCHTIP_DSN` | ✅ Set | `backend/.env` |

### ⚠️ Still Need to Configure

| Variable | Why | Where to Get |
|----------|-----|--------------|
| `SUPABASE_URL` | User authentication | https://supabase.com/dashboard |
| `SUPABASE_ANON_KEY` | User authentication | Supabase Dashboard > Settings > API |
| `CORS_ORIGINS` | Security | Your Netlify URL |
| `VITE_API_URL` | Frontend API calls | Your Railway URL |

---

## 🔧 Set Remaining Variables (Railway)

After your first deploy, set these in Railway Dashboard:

```bash
# 1. Get your Railway URL
railway domain

# Example output: https://ihhashi-api.up.railway.app
```

Then go to Railway Dashboard → Your Project → Variables and add:

```
CORS_ORIGINS=https://your-netlify-site.netlify.app
```

---

## 🧪 Test Everything

After deployment, test with:

```bash
# Test backend
curl https://your-railway-app.up.railway.app/health

# Should return:
# {"status":"healthy","database":{"status":"healthy"}}
```

Open your Netlify URL in browser and check:
- No red errors in console
- Can connect to API

---

## 📁 Files Created/Updated

```
backend/
├── .env                    ✅ Created with MongoDB
├── .env.production         ✅ Created
├── .env.development        ✅ Created
└── app/config.py          ✅ Updated for MONGODB_URI

deployment/
├── scripts/
│   └── setup-mongodb.sh   ✅ Created
├── README.md              ✅ Exists
└── GITHUB_SECRETS.md      ✅ Exists

MONGODB_SETUP.md           ✅ Created
SETUP_COMPLETE.md          ✅ This file
```

---

## 🆘 Need Help?

### Check Configuration
```bash
./deployment/scripts/verify-deployment.sh
```

### View Logs
```bash
# Railway logs
railway logs --follow

# Netlify logs
netlify logs
```

### Common Issues

**"Cannot connect to MongoDB"**
→ Did you set Network Access to "Allow from Anywhere" in MongoDB Atlas?

**"CORS error"**
→ Add your Netlify URL to `CORS_ORIGINS` in Railway variables

**"Build failed"**
→ Check `railway logs` for errors

---

## 🎯 Summary

✅ MongoDB Atlas configured  
✅ Environment files created  
✅ Backend ready for Railway  
✅ Frontend ready for Netlify  
✅ Deployment scripts ready  

**Next: Run the deploy command!**

```bash
./deployment/scripts/quick-start.sh
```

Or manually:
```bash
cd backend && railway up
cd ../frontend && npm run build && netlify deploy --prod
```

---

**Your MongoDB**: `mongodb+srv://teacherchris37_db_user:****@cluster0.ai5z7wq.mongodb.net/ihhashi`  
**Status**: Ready to deploy! 🚀
