# Payment Implementation Plan for SmartSSAT

## 🎯 **Current State Analysis**

### **Existing Infrastructure:**
- ✅ **User Roles**: `free`, `premium`, `admin` (already implemented)
- ✅ **Daily Limits**: Different limits per role (free: 1 test, premium: 4 tests)
- ✅ **Supabase Auth**: User management and authentication
- ✅ **Admin Panel**: Role management interface
- ✅ **Backend API**: FastAPI with role-based access control

### **Missing Components:**
- ❌ **Payment Processing**: No payment gateway integration
- ❌ **Pricing Page**: No pricing/plans display
- ❌ **Subscription Management**: No recurring billing
- ❌ **Payment History**: No transaction tracking
- ❌ **Billing Portal**: No customer billing interface

## 🚀 **Recommended Solution: Stripe Integration**

### **Why Stripe?**
- ✅ **Easy Integration**: Excellent Next.js/React support
- ✅ **Comprehensive**: Subscriptions, one-time payments, webhooks
- ✅ **Developer Friendly**: Great documentation and SDKs
- ✅ **Reliable**: Industry standard with 99.9% uptime
- ✅ **Compliance**: PCI DSS, GDPR, SOC 2 compliant

## 📊 **Pricing Strategy**

### **Free Tier (Current):**
- 1 full test per day
- Basic question types
- Standard support

### **Premium Tier ($9.99/month):**
- 4 full tests per day
- All question types
- Priority support
- PDF export
- Progress tracking

### **Pro Tier ($19.99/month):**
- Unlimited tests
- Advanced analytics
- Custom question generation
- API access
- Priority support

## 🏗️ **Implementation Plan**

### **Phase 1: Core Payment Infrastructure**

#### **1.1 Backend Setup**
```python
# Add to backend/pyproject.toml
dependencies = [
    "stripe>=7.0.0",
    # ... existing dependencies
]
```

#### **1.2 Frontend Setup**
```json
// Add to frontend/package.json
dependencies = {
    "@stripe/stripe-js": "^2.0.0",
    "@stripe/react-stripe-js": "^2.0.0"
}
```

#### **1.3 Database Schema Updates**
```sql
-- Add payment-related tables
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    stripe_subscription_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    status TEXT NOT NULL,
    plan_type TEXT NOT NULL,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    stripe_payment_intent_id TEXT UNIQUE,
    amount INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **Phase 2: Stripe Integration**

#### **2.1 Backend API Routes**
```python
# /api/payments/create-checkout-session
# /api/payments/create-portal-session
# /api/payments/webhook
# /api/payments/subscription-status
```

#### **2.2 Frontend Components**
```typescript
// Components to create:
- PricingPage.tsx
- CheckoutForm.tsx
- BillingPortal.tsx
- SubscriptionStatus.tsx
```

### **Phase 3: User Experience**

#### **3.1 Pricing Page**
- Display plans and features
- Clear value proposition
- Easy upgrade flow

#### **3.2 Checkout Flow**
- Stripe Checkout integration
- Secure payment processing
- Automatic role upgrade

#### **3.3 Billing Management**
- Customer portal access
- Payment history
- Subscription management

## 📋 **Detailed Implementation Steps**

### **Step 1: Environment Setup**

#### **Backend (.env):**
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PREMIUM=price_...
STRIPE_PRICE_PRO=price_...
```

#### **Frontend (.env.local):**
```bash
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_STRIPE_PREMIUM_PRICE_ID=price_...
NEXT_PUBLIC_STRIPE_PRO_PRICE_ID=price_...
```

### **Step 2: Backend Implementation**

#### **2.1 Install Dependencies**
```bash
cd backend
pip install stripe
```

#### **2.2 Create Payment Service**
```python
# backend/app/services/payment_service.py
class PaymentService:
    def __init__(self):
        self.stripe = stripe.Stripe(settings.STRIPE_SECRET_KEY)
    
    async def create_checkout_session(self, user_id: str, price_id: str):
        # Create Stripe checkout session
    
    async def create_portal_session(self, customer_id: str):
        # Create customer portal session
    
    async def handle_webhook(self, event):
        # Handle Stripe webhooks
```

#### **2.3 Add API Routes**
```python
# backend/app/main.py
@app.post("/api/payments/create-checkout-session")
async def create_checkout_session(request: CheckoutRequest, current_user: UserProfile):
    # Create Stripe checkout session

@app.post("/api/payments/create-portal-session")
async def create_portal_session(current_user: UserProfile):
    # Create customer portal session

@app.post("/api/payments/webhook")
async def stripe_webhook(request: Request):
    # Handle Stripe webhooks
```

### **Step 3: Frontend Implementation**

#### **3.1 Install Dependencies**
```bash
cd frontend
npm install @stripe/stripe-js @stripe/react-stripe-js
```

#### **3.2 Create Pricing Page**
```typescript
// frontend/src/app/pricing/page.tsx
export default function PricingPage() {
    return (
        <div>
            <h1>Choose Your Plan</h1>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <PlanCard plan="free" />
                <PlanCard plan="premium" />
                <PlanCard plan="pro" />
            </div>
        </div>
    );
}
```

