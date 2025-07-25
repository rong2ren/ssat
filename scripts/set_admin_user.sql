-- ========================================
-- SET USER AS ADMIN
-- Run this in Supabase SQL Editor
-- ========================================

-- Replace 'rong2ren@gmail.com' with the email of the user you want to make admin
UPDATE auth.users
SET raw_user_meta_data = jsonb_set(
  COALESCE(raw_user_meta_data, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email = '';

-- Verify the update
SELECT 
    id,
    email,
    raw_user_meta_data->>'role' as role,
FROM auth.users 
WHERE email = ''; 