#!/usr/bin/env bun
/**
 * KEYSTORE MANAGER AGENT
 * Mission: Generate, validate, and manage Android keystores
 */

import { execSync } from 'child_process';
import { existsSync, readFileSync, writeFileSync } from 'fs';

const KEYSTORE_PATH = process.env.KEYSTORE_PATH || './android.keystore';
const KEY_ALIAS = process.env.KEY_ALIAS || 'upload';
const VALIDITY_YEARS = 25;

console.log('🔐 Keystore Manager Agent Active');

// Check if keystore exists
if (!existsSync(KEYSTORE_PATH)) {
  console.log('⚠️  No keystore found. Generating new one...');
  
  // Generate keystore using keytool
  try {
    const keytoolCmd = `keytool -genkey -v \
      -keystore ${KEYSTORE_PATH} \
      -alias ${KEY_ALIAS} \
      -keyalg RSA \
      -keysize 2048 \
      -validity ${VALIDITY_YEARS * 365} \
      -storepass ${process.env.KEYSTORE_PASSWORD || 'changeme'} \
      -keypass ${process.env.KEYSTORE_PASSWORD || 'changeme'} \
      -dname "CN=Elite Squad, OU=Dev, O=MasterBuilder7, L=JHB, ST=GP, C=ZA"`;
    
    execSync(keytoolCmd, { stdio: 'inherit' });
    console.log('✅ Keystore generated successfully');
  } catch (e) {
    console.error('❌ Keystore generation failed:', e);
    process.exit(1);
  }
}

// Validate keystore
try {
  const validateCmd = `keytool -list -v \
    -keystore ${KEYSTORE_PATH} \
    -alias ${KEY_ALIAS} \
    -storepass ${process.env.KEYSTORE_PASSWORD || 'changeme'}`;
  
  const output = execSync(validateCmd, { encoding: 'utf8' });
  console.log('✅ Keystore validated');
  console.log(output.split('\n').slice(0, 5).join('\n'));
} catch (e) {
  console.error('❌ Keystore validation failed');
  process.exit(1);
}

// Convert to Base64 for GitHub Actions
if (existsSync(KEYSTORE_PATH)) {
  const keystoreBuffer = readFileSync(KEYSTORE_PATH);
  const base64Keystore = keystoreBuffer.toString('base64');
  
  console.log('\n📋 GitHub Actions Secret (UPLOAD_KEYSTORE_B64):');
  console.log(base64Keystore.substring(0, 50) + '... [truncated]');
  
  // Save to file for reference
  writeFileSync('./keystore.base64.txt', base64Keystore);
  console.log('\n💾 Full Base64 saved to: keystore.base64.txt');
}

console.log('\n🔐 Keystore Manager: Mission Complete');
