# Authentication Setup - Simplified Approach

This document describes the simplified authentication system for the SSAT application, following the NestJS Supabase Auth pattern.

## 🎯 **Overview**

The authentication system uses **only Supabase's `auth.users` table** with metadata for user profile data, eliminating the need for a separate `user_profiles` table.

## 🏗️ **Architecture**

### **Database Schema**
- **`auth.users`** - Supabase's built-in authentication table
  - Contains: `id`, `email`, `password_hash`, `created_at`, `updated_at`, etc.
  - **`raw_user_meta_data`** - JSON field for custom user data
    - `full_name` - User's full name
    - `grade_level` - SSAT grade level (3rd-8th)

### **Content Tracking**
- **`ai_generation_sessions`** - Tracks user's content generation
  - `user_id` - Links to `auth.users.id`
  - `request_params`, `total_questions_generated`, `status`, etc.

## 📊 **Database Functions**

### **`get_user_content_count(p_user_id UUID)`**
Returns user's content generation statistics by section type:
```sql
RETURNS TABLE (
    quantitative_count INTEGER,
    analogy_count INTEGER,
    synonym_count INTEGER,
    reading_count INTEGER,
    writing_count INTEGER
)
```

### **`get_ai_generation_sessions(p_user_id UUID, limit_count INT)`**
Returns user's generation sessions:
```sql
RETURNS TABLE (
    session_id TEXT,
    user_id UUID,
    request_params JSONB,
    total_questions INTEGER,
    providers_used TEXT[],
    generation_duration_ms INTEGER,
    status TEXT,
    created_at TIMESTAMPTZ
)
```

## 🔧 **Backend Implementation**

### **Models (`backend/app/models/user.py`)**
```python
class UserMetadata(BaseModel):
    """User metadata stored in auth.users.raw_user_meta_data"""
    full_name: Optional[str] = None
    grade_level: Optional[GradeLevel] = None

class UserProfile(BaseModel):
    """User profile from auth.users table with metadata"""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    grade_level: Optional[GradeLevel] = None
    created_at: datetime
    updated_at: datetime
    last_sign_in_at: Optional[datetime] = None
    email_confirmed_at: Optional[datetime] = None
```

### **Service (`backend/app/services/user_service.py`)**
- **`get_user_profile(user_id)`** - Extract profile from `auth.users` with metadata
- **`update_user_profile(user_id, data)`** - Update metadata using Supabase admin API
- **`get_user_content_stats(user_id)`** - Get content generation statistics

### **Authentication (`backend/app/auth.py`)**
- **Registration** - Store metadata in `user_metadata` during signup
- **Login** - Extract profile from `auth.users` with metadata
- **Profile Updates** - Update metadata using admin API

## 🌐 **Frontend Implementation**

### **Context (`frontend/src/contexts/AuthContext.tsx`)**
- Manages authentication state
- Handles login, register, logout
- Stores token in `localStorage`

### **Components**
- **`LoginForm`** - User login
- **`RegisterForm`** - User registration
- **`UserProfile`** - Display and edit profile
- **`AuthGuard`** - Route protection

## 🔍 **Debug Queries**

### **View All Users with Metadata**
```sql
SELECT 
    id,
    email,
    raw_user_meta_data,
    created_at,
    last_sign_in_at
FROM auth.users 
WHERE deleted_at IS NULL;
```

### **Get User Content Statistics**
```sql
SELECT * FROM get_user_content_count('user-uuid-here');
```

### **Get User's Generation Sessions**
```sql
SELECT * FROM get_ai_generation_sessions('user-uuid-here', 10);
```

## 🚀 **Benefits of This Approach**

1. **Simplified Architecture** - No joins or sync issues
2. **Automatic Consistency** - Data always in sync with auth
3. **Better Performance** - No additional queries
4. **Follows Supabase Best Practices** - Use built-in features
5. **Easier Maintenance** - Less code to manage

## 🔒 **Security Considerations**

- **JWT Tokens** - Used for authentication
- **Metadata Access** - Controlled through Supabase Auth
- **Content Isolation** - Users can only access their own content via `user_id`

## 📝 **Usage Examples**

### **Registration**
```python
# Backend
metadata = UserMetadata(full_name="John Doe", grade_level="5th")
auth_response = supabase.auth.sign_up({
    "email": "john@example.com",
    "password": "password123",
    "options": {"data": metadata.dict(exclude_none=True)}
})
```

### **Profile Update**
```python
# Backend
result = supabase.auth.admin.update_user_by_id(
    str(user_id),
    {"user_metadata": {"full_name": "John Smith", "grade_level": "6th"}}
)
```

### **Content Tracking**
```sql
-- Insert generation session
INSERT INTO ai_generation_sessions (id, user_id, request_params, status)
VALUES ('job-123', 'user-uuid', '{"sections": ["math"]}', 'completed');

-- Get user statistics
SELECT * FROM get_user_content_count('user-uuid');
```

## 🔄 **Migration from Previous Version**

If migrating from the previous version with `user_profiles` table:

1. **Export existing data** from `user_profiles`
2. **Update `auth.users` metadata** with profile data
3. **Drop `user_profiles` table**
4. **Update application code** to use new approach

## 📚 **References**

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [NestJS Supabase Auth Project](https://github.com/hiro1107/nestjs-supabase-auth)
- [Supabase User Metadata](https://supabase.com/docs/guides/auth/managing-user-data) 