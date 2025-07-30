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
</head>
<body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; background-color: #f8fafc; color: #374151; line-height: 1.6;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);">
                    <tr>
                        <td style="padding: 40px;">
                            <!-- Header -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding-bottom: 20px;">
                                        <h1 style="font-size: 24px; font-weight: 600; color: #1f2937; margin: 0; text-align: center;">Welcome to SmartSSAT!</h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-bottom: 30px;">
                                        <p style="font-size: 16px; color: #6b7280; margin: 0; text-align: center;">Thank you for creating your account! Please verify your email address to start practicing.</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td align="center" style="background-color: #2563eb; border-radius: 6px;">
                                                    <a href="{{ .ConfirmationURL }}" style="display: inline-block; padding: 12px 24px; color: #ffffff; text-decoration: none; font-weight: 500; font-size: 16px; background-color: #2563eb; border-radius: 6px;">
                                                        <span style="color: #ffffff; font-weight: 500; font-size: 16px;">Verify My Account</span>
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Footer -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                                <tr>
                                    <td align="center">
                                        <p style="color: #6b7280; font-size: 14px; margin: 5px 0; font-weight: bold;">SmartSSAT</p>
                                        <p style="color: #6b7280; font-size: 14px; margin: 5px 0;">AI-Powered SSAT Preparation Platform</p>
                                        <p style="color: #6b7280; font-size: 14px; margin: 5px 0;">
                                            <a href="https://your-website.com" style="color: #2563eb; text-decoration: none;">Visit our website</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
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
</head>
<body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; background-color: #f8fafc; color: #374151; line-height: 1.6;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);">
                    <tr>
                        <td style="padding: 40px;">
                            <!-- Header -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding-bottom: 20px;">
                                        <h1 style="font-size: 24px; font-weight: 600; color: #1f2937; margin: 0; text-align: center;">Password Reset Request</h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-bottom: 30px;">
                                        <p style="font-size: 16px; color: #6b7280; margin: 0; text-align: center;">We received a request to reset your password. Click the button below to create a new password.</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td align="center" style="background-color: #2563eb; border-radius: 6px;">
                                                    <a href="{{ .ConfirmationURL }}" style="display: inline-block; padding: 12px 24px; color: #ffffff; text-decoration: none; font-weight: 500; font-size: 16px; background-color: #2563eb; border-radius: 6px;">
                                                        <span style="color: #ffffff; font-weight: 500; font-size: 16px;">Reset My Password</span>
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Footer -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                                <tr>
                                    <td align="center">
                                        <p style="color: #6b7280; font-size: 14px; margin: 5px 0; font-weight: bold;">SmartSSAT</p>
                                        <p style="color: #6b7280; font-size: 14px; margin: 5px 0;">AI-Powered SSAT Preparation Platform</p>
                                        <p style="color: #6b7280; font-size: 14px; margin: 5px 0;">
                                            <a href="https://your-website.com" style="color: #2563eb; text-decoration: none;">Visit our website</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
```

---

## 📧 Email Client Compatibility Tips

### **Why These Templates Work Better:**

1. **Table-based Layout**: Email clients prefer table layouts over div-based layouts
2. **Inline Styles**: All styles are inline to ensure maximum compatibility
3. **Fallback Colors**: Multiple color declarations for button text
4. **Simple Font Stack**: Using Arial, Helvetica, sans-serif for maximum compatibility
5. **No External CSS**: All styles are embedded to avoid stripping

### **Key Improvements:**

- ✅ **Button text visibility**: Multiple color declarations ensure white text shows
- ✅ **Cross-client compatibility**: Works in Gmail, Outlook, Apple Mail, etc.
- ✅ **Mobile responsive**: Table-based layout adapts to mobile screens
- ✅ **Accessibility**: Proper contrast ratios and readable fonts
- ✅ **Professional appearance**: Clean, modern design that matches your brand

### **Testing Recommendations:**

1. **Test in multiple email clients**: Gmail, Outlook, Apple Mail, Yahoo
2. **Test on mobile devices**: iPhone, Android
3. **Check button visibility**: Ensure white text is visible on blue background
4. **Verify links work**: Test confirmation URLs
5. **Monitor delivery rates**: Check spam folder placement

Email Service Provider: Resend

