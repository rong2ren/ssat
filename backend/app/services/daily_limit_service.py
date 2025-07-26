"""
Daily Limit Service
Simple, clean implementation for SSAT section-based daily limits
"""

import logging
from datetime import date
from typing import Dict, Optional, Tuple, Any
from supabase import Client

logger = logging.getLogger(__name__)

class DailyLimitService:
    """Service for managing user daily usage limits by SSAT section"""
    
    # Default limits for free users - one full test
    DEFAULT_LIMITS = {
        "quantitative": 30,      # 30 math questions per day
        "analogy": 18,           # 18 analogy questions per day
        "synonyms": 12,          # 12 synonym questions per day
        "reading_passages": 7,  # 7 reading passages per day
        "writing": 1             # 1 writing prompts per day
    }
    
    # Premium user limits (4 full tests)
    PREMIUM_LIMITS = {
        "quantitative": 120,
        "analogy": 120,
        "synonyms": 120,
        "reading_passages": 40,
        "writing": 4
    }
    
    # Admin/Unlimited user limits
    UNLIMITED_LIMITS = {
        "quantitative": -1,      # -1 means unlimited
        "analogy": -1,
        "synonyms": -1,
        "reading_passages": -1,
        "writing": -1
    }
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_user_limits(self, user_id: str, user_metadata: Optional[Dict] = None) -> Dict[str, int]:
        """Get user's daily limits from metadata or return defaults"""
        try:
            # Use provided metadata or return defaults
            if user_metadata:
                # Check user role first
                user_role = user_metadata.get('role', 'free')
                
                # Admin/Unlimited users
                if user_role in ['admin', 'unlimited']:
                    return self.UNLIMITED_LIMITS
                
                # Premium users
                elif user_role == 'premium':
                    return self.PREMIUM_LIMITS
                
                # Free users with custom limits
                else:
                    custom_limits = user_metadata.get('daily_limits', {})
                    if not custom_limits:
                        return self.DEFAULT_LIMITS
                    else:
                        return {
                            "quantitative": custom_limits.get("quantitative", self.DEFAULT_LIMITS["quantitative"]),
                            "analogy": custom_limits.get("analogy", self.DEFAULT_LIMITS["analogy"]),
                            "synonyms": custom_limits.get("synonyms", self.DEFAULT_LIMITS["synonyms"]),
                            "reading_passages": custom_limits.get("reading_passages", self.DEFAULT_LIMITS["reading_passages"]),
                            "writing": custom_limits.get("writing", self.DEFAULT_LIMITS["writing"])
                        }
            
            return self.DEFAULT_LIMITS
            
        except Exception as e:
            logger.error(f"Error getting user limits for {user_id}: {e}")
            return self.DEFAULT_LIMITS
    
    async def get_current_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current usage with automatic reset if needed"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 DEBUG: Getting current usage for user {user_id} (attempt {attempt + 1}/{max_retries})")
                
                # Use Supabase RPC to call our database function
                response = self.supabase.rpc(
                    'get_or_create_user_daily_limits',
                    {'p_user_id': user_id}
                ).execute()
                
                logger.info(f"🔍 DEBUG: Database response: {response.data}")
                
                if response.data:
                    usage_data = response.data[0] if isinstance(response.data, list) else response.data
                    result = {
                        "user_id": usage_data.get("user_id"),
                        "last_reset_date": usage_data.get("last_reset_date"),
                        "quantitative_generated": usage_data.get("quantitative_generated", 0),
                        "analogy_generated": usage_data.get("analogy_generated", 0),
                        "synonyms_generated": usage_data.get("synonyms_generated", 0),
                        "reading_passages_generated": usage_data.get("reading_passages_generated", 0),
                        "writing_generated": usage_data.get("writing_generated", 0),
                        "needs_reset": usage_data.get("needs_reset", False)
                    }
                    logger.info(f"🔍 DEBUG: Returning usage data: {result}")
                    return result
                
                logger.warning(f"🔍 DEBUG: No data returned from database, using fallback")
                # Fallback if function fails
                return await self._get_usage_fallback(user_id)
                
            except Exception as e:
                logger.error(f"🔍 DEBUG: Error getting current usage for {user_id} (attempt {attempt + 1}/{max_retries}): {e}")
                
                # If this is the last attempt, use fallback
                if attempt == max_retries - 1:
                    logger.warning(f"🔍 DEBUG: All retries failed for user {user_id}, using fallback")
                    return await self._get_usage_fallback(user_id)
                
                # Wait before retrying
                import asyncio
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # This should never be reached, but just in case
        return await self._get_usage_fallback(user_id)
    
    async def _get_usage_fallback(self, user_id: str) -> Dict[str, Any]:
        """Fallback method if database function fails"""
        max_retries = 2
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 DEBUG: Fallback attempt {attempt + 1}/{max_retries} for user {user_id}")
                
                # Query the user_daily_limits table directly
                response = self.supabase.table('user_daily_limits').select(
                    'last_reset_date, quantitative_generated, analogy_generated, synonyms_generated, reading_passages_generated, writing_generated'
                ).eq('user_id', user_id).execute()
                
                today = date.today()
                
                if not response.data:
                    # Create new record
                    self.supabase.table('user_daily_limits').insert({
                        'user_id': user_id,
                        'last_reset_date': today.isoformat()
                    }).execute()
                    
                    return {
                        "user_id": user_id,
                        "last_reset_date": today,
                        "quantitative_generated": 0,
                        "analogy_generated": 0,
                        "synonyms_generated": 0,
                        "reading_passages_generated": 0,
                        "writing_generated": 0,
                        "needs_reset": False
                    }
                
                row = response.data[0]
                last_reset_date = row['last_reset_date']
                if isinstance(last_reset_date, str):
                    last_reset_date = date.fromisoformat(last_reset_date)
                
                # Check if reset is needed
                if last_reset_date < today:
                    # Reset counters
                    self.supabase.table('user_daily_limits').update({
                        'quantitative_generated': 0,
                        'analogy_generated': 0,
                        'synonyms_generated': 0,
                        'reading_passages_generated': 0,
                        'writing_generated': 0,
                        'last_reset_date': today.isoformat(),
                        'updated_at': date.today().isoformat()
                    }).eq('user_id', user_id).execute()
                    
                    return {
                        "user_id": user_id,
                        "last_reset_date": today,
                        "quantitative_generated": 0,
                        "analogy_generated": 0,
                        "synonyms_generated": 0,
                        "reading_passages_generated": 0,
                        "writing_generated": 0,
                        "needs_reset": True
                    }
                
                return {
                    "user_id": user_id,
                    "last_reset_date": last_reset_date,
                    "quantitative_generated": row['quantitative_generated'],
                    "analogy_generated": row['analogy_generated'],
                    "synonyms_generated": row['synonyms_generated'],
                    "reading_passages_generated": row['reading_passages_generated'],
                    "writing_generated": row['writing_generated'],
                    "needs_reset": False
                }
                
            except Exception as e:
                logger.error(f"🔍 DEBUG: Fallback error for user {user_id} (attempt {attempt + 1}/{max_retries}): {e}")
                
                # If this is the last attempt, return default values
                if attempt == max_retries - 1:
                    logger.warning(f"🔍 DEBUG: All fallback attempts failed for user {user_id}, returning default values")
                    return {
                        "user_id": user_id,
                        "last_reset_date": date.today(),
                        "quantitative_generated": 0,
                        "analogy_generated": 0,
                        "synonyms_generated": 0,
                        "reading_passages_generated": 0,
                        "writing_generated": 0,
                        "needs_reset": False
                    }
                
                # Wait before retrying
                import asyncio
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # This should never be reached, but just in case
        return {
            "user_id": user_id,
            "last_reset_date": date.today(),
            "quantitative_generated": 0,
            "analogy_generated": 0,
            "synonyms_generated": 0,
            "reading_passages_generated": 0,
            "writing_generated": 0,
            "needs_reset": False
        }
    
    async def check_and_increment(self, user_id: str, section: str, user_metadata: Optional[Dict] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user can generate content for a section and increment usage if allowed
        
        Args:
            user_id: User ID
            section: SSAT section ('quantitative', 'analogy', 'synonyms', 'reading_passages', 'writing')
            user_metadata: User metadata for role/limits
            
        Returns:
            Tuple of (success: bool, usage_info: dict)
        """
        try:
            logger.info(f"🔍 DEBUG: Starting check_and_increment for user {user_id}, section '{section}'")
            logger.info(f"🔍 DEBUG: Section parameter received: '{section}'")
            logger.info(f"🔍 DEBUG: User metadata: {user_metadata}")
            
            # Get user limits first to check if unlimited
            limits = await self.get_user_limits(user_id, user_metadata)
            limit_value = limits.get(section, 0)
            
            logger.info(f"🔍 DEBUG: User {user_id} has limit {limit_value} for section {section}")
            logger.info(f"🔍 DEBUG: All limits: {limits}")
            
            # If unlimited (-1), always allow
            if limit_value == -1:
                logger.debug(f"🔍 DAILY LIMITS: User {user_id} has unlimited access for section {section}")
                # Still increment usage for tracking, but don't block
                try:
                    response = self.supabase.rpc(
                        'increment_user_daily_usage',
                        {
                            'p_user_id': user_id,
                            'p_section': section
                        }
                    ).execute()
                    logger.debug(f"🔍 DAILY LIMITS: Incremented usage for unlimited user {user_id}, section {section}")
                except Exception as inc_error:
                    logger.warning(f"🔍 DAILY LIMITS: Failed to increment usage for unlimited user {user_id}, section {section}: {inc_error}")
                    # If increment fails, still allow for unlimited users
                    pass
                
                usage_info = await self.get_current_usage(user_id)
                logger.debug(f"🔍 DAILY LIMITS: Unlimited user {user_id} current usage for {section}: {usage_info.get(f'{section}_generated', 0)}")
                return True, {
                    "usage": usage_info,
                    "limits": limits,
                    "remaining": self._calculate_remaining(usage_info, limits)
                }
            
            # For limited users, check limits in Python first
            usage = await self.get_current_usage(user_id)
            current_count = usage.get(f"{section}_generated", 0)
            
            logger.info(f"🔍 DEBUG: User {user_id} current usage for {section}: {current_count}/{limit_value}")
            logger.info(f"🔍 DEBUG: Full usage data: {usage}")
            
            # Check if limit would be exceeded (we're about to increment by 1)
            if limit_value > 0 and current_count >= limit_value:
                logger.warning(f"🔍 DEBUG: User {user_id} exceeded limit for {section}: {current_count}/{limit_value}")
                logger.info(f"🔍 DEBUG: Returning False due to limit exceeded")
                return False, {
                    "usage": usage,
                    "limits": limits,
                    "remaining": self._calculate_remaining(usage, limits),
                    "error": f"Daily limit exceeded for {section}"
                }
            
            # If within limits, increment usage
            logger.info(f"🔍 DEBUG: Incrementing usage for user {user_id}, section '{section}' from {current_count} to {current_count + 1}")
            logger.info(f"🔍 DEBUG: Calling SQL function with p_user_id={user_id}, p_section='{section}'")
            response = self.supabase.rpc(
                'increment_user_daily_usage',
                {
                    'p_user_id': user_id,
                    'p_section': section
                }
            ).execute()
            logger.info(f"🔍 DEBUG: SQL function response: {response.data}")
            
            success = response.data if response.data is not None else False
            
            if not success:
                logger.error(f"🔍 DEBUG: ❌ SQL increment failed for user {user_id}, section {section}")
                return False, {
                    "usage": usage,
                    "limits": limits,
                    "remaining": self._calculate_remaining(usage, limits),
                    "error": f"Failed to increment usage for {section}"
                }
            
            # Calculate updated usage locally instead of making another database call
            usage_info = usage.copy()
            usage_info[f"{section}_generated"] = current_count + 1
            new_count = current_count + 1
            
            logger.info(f"🔍 DEBUG: ✅ Successfully incremented usage for user {user_id}, section {section}: {current_count} → {new_count}")
            logger.info(f"🔍 DEBUG: Returning success with calculated usage: {usage_info}")
            
            return True, {
                "usage": usage_info,
                "limits": limits,
                "remaining": self._calculate_remaining(usage_info, limits)
            }
            
        except Exception as e:
            logger.error(f"🔍 DEBUG: ❌ Error checking/incrementing usage for {user_id}, {section}: {e}")
            logger.error(f"🔍 DEBUG: Exception details: {type(e).__name__}: {str(e)}")
            return False, {"error": str(e)}
    
    async def get_remaining_limits(self, user_id: str, user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Get user's remaining limits for all sections"""
        try:
            usage = await self.get_current_usage(user_id)
            limits = await self.get_user_limits(user_id, user_metadata)
            
            return {
                "usage": usage,
                "limits": limits,
                "remaining": self._calculate_remaining(usage, limits)
            }
            
        except Exception as e:
            logger.error(f"Error getting remaining limits for {user_id}: {e}")
            return {
                "usage": None,
                "limits": self.DEFAULT_LIMITS,
                "remaining": self.DEFAULT_LIMITS,
                "error": str(e)
            }
    
    def _calculate_remaining(self, usage: Dict[str, Any], limits: Dict[str, int]) -> Dict[str, int]:
        """Calculate remaining limits for all sections"""
        # Add null safety
        if not usage or not limits:
            logger.warning(f"🔍 DEBUG: Usage or limits is None/empty. Usage: {usage}, Limits: {limits}")
            return {
                "quantitative": 0,
                "analogy": 0,
                "synonyms": 0,
                "reading_passages": 0,
                "writing": 0
            }
        
        return {
            "quantitative": -1 if limits.get("quantitative") == -1 else max(0, limits.get("quantitative", 0) - usage.get("quantitative_generated", 0)),
            "analogy": -1 if limits.get("analogy") == -1 else max(0, limits.get("analogy", 0) - usage.get("analogy_generated", 0)),
            "synonyms": -1 if limits.get("synonyms") == -1 else max(0, limits.get("synonyms", 0) - usage.get("synonyms_generated", 0)),
            "reading_passages": -1 if limits.get("reading_passages") == -1 else max(0, limits.get("reading_passages", 0) - usage.get("reading_passages_generated", 0)),
            "writing": -1 if limits.get("writing") == -1 else max(0, limits.get("writing", 0) - usage.get("writing_generated", 0))
        }
    
    def determine_section(self, request_type: str, question_type: Optional[str] = None) -> str:
        """
        Determine the SSAT section based on the generation request
        
        Args:
            request_type: Type of request ('questions', 'reading', 'writing')
            question_type: Specific question type for individual questions
            
        Returns:
            Section string
        """
        if request_type == "reading":
            return "reading_passages"
        elif request_type == "writing":
            return "writing"
        elif request_type == "questions":
            # Individual questions (math, verbal)
            if question_type == "quantitative" or question_type == "math":
                return "quantitative"
            elif question_type == "analogy":
                return "analogy"
            elif question_type == "synonym" or question_type == "synonyms":
                return "synonyms"
            else:
                return "quantitative"  # Default fallback
        else:
            return "quantitative"  # Default fallback 