#### **3.3 Create Checkout Component**
```typescript
// frontend/src/components/CheckoutForm.tsx
export function CheckoutForm({ priceId, planType }: CheckoutFormProps) {
    const handleCheckout = async () => {
        const response = await fetch('/api/payments/create-checkout-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ priceId, planType })
        });
        
        const { url } = await response.json();
        window.location.href = url;
    };
    
    return (
        <button onClick={handleCheckout}>
            Upgrade to {planType}
        </button>
    );
}
```

### **Step 4: Database Integration**

#### **4.1 Update User Model**
```python
# backend/app/models/user.py
class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    grade_level: Optional[str] = None
    role: str = 'free'
    stripe_customer_id: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: str
    updated_at: str
```

#### **4.2 Add Subscription Management**
```python
# backend/app/services/subscription_service.py
class SubscriptionService:
    async def get_user_subscription(self, user_id: str):
        # Get user subscription status
    
    async def update_user_role_from_subscription(self, user_id: str):
        # Update user role based on subscription
```

### **Step 5: Webhook Handling**

#### **5.1 Handle Stripe Events**
```python
# backend/app/main.py
@app.post("/api/payments/webhook")
async def stripe_webhook(request: Request):
    event = stripe.Webhook.construct_event(
        payload=await request.body(),
        sig_header=request.headers.get('stripe-signature'),
        secret=settings.STRIPE_WEBHOOK_SECRET
    )
    
    if event['type'] == 'checkout.session.completed':
        await handle_checkout_completed(event)
    elif event['type'] == 'customer.subscription.updated':
        await handle_subscription_updated(event)
    elif event['type'] == 'customer.subscription.deleted':
        await handle_subscription_deleted(event)
```

## 🎯 **User Flow**

### **1. Free User Experience:**
```
User visits pricing page → Sees plan comparison → 
Clicks upgrade → Stripe Checkout → Payment success → 
Webhook updates role → User gets premium features
```

### **2. Premium User Experience:**
```
User has premium → Can access billing portal → 
Manage subscription → Cancel/upgrade/downgrade → 
Webhook updates role accordingly
```

## 📊 **Pricing Structure**

### **Free Plan:**
- Price: $0/month
- Features:
  - 1 full test per day
  - Basic question types
  - Standard support
- Limits: Current DEFAULT_LIMITS

### **Premium Plan:**
- Price: $9.99/month
- Features:
  - 4 full tests per day
  - All question types
  - PDF export
  - Progress tracking
- Limits: Current PREMIUM_LIMITS

### **Pro Plan:**
- Price: $19.99/month
- Features:
  - Unlimited tests
  - Advanced analytics
  - Custom question generation
  - API access
- Limits: Unlimited (-1 for all sections)

## 🔧 **Technical Implementation Details**

### **Stripe Products Setup:**
```bash
# Create products in Stripe Dashboard
stripe products create --name "SmartSSAT Premium" --description "Premium SSAT practice platform"
stripe products create --name "SmartSSAT Pro" --description "Professional SSAT practice platform"

# Create prices
stripe prices create --product=prod_xxx --unit-amount=999 --currency=usd --recurring[interval]=month
stripe prices create --product=prod_yyy --unit-amount=1999 --currency=usd --recurring[interval]=month
```

### **Webhook Endpoints:**
```bash
# Register webhook endpoint
stripe listen --forward-to localhost:8000/api/payments/webhook
```

### **Environment Variables:**
```bash
# Backend
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PREMIUM_PRICE_ID=price_...
STRIPE_PRO_PRICE_ID=price_...

# Frontend
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_STRIPE_PREMIUM_PRICE_ID=price_...
NEXT_PUBLIC_STRIPE_PRO_PRICE_ID=price_...
```

## 🚀 **Implementation Timeline**

### **Week 1: Foundation**
- [ ] Set up Stripe account and products
- [ ] Install dependencies
- [ ] Create database schema
- [ ] Set up environment variables

### **Week 2: Backend**
- [ ] Implement PaymentService
- [ ] Create API routes
- [ ] Add webhook handling
- [ ] Update user role management

### **Week 3: Frontend**
- [ ] Create pricing page
- [ ] Implement checkout flow
- [ ] Add billing portal
- [ ] Update user interface

### **Week 4: Testing & Launch**
- [ ] Test payment flows
- [ ] Test webhook handling
- [ ] Test role updates
- [ ] Deploy to production

## 📈 **Success Metrics**

### **Technical Metrics:**
- ✅ Payment success rate > 99%
- ✅ Webhook delivery success > 99.9%
- ✅ Role update latency < 5 seconds
- ✅ Zero payment data exposure

### **Business Metrics:**
- ✅ Conversion rate from free to premium
- ✅ Monthly recurring revenue (MRR)
- ✅ Customer lifetime value (CLV)
- ✅ Churn rate < 5%

## 🔒 **Security Considerations**

### **Payment Security:**
- ✅ Use Stripe's secure checkout
- ✅ Never handle raw payment data
- ✅ Validate webhook signatures
- ✅ Use HTTPS for all payment endpoints

### **Data Protection:**
- ✅ Encrypt sensitive data
- ✅ Follow GDPR compliance
- ✅ Implement proper access controls
- ✅ Regular security audits

## ✅ **Conclusion**

This implementation plan provides:
- **Secure payment processing** with Stripe
- **Seamless user experience** with clear upgrade paths
- **Scalable architecture** that grows with your business
- **Comprehensive billing management** for customers

The key is to **start simple** with the core payment flow and **iterate based on user feedback**. 