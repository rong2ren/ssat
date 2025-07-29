# Frontend Logging Strategy for Vercel

## 🎯 **Overview**

This document outlines the strategy for implementing frontend logging that appears in Vercel's runtime logs while maintaining optimal performance.

## 📊 **Current State**

### **Problem:**
- Frontend `console.log()` statements run in browser
- Vercel runtime logs only show server-side logs
- Frontend logs are invisible in Vercel dashboard

### **Current Logging:**
- Basic `console.log` statements throughout the app
- No visibility in Vercel runtime logs
- No structured logging or error tracking

## 🚀 **Recommended Solution: Minimal API Route Logging**

### **Approach:**
Create a single API route (`/api/log`) that captures critical business events and logs them to Vercel's runtime logs.

### **Benefits:**
- ✅ **Visible in Vercel** - All logs appear in dashboard
- ✅ **Minimal performance impact** - Only log critical events
- ✅ **No dependencies** - Uses Next.js built-in features
- ✅ **Full control** - Log exactly what you need

## 📋 **What to Log vs. What NOT to Log**

### **✅ Log These (Critical Business Events):**

```javascript
// Test Generation Events
- "Test generation started" → API route
- "Test generation completed" → API route
- "Test generation failed" → API route

// API Errors
- "API error: 500" → API route
- "API error: 404" → API route
- "Network timeout" → API route

// Business Logic
- "Daily limit exceeded" → API route
- "Payment failed" → API route
- "Admin action performed" → API route
- "User upgraded to premium" → API route

// Critical User Actions
- "User deleted account" → API route
- "Bulk operation started" → API route
- "Data export requested" → API route
```

### **❌ Don't Log These (Too Frequent or Handled Elsewhere):**

```javascript
// Auth Events (Supabase handles these)
- User login/logout → Supabase dashboard
- Registration events → Supabase dashboard
- Password resets → Supabase dashboard
- Session management → Supabase dashboard

// Development/UI Events
- Component renders → console.log only
- Button clicks → console.log only
- Cache operations → console.log only
- Debug statements → console.log only
```

## 🏗️ **Implementation Strategy**

### **1. API Route Structure**
```javascript
// /api/log
POST /api/log
{
  level: 'INFO' | 'ERROR' | 'WARN',
  message: string,
  context: {
    userId?: string,
    action?: string,
    component?: string
  },
  data?: any,
  error?: Error
}
```

### **2. Performance Optimizations**

#### **Async Logging (Don't Block UI):**
```javascript
// ✅ Good - Fire and forget
fetch('/api/log', { 
  method: 'POST', 
  body: JSON.stringify(logData) 
}); // Don't await

// ❌ Bad - Blocks UI
await fetch('/api/log', { ... });
```

#### **Batch Logging (Reduce Requests):**
```javascript
// Collect logs for 2-5 seconds, then send batch
const logQueue = [];
setInterval(() => {
  if (logQueue.length > 0) {
    fetch('/api/log/batch', { body: JSON.stringify(logQueue) });
    logQueue.length = 0;
  }
}, 3000);
```

#### **Smart Sampling:**
```javascript
// Only log every Nth occurrence for frequent events
let errorCount = 0;
if (errorCount % 10 === 0) { // Log every 10th error
  logError('API error occurred', error);
}
```

### **3. Log Levels**

```javascript
enum LogLevel {
  INFO = 'INFO',    // General information
  WARN = 'WARN',    // Warnings
  ERROR = 'ERROR'   // Errors and exceptions
}
```

## 📊 **Expected Vercel Log Output**

### **Before Implementation:**
```
GET /custom-section 200
GET /full-test 200
POST /api/generate 200
```

### **After Implementation:**
```
GET /custom-section 200
POST /api/log 200
[FRONTEND-INFO] Test generation started { userId: '123', sections: ['math', 'reading'] }
POST /api/generate 200
POST /api/log 200
[FRONTEND-INFO] Test generation completed { jobId: 'abc123', duration: 45000 }
POST /api/log 200
[FRONTEND-ERROR] API error occurred { endpoint: '/api/users', status: 500 }
```

## 🔧 **Implementation Steps**

### **Phase 1: Core Infrastructure**
1. Create `/api/log` route
2. Implement basic logging function
3. Add error handling and validation

### **Phase 2: Critical Events**
1. Replace critical `console.log` statements
2. Add test generation event logging
3. Add API error logging

### **Phase 3: Optimization**
1. Implement batch logging
2. Add performance monitoring
3. Add smart sampling for frequent events

### **Phase 4: Monitoring**
1. Set up log aggregation
2. Add alerting for critical errors
3. Monitor performance impact

## 📈 **Performance Impact Analysis**

### **Estimated Impact:**
- **Network Requests**: 1-3 per user session (minimal)
- **Bundle Size**: No increase (no dependencies)
- **Runtime Performance**: Negligible (async, non-blocking)
- **Vercel Log Volume**: +5-10 log entries per session

### **Performance Monitoring:**
```javascript
// Track logging performance
const startTime = performance.now();
await logEvent('test_generation_started', data);
const duration = performance.now() - startTime;

if (duration > 100) {
  console.warn('Logging taking too long:', duration);
}
```

## 🎯 **Success Metrics**

### **Technical Metrics:**
- ✅ Logs appear in Vercel runtime logs
- ✅ < 50ms average logging latency
- ✅ < 1% performance impact
- ✅ Zero blocking operations

### **Business Metrics:**
- ✅ Critical errors visible in Vercel
- ✅ Test generation events tracked
- ✅ User actions logged for debugging
- ✅ Admin actions audited

## 🔄 **Future Enhancements**

### **Advanced Features:**
1. **Log Retention**: Configure log retention periods
2. **Log Search**: Add search functionality in Vercel
3. **Alerting**: Set up alerts for critical errors
4. **Analytics**: Track log volume and patterns

### **Integration Options:**
1. **Vercel Analytics**: For performance metrics
2. **Sentry**: For error tracking (if needed)
3. **LogRocket**: For session replay (if needed)

## 📝 **Code Examples**

### **Basic Logging Function:**
```javascript
const logToVercel = async (level: string, message: string, context?: any) => {
  try {
    fetch('/api/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level,
        message,
        context,
        timestamp: new Date().toISOString()
      })
    });
  } catch (error) {
    // Fallback to console.log if API fails
    console.log(`[${level}] ${message}`, context);
  }
};
```

### **Usage Examples:**
```javascript
// Test generation
await logToVercel('INFO', 'Test generation started', { 
  userId: user.id, 
  sections: ['math', 'reading'] 
});

// API error
await logToVercel('ERROR', 'API call failed', { 
  endpoint: '/api/users', 
  status: 500,
  error: error.message 
});

// Business event
await logToVercel('INFO', 'Daily limit exceeded', { 
  userId: user.id, 
  limit: 'quantitative' 
});
```

## 🚫 **What NOT to Implement**

### **Avoid These Patterns:**
1. **Synchronous logging** - Blocks UI
2. **Logging everything** - Performance impact
3. **Large payloads** - Network overhead
4. **Complex batching** - Over-engineering
5. **External dependencies** - Keep it simple

### **Don't Log:**
- Component lifecycle events
- User interactions (clicks, hovers)
- Cache operations
- Debug statements
- Auth events (Supabase handles these)

## ✅ **Conclusion**

This strategy provides:
- **Visibility** in Vercel logs
- **Minimal performance impact**
- **Simple implementation**
- **Full control** over what gets logged

The key is to **only log critical business events** and **keep it simple**. 