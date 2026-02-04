# Print3D Implementation Plan

## Current Status

### ✅ Completed
- [x] Next.js frontend project created (`print3d-web/`)
- [x] Landing page with hero, pricing preview, artist section
- [x] Create page with 3-step flow (Generate → Customize → Checkout)
- [x] Pricing page with all tiers and FAQ
- [x] Contact page with form
- [x] Artists consulting page
- [x] Generator component with style selection
- [x] 3D model preview component (Three.js)
- [x] Pricing selector component
- [x] Backend payment module (`web/payments.py`)
- [x] Backend orders module (`web/orders.py`)
- [x] Backend API routes (`web/api.py`)
- [x] Email templates (`web/emails.py`)
- [x] Config updated with all new env vars
- [x] API keys configured (Gemini, Meshy, Stripe, Shapeways)

### ⚠️ Needs Work
- [ ] Connect frontend to backend API
- [ ] Test full generation flow end-to-end
- [ ] Stripe checkout integration (frontend)
- [ ] Webhook handling for payment confirmation
- [ ] Shapeways order submission after payment
- [ ] Database persistence (currently in-memory)
- [ ] Error handling and edge cases
- [ ] Mobile responsiveness testing

---

## Phase 1: Backend Fixes (Day 1)

### 1.1 Fix Import Issues
```
Location: /print3d/web/api.py
Issue: Relative imports may fail
Action: Fix import paths for standalone running
```

### 1.2 Install Backend Dependencies
```bash
cd /Users/pedrohernandezbaez/Documents/print3d
pip install flask flask-cors stripe
```

### 1.3 Add CORS Headers Properly
```
Location: /print3d/web/api.py
Action: Ensure CORS allows localhost:3000 and production domain
```

### 1.4 Serve Static Files (Generated Images/Models)
```
Location: /print3d/web/api.py
Action: Add route to serve files from output/ directory
```

### 1.5 Test Backend Standalone
```bash
python run_web.py
# Should start on http://localhost:5000
# Test: curl http://localhost:5000/api/health
```

---

## Phase 2: Frontend-Backend Integration (Day 2)

### 2.1 Create Frontend Environment File
```
Location: /print3d-web/.env.local
Content:
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 2.2 Update API Client
```
Location: /print3d-web/src/lib/api.ts
Actions:
- Add proper error handling
- Add timeout handling
- Add retry logic for failed requests
```

### 2.3 Fix Generator Component
```
Location: /print3d-web/src/components/Generator.tsx
Actions:
- Handle API errors gracefully
- Show meaningful error messages
- Add loading states
```

### 2.4 Fix 3D Preview Component
```
Location: /print3d-web/src/components/ModelPreview.tsx
Actions:
- Handle GLB/OBJ file loading
- Add fallback for unsupported formats
- Fix image preview during generation
```

### 2.5 Test Generation Flow
```
1. Start backend: python run_web.py
2. Start frontend: cd print3d-web && npm run dev
3. Go to http://localhost:3000/create
4. Enter prompt, click Generate
5. Verify image appears
6. Verify 3D model loads
```

---

## Phase 3: Payment Integration (Day 3)

### 3.1 Add Stripe to Frontend
```
Location: /print3d-web/src/app/create/page.tsx
Actions:
- Import Stripe.js
- Create checkout session via API
- Redirect to Stripe Checkout
```

### 3.2 Create Checkout API Endpoint
```
Location: /print3d/web/api.py - /api/checkout
Actions:
- Validate job exists and is complete
- Create Stripe checkout session
- Return checkout URL
```

### 3.3 Handle Stripe Webhooks
```
Location: /print3d/web/api.py - /api/webhook/stripe
Actions:
- Verify webhook signature
- Update order status to PAID
- Trigger Shapeways order submission
- Send confirmation email
```

### 3.4 Create Success/Cancel Pages
```
Location: /print3d-web/src/app/order/[id]/page.tsx
Actions:
- Show order confirmation
- Display order status
- Show tracking info when available
```

### 3.5 Test Payment Flow
```
1. Complete generation
2. Select size/material
3. Click checkout
4. Use test card: 4242 4242 4242 4242
5. Verify redirect to success page
6. Check webhook received (Stripe dashboard)
```

---

## Phase 4: Shapeways Integration (Day 4)

### 4.1 Implement OAuth Token Flow
```
Location: /print3d/print_api.py
Actions:
- Get access token using client credentials
- Cache token with expiry
- Refresh token when expired
```

### 4.2 Upload Model to Shapeways
```
Location: /print3d/web/shapeways_orders.py (new file)
Actions:
- Upload mesh file after payment
- Get model ID
- Check printability
```

### 4.3 Create Shapeways Order
```
Actions:
- Select material based on user choice
- Set shipping address
- Submit order
- Save Shapeways order ID
```

### 4.4 Sync Order Status
```
Actions:
- Poll Shapeways for order status
- Update local order status
- Get tracking number when shipped
- Send shipping notification email
```

---

## Phase 5: Database & Persistence (Day 5)

### 5.1 Choose Database
```
Options:
- SQLite (simple, file-based) - Good for MVP
- Supabase (PostgreSQL) - Good for scale
- PlanetScale (MySQL) - Good for scale

