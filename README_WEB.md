# Print3D Web Integration

This guide explains how to run the Print3D website with payment integration.

## Quick Start

### 1. Install Backend Dependencies

```bash
cd print3d
pip install flask flask-cors stripe resend
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required for MVP:
- `MESHY_API_KEY` - For 3D model generation
- `FAL_KEY` or `GEMINI_API_KEY` - For image generation
- `STRIPE_SECRET_KEY` - For payments
- `STRIPE_PUBLISHABLE_KEY` - For frontend

### 3. Start Backend API

```bash
python run_web.py
# API runs at http://localhost:5000
```

### 4. Start Frontend (in separate terminal)

```bash
cd ../print3d-web
cp .env.local.example .env.local
npm run dev
# Frontend runs at http://localhost:3000
```

## Architecture

```
print3d/                  # Backend (Python/Flask)
├── web/
│   ├── api.py           # REST API endpoints
│   ├── payments.py      # Stripe + PayPal integration
│   ├── orders.py        # Order management
│   └── emails.py        # Email notifications
├── config.py            # Configuration
└── run_web.py           # Entry point

print3d-web/              # Frontend (Next.js)
├── src/app/
│   ├── page.tsx         # Landing page
│   ├── create/          # Generator UI
│   ├── pricing/         # Pricing page
│   ├── contact/         # Contact form
│   └── artists/         # Artist consulting
├── src/components/
│   ├── Generator.tsx    # AI generation form
│   ├── ModelPreview.tsx # 3D viewer (Three.js)
│   └── PricingSelector.tsx
└── src/lib/
    └── api.ts           # Backend API client
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/jobs` | POST | Submit generation job |
| `/api/jobs/:id` | GET | Get job status |
| `/api/checkout` | POST | Create payment session |
| `/api/order/:id` | GET | Get order details |
| `/api/webhook/stripe` | POST | Stripe webhook |

## Stripe Setup

1. Create account at https://stripe.com
2. Get API keys from Dashboard → Developers → API keys
3. Set up webhook endpoint: `https://yourdomain.com/api/webhook/stripe`
4. Enable events: `checkout.session.completed`

## Deployment

### Backend (Railway/Render)

1. Push code to GitHub
2. Connect to Railway/Render
3. Set environment variables
4. Deploy

### Frontend (Vercel)

1. Push print3d-web to GitHub
2. Import to Vercel
3. Set `NEXT_PUBLIC_API_URL` to your backend URL
4. Deploy

## Testing

### Test Generation Flow

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"description": "a cute robot"}'
```

### Test Checkout (Stripe Test Mode)

Use test card: `4242 4242 4242 4242`

## Pricing

| Size | PLA | Resin |
|------|-----|-------|
| Small (50mm) | $29 | $39 |
| Medium (75mm) | $49 | $59 |
| Large (100mm) | $69 | $89 |
