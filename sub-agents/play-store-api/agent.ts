#!/usr/bin/env bun
/**
 * PLAY STORE API AGENT
 * Mission: Create Google Play Service Account and enable API access
 */

console.log('📱 Play Store API Agent Active');
console.log('\n🎯 Mission: Acquire Google Play API credentials');

const INSTRUCTIONS = `
=== GOOGLE PLAY SERVICE ACCOUNT SETUP ===

Step 1: Google Cloud Console
  1. Visit: https://console.cloud.google.com/
  2. Create new project: "masterbuilder7-deploy"
  3. Enable Android Publisher API:
     - APIs & Services > Library
     - Search "Google Play Android Developer API"
     - Click Enable

Step 2: Create Service Account
  1. IAM & Admin > Service Accounts
  2. Click "Create Service Account"
  3. Name: "masterbuilder7-deployer"
  4. Role: "Editor" (or custom with Android Publisher)
  5. Click Create

Step 3: Create Key
  1. Click on the service account
  2. Keys > Add Key > Create New Key
  3. Select JSON format
  4. Download the JSON file

Step 4: Grant Play Console Access
  1. Visit: https://play.google.com/console
  2. Users and permissions > Invite new users
  3. Add service account email (from JSON)
  4. Role: Release Manager (or Admin)
  5. Send invite

Step 5: GitHub Actions Secret
  1. Base64 encode the JSON:
     cat service-account.json | base64 -w 0
  2. Add to GitHub Secrets:
     Name: GOOGLE_PLAY_JSON_KEY
     Value: [base64-encoded-json]

=== VERIFICATION ===
Test with: curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  https://androidpublisher.googleapis.com/androidpublisher/v3/applications/your.package.name
`;

console.log(INSTRUCTIONS);

// Check if credentials exist
const fs = require('fs');
if (fs.existsSync('./service-account.json')) {
  console.log('\n✅ Found service-account.json');
  const content = fs.readFileSync('./service-account.json', 'utf8');
  const json = JSON.parse(content);
  console.log(`   Client Email: ${json.client_email}`);
  console.log(`   Project ID: ${json.project_id}`);
  
  // Show base64 command
  console.log('\n📋 Run this to get GitHub Secret:');
  console.log('   cat service-account.json | base64 -w 0');
} else {
  console.log('\n⚠️  service-account.json not found');
  console.log('   Follow steps above to create it');
}

console.log('\n📱 Play Store API Agent: Standing by for credentials');