Recommendation: Start with SQLite, migrate later
```

### 5.2 Create Database Models
```
Location: /print3d/models/database.py
Tables:
- jobs (id, prompt, style, status, image_path, mesh_path, created_at)
- orders (id, job_id, email, size, material, price, status, paid_at, shipped_at)
- payments (id, order_id, provider, payment_id, amount, status)
```

### 5.3 Add SQLAlchemy
```bash
pip install sqlalchemy
```

### 5.4 Migrate In-Memory to Database
```
Actions:
- Replace dict storage with SQLAlchemy models
- Add database session management
- Add database migrations
```

---

## Phase 6: Testing & Polish (Day 6-7)

### 6.1 End-to-End Testing
```
Test Cases:
1. Generate image → 3D model → checkout → payment
2. Failed generation (bad prompt)
3. Failed payment (declined card)
4. Order tracking page
5. Contact form submission
```

### 6.2 Error Handling
```
Actions:
- Add try/catch to all API calls
- Show user-friendly error messages
- Add error logging
- Add Sentry for production error tracking
```

### 6.3 Mobile Responsiveness
```
Pages to test:
- Landing page
- Create page (generator + preview)
- Pricing page
- Contact page
```

### 6.4 Performance Optimization
```
Actions:
- Lazy load 3D viewer
- Optimize images
- Add loading skeletons
- Cache API responses where appropriate
```

---

## Phase 7: Deployment (Day 8-10)

### 7.1 Backend Deployment (Railway)
```
Steps:
1. Create Railway account
2. Connect GitHub repo
3. Set environment variables
4. Deploy
5. Get production URL
```

### 7.2 Frontend Deployment (Vercel)
```
Steps:
1. Create Vercel account
2. Import print3d-web from GitHub
3. Set NEXT_PUBLIC_API_URL to Railway URL
4. Deploy
5. Get production URL
```

### 7.3 Domain Setup
```
Steps:
1. Point domain DNS to Vercel
2. Add custom domain in Vercel
3. Enable HTTPS
4. Update CORS in backend for production domain
```

### 7.4 Stripe Production Mode
```
Steps:
1. Complete Stripe account verification
2. Switch to live API keys
3. Set up production webhook endpoint
4. Test with real card (small amount)
```

### 7.5 Monitoring Setup
```
Tools:
- Vercel Analytics (frontend)
- Railway Metrics (backend)
- Stripe Dashboard (payments)
- Sentry (error tracking)
```

---

## Immediate Next Steps

### Right Now (Next 30 Minutes)
1. [ ] Install backend dependencies
2. [ ] Start backend server
3. [ ] Start frontend server
4. [ ] Test the landing page loads
5. [ ] Test the create page loads

### Today
1. [ ] Fix any import/connection errors
2. [ ] Test generation flow (may fail - identify issues)
3. [ ] Document all errors encountered

### This Week
1. [ ] Complete Phase 1-3 (Backend, Frontend, Payments)
2. [ ] Have working checkout flow
3. [ ] Test with Stripe test mode

---

## File Checklist

### Backend Files
```
print3d/
├── config.py              ✅ Updated
├── image_gen.py           ✅ Updated (Gemini primary)
├── mesh_gen.py            ✅ Exists (Meshy)
├── print_api.py           ✅ Exists (Shapeways)
├── pipeline.py            ✅ Exists
├── agent_service.py       ✅ Exists (job queue)
├── run_web.py             ✅ Created
├── web/
│   ├── __init__.py        ✅ Created
│   ├── api.py             ✅ Created
│   ├── payments.py        ✅ Created
│   ├── orders.py          ✅ Created
│   └── emails.py          ✅ Created
└── .env                   ✅ Configured
```

### Frontend Files
```
print3d-web/
├── src/app/
│   ├── page.tsx           ✅ Landing page
│   ├── layout.tsx         ✅ Updated
│   ├── create/page.tsx    ✅ Generator flow
│   ├── pricing/page.tsx   ✅ Pricing page
│   ├── contact/page.tsx   ✅ Contact form
│   └── artists/page.tsx   ✅ Artist consulting
├── src/components/
│   ├── Generator.tsx      ✅ Created
│   ├── ModelPreview.tsx   ✅ Created
│   └── PricingSelector.tsx ✅ Created
├── src/lib/
│   └── api.ts             ✅ Created
└── .env.local             ⚠️ Need to create
```

---

## Commands Reference

### Start Backend
```bash
cd /Users/pedrohernandezbaez/Documents/print3d
python run_web.py
```

### Start Frontend
```bash
cd /Users/pedrohernandezbaez/Documents/print3d-web
npm run dev
```

### Test API
```bash
# Health check
curl http://localhost:5000/api/health

# Submit job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"description": "a cute robot"}'

# Check job status
curl http://localhost:5000/api/jobs/{job_id}
```

### Build for Production
```bash
# Frontend
cd print3d-web && npm run build

# Backend - no build needed (Python)
```
