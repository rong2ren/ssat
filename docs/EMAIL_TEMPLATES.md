# SmartSSAT - Email Templates & Setup

Professional email templates for Supabase authentication with Resend SMTP integration.

## 🏷️ Brand Name

### **SmartSSAT** 📚✨
- **Smart & Catchy** - Immediately communicates intelligence and AI
- **Clear Purpose** - Directly relates to SSAT preparation
- **Memorable** - Easy to remember and type
- **Professional** - Sounds modern and tech-forward
- **Perfect for AI** - "Smart" emphasizes the AI-powered nature

---

## 🚀 Resend SMTP Setup

### **Why Resend?**
- **Free tier**: 3,000 emails/month
- **Excellent deliverability** (99.9%+)
- **Easy Supabase integration**
- **Professional templates**
- **Great developer experience**

### **Setup Instructions:**

#### **Step 1: Create Resend Account**
1. Go to [resend.com](https://resend.com)
2. Sign up for a free account
3. Verify your email address
4. Add your domain (optional but recommended)

#### **Step 2: Get API Key**
1. Go to **API Keys** in your Resend dashboard
2. Create a new API key
3. Copy the API key (starts with `re_`)

#### **Step 3: Configure Supabase SMTP**
1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **Auth** → **Email Templates**
3. Click **"Configure SMTP"**
4. Enter the following settings:

```
SMTP Host: smtp.resend.com
SMTP Port: 587
SMTP Username: resend
SMTP Password: [Your Resend API Key]
```

5. Click **Save** - you should see a success message

#### **Step 4: Update Email Templates**
1. In Supabase dashboard, go to **Authentication** → **Email Templates**
2. Replace the templates with the SmartSSAT templates below
3. Test the email delivery

#### **Step 5: Verify Setup**
1. Create a test account
2. Check if verification email is received
3. Test password reset functionality
4. Monitor email delivery in Resend dashboard

### **Benefits:**
- ✅ **Professional emails** with high deliverability
- ✅ **Scalable** for growth
- ✅ **Cost-effective** (free for 3,000 emails/month)
- ✅ **Easy setup** and maintenance
- ✅ **Great developer experience**

---

## 🎨 Design Elements
- **Primary Color**: Blue (#2563eb - blue-600)
- **Secondary Colors**: Clean whites and grays
- **Typography**: Simple, readable fonts
- **Branding**: Simple text-based logo
- **Style**: Clean, professional, minimal

---

## 📧 Email Verification Template

**Subject Line:** `Verify your SmartSSAT account`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your SmartSSAT account</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #374151;
            margin: 0;
            padding: 20px;
            background-color: #f8fafc;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            text-align: center;
        }
        .description {
            font-size: 16px;
            color: #6b7280;
            margin-bottom: 30px;
            text-align: center;
        }
        .button-container {
            text-align: center;
            margin: 30px 0;
        }
        .verify-button {
            display: inline-block;
            background-color: #2563eb;
            color: #ffffff;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 500;
            font-size: 16px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }
        .footer p {
            color: #6b7280;
            font-size: 14px;
            margin: 5px 0;
        }
        .footer a {
            color: #2563eb;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="title">Welcome to SmartSSAT!</div>
        
        <div class="description">
            Thank you for creating your account! Please verify your email address to start practicing.
        </div>
        
        <div class="button-container">
            <a href="{{ .ConfirmationURL }}" class="verify-button">
                Verify My Account
            </a>
        </div>
        
        <div class="footer">
            <p><strong>SmartSSAT</strong></p>
            <p>AI-Powered SSAT Preparation Platform</p>
            <p><a href="https://your-website.com">Visit our website</a></p>
        </div>
    </div>
</body>
</html>
```

---

## 🔑 Password Reset Template

**Subject Line:** `Reset your SmartSSAT password`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your SmartSSAT password</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #374151;
            margin: 0;
            padding: 20px;
            background-color: #f8fafc;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            text-align: center;
        }
        .description {
            font-size: 16px;
            color: #6b7280;
            margin-bottom: 30px;
            text-align: center;
        }
        .button-container {
            text-align: center;
            margin: 30px 0;
        }
        .reset-button {
            display: inline-block;
            background-color: #2563eb;
            color: #ffffff;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 500;
            font-size: 16px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }
        .footer p {
            color: #6b7280;
            font-size: 14px;
            margin: 5px 0;
        }
        .footer a {
            color: #2563eb;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="title">Password Reset Request</div>
        
        <div class="description">
            We received a request to reset your password. Click the button below to create a new password.
        </div>
        
        <div class="button-container">
            <a href="{{ .ConfirmationURL }}" class="reset-button">
                Reset My Password
            </a>
        </div>
        
        <div class="footer">
            <p><strong>SmartSSAT</strong></p>
            <p>AI-Powered SSAT Preparation Platform</p>
            <p><a href="https://your-website.com">Visit our website</a></p>
        </div>
    </div>
</body>
</html>
```

---

Email Service Provider: Resend

