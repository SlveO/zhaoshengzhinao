---
name: deploy-miniapp
description: Build and deploy a tenant's mini-app to Cloudflare Pages. Invoke when user says "deploy mini-app", "publish mini-app", "deploy <tenant>", or "build and deploy <tenant>".
---

# Deploy Mini-app

Build and deploy a tenant-specific mini-app to Cloudflare Pages.

## Steps

1. **Build tenant config**:
   ```bash
   cd mini-app && TENANT=<tenant_slug> node build.config.js
   ```
   This reads `mini-app/tenants/<tenant_slug>.json` → generates `src/tenant.config.ts`

2. **Build H5**:
   ```bash
   cd mini-app && npm run build:h5
   ```

3. **Deploy to Cloudflare Pages**:
   Use the wrangler deploy command appropriate for the tenant's configuration.

## Pre-flight checks
- Verify `mini-app/tenants/<tenant_slug>.json` exists
- Verify `DEEPSEEK_API_KEY` and other env vars are set
- Confirm CF Pages project name with user

## Post-deploy
- Verify the deployed URL returns 200
- Check that tenant-specific theming (colors, features) is correct
