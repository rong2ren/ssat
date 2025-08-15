"""
Pool Selection Service
Service for selecting unused questions from existing AI-generated content pools
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from supabase import Client
from app.services.database import get_database_connection

logger = logging.getLogger(__name__)

class PoolSelectionService:
    """Service for selecting unused questions from existing AI-generated content pools."""
    
    def __init__(self):
        self.supabase = get_database_connection()
    
    async def get_unused_questions_for_user(
        self, 
        user_id: str, 
        section: str, 
        count: int, 
        difficulty: Optional[str] = None,
        subsection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get unused questions for a user from existing AI-generated content."""
        
        try:
            logger.info(f"🔍 POOL SERVICE: Getting {count} unused {section} questions for user {user_id}")
            logger.info(f"🔍 POOL SERVICE DEBUG: Section={section}, Difficulty={difficulty}, Subsection={subsection}")
            
            # Use database function to get unused questions
            response = self.supabase.rpc(
                'get_unused_questions_for_user',
                {
                    'p_user_id': user_id,
                    'p_section': section,
                    'p_difficulty': difficulty,
                    'p_subsection': subsection,  # Add subsection parameter
                    'p_limit_count': count
                }
            ).execute()
            
            if response.data:
                questions = response.data
                logger.info(f"🔍 POOL SERVICE: ✅ Found {len(questions)} unused {section} questions for user {user_id}")
                logger.info(f"🔍 POOL SERVICE DEBUG: Question IDs: {[q.get('id', '')[:8] + '...' for q in questions[:3]]}")
                return questions
            else:
                logger.info(f"🔍 POOL SERVICE: ❌ No unused {section} questions found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"🔍 POOL SERVICE: ❌ Error getting unused questions for user {user_id}: {e}")
            return []
    
    async def get_quantitative_questions_with_subsection_breakdown(
        self, 
        user_id: str, 
        total_count: int = 30, 
        difficulty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get quantitative questions with proper subsection breakdown for complete tests ONLY."""
        
        try:
            logger.info(f"🎯 COMPLETE TEST POOL: Getting {total_count} quantitative questions with subsection breakdown for user {user_id}")
            
            # Use EXACT same domain groups as admin 5-call strategy (ACTUAL database subsections)
            domain_groups = [
                {
                    "group_name": "Number Operations",
                    "subsections": {
                        "Number Properties": 3,    # 32 available - number relationships, place value
                        "Fractions": 3,           # 21 available - fraction operations  
                        "Arithmetic": 3,          # 18 available - basic operations
                        "Word Problems": 2,       # 16 available - problem solving contexts
                        "Decimals": 1             # 2 available - decimal operations
                    }
                },
                {
                    "group_name": "Algebra & Functions", 
                    "subsections": {
                        "Algebra": 4,             # 16 available - equations, expressions
                        "Number Sequences": 2     # 2 available - patterns and sequences
                    }
                },
                {
                    "group_name": "Geometry & Spatial",
                    "subsections": {
                        "Geometry": 7             # 25 available - shapes, area, perimeter, angles, spatial reasoning
                    }
                },
                {
                    "group_name": "Measurement", 
                    "subsections": {
                        "Measurement": 2,         # 10 available - units, conversions
                        "Money": 1                # 4 available - money calculations
                    }
                },
                {
                    "group_name": "Data & Probability",
                    "subsections": {
                        "Data Interpretation": 1,  # 9 available - reading graphs, tables
                        "Probability": 1          # 1 available - basic probability
                    }
                }
            ]
            
            # Verify total count matches
            expected_total = sum(
                sum(group["subsections"].values()) 
                for group in domain_groups
            )
            if expected_total != total_count:
                logger.warning(f"🎯 COMPLETE TEST POOL: Domain breakdown total {expected_total} != requested {total_count}")
            
            # Collect questions by subsection
            all_pool_questions = []
            subsection_stats = {}
            
            for group in domain_groups:
                group_name = group["group_name"]
                logger.info(f"🎯 COMPLETE TEST POOL: Collecting {group_name} questions")
                
                for subsection, needed_count in group["subsections"].items():
                    logger.info(f"🎯 COMPLETE TEST POOL: Requesting {needed_count} {subsection} questions")
                    
                    subsection_questions = await self.get_unused_questions_for_user(
                        user_id=user_id,
                        section="Quantitative",
                        subsection=subsection,  # Specific subsection filtering
                        count=needed_count,
                        difficulty=difficulty
                    )
                    
                    found_count = len(subsection_questions)
                    subsection_stats[subsection] = {"needed": needed_count, "found": found_count}
                    
                    if found_count > 0:
                        all_pool_questions.extend(subsection_questions[:needed_count])
                        logger.info(f"🎯 COMPLETE TEST POOL: ✅ Found {found_count}/{needed_count} {subsection} questions")
                    else:
                        logger.info(f"🎯 COMPLETE TEST POOL: ❌ No {subsection} questions available")
            
            # Log summary statistics
            total_found = len(all_pool_questions)
            logger.info(f"🎯 COMPLETE TEST POOL: Summary - Found {total_found}/{total_count} questions")
            logger.info(f"🎯 COMPLETE TEST POOL: Subsection breakdown: {subsection_stats}")
            
            # Return questions (may be less than requested if pool insufficient)
            return all_pool_questions
            
        except Exception as e:
            logger.error(f"🎯 COMPLETE TEST POOL: ❌ Error getting subsection breakdown for user {user_id}: {e}")
            return []
    
    async def get_unused_reading_content_for_user(
        self, 
        user_id: str, 
        count: int,
        difficulty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get unused reading passages and questions for a user."""
        
        try:
            logger.info(f"🔍 POOL SERVICE: Getting {count} unused reading passages for user {user_id}")
            logger.info(f"🔍 POOL SERVICE DEBUG: Difficulty={difficulty}")
            
            # Use database function to get unused reading content
            response = self.supabase.rpc(
                'get_unused_reading_content_for_user',
                {
                    'p_user_id': user_id,
                    'p_limit_count': count,
                    'p_difficulty': difficulty
                }
            ).execute()
            
            if response.data:
                content = response.data
                logger.info(f"🔍 POOL SERVICE: ✅ Found {len(content)} unused reading passages for user {user_id}")
                
                # Group by passage
                passages = {}
                for item in content:
                    passage_id = item['passage_id']
                    if passage_id not in passages:
                        passages[passage_id] = {
                            'passage_id': passage_id,
                            'passage': item['passage'],
                            'passage_type': item['passage_type'],
                            'generation_session_id': item['generation_session_id'],
                            'created_at': item['created_at'],
                            'questions': []
                        }
                    
                    # Add question to passage
                    passages[passage_id]['questions'].append({
                        'id': item['question_id'],
                        'question': item['question'],
                        'choices': item['choices'],
                        'answer': item['answer'],
                        'explanation': item['explanation'],
                        'difficulty': item['difficulty'],
                        'visual_description': item['visual_description']
                    })
                    
                    # Add topic to passage if not already set (topic is not stored in DB, generate from passage_type)
                    if 'topic' not in passages[passage_id]:
                        passage_type = item.get('passage_type', 'General')
                        # Generate topic from passage type
                        topic_mapping = {
                            'fiction': 'Fiction Reading',
                            'non_fiction': 'Non-Fiction Reading', 
                            'poetry': 'Poetry Reading',
                            'biography': 'Biography Reading',
                            'science': 'Science Reading',
                            'history': 'History Reading'
                        }
                        if passage_type:
                            passages[passage_id]['topic'] = topic_mapping.get(passage_type.lower(), f'{passage_type.title()} Reading')
                        else:
                            passages[passage_id]['topic'] = 'General Reading'
                
                # Only return passages that have at least one question
                valid_passages = [p for p in list(passages.values()) if len(p['questions']) > 0]
                logger.info(f"🔍 POOL SERVICE: ✅ Returning {len(valid_passages)} valid passages with questions")
                logger.info(f"🔍 POOL SERVICE DEBUG: Passage IDs: {[p['passage_id'][:8] + '...' for p in valid_passages[:3]]}")
                return valid_passages
            else:
                logger.info(f"🔍 POOL SERVICE: ❌ No unused reading content found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"🔍 POOL SERVICE: ❌ Error getting unused reading content for user {user_id}: {e}")
            return []
    
    async def get_unused_writing_prompts_for_user(
        self, 
        user_id: str, 
        count: int
    ) -> List[Dict[str, Any]]:
        """Get unused writing prompts for a user."""
        
        try:
            logger.info(f"🔍 POOL: Getting {count} unused writing prompts for user {user_id}")
            
            # Use database function to get unused writing prompts
            response = self.supabase.rpc(
                'get_unused_writing_prompts_for_user',
                {
                    'p_user_id': user_id,
                    'p_limit_count': count
                }
            ).execute()
            
            if response.data:
                prompts = response.data
                logger.info(f"🔍 POOL: Found {len(prompts)} unused writing prompts for user {user_id}")
                return prompts
            else:
                logger.info(f"🔍 POOL: No unused writing prompts found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"🔍 POOL: Error getting unused writing prompts for user {user_id}: {e}")
            return []
    
    async def mark_content_as_used(
        self, 
        user_id: str, 
        question_ids: Optional[List[str]] = None,
        passage_ids: Optional[List[str]] = None,
        writing_prompt_ids: Optional[List[str]] = None,
        usage_type: str = "custom_section",
        content_type: Optional[str] = None  # Add content_type parameter
    ):
        """Mark content as used by a user."""
        
        try:
            usage_records = []
            
            # Mark questions as used
            if question_ids:
                for question_id in question_ids:
                    usage_records.append({
                        "user_id": user_id,
                        "question_id": question_id,
                        "content_type": content_type or "quantitative",  # Use specific type or default
                        "usage_type": usage_type
                    })
            
            # Mark passages as used
            if passage_ids:
                for passage_id in passage_ids:
                    usage_records.append({
                        "user_id": user_id,
                        "question_id": passage_id,  # Reuse question_id field for passage_id
                        "content_type": "reading",
                        "usage_type": usage_type
                    })
            
            # Mark writing prompts as used
            if writing_prompt_ids:
                for prompt_id in writing_prompt_ids:
                    usage_records.append({
                        "user_id": user_id,
                        "question_id": prompt_id,  # Reuse question_id field for prompt_id
                        "content_type": "writing",
                        "usage_type": usage_type
                    })
            
            # Insert usage records
            if usage_records:
                try:
                    self.supabase.table("user_question_usage").insert(usage_records).execute()
                    logger.info(f"🔍 POOL SERVICE: ✅ Marked {len(usage_records)} content items as used by user {user_id}")
                    logger.info(f"🔍 POOL SERVICE DEBUG: Usage records: {[r['question_id'][:8] + '...' for r in usage_records[:3]]}")
                except Exception as insert_error:
                    # Handle duplicate key constraint - this can happen if the user already used this content
                    if "duplicate key value violates unique constraint" in str(insert_error):
                        logger.warning(f"🔍 POOL SERVICE: ⚠️ Some content already marked as used for user {user_id} - this is expected if user already used this content")
                        # Don't raise the error, just log it
                    else:
                        # Re-raise other errors
                        raise insert_error
            
        except Exception as e:
            logger.error(f"🔍 POOL: Error marking content as used for user {user_id}: {e}")
            raise
    
    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current pool."""
        
        try:
            # Get total counts from each table
            questions_response = self.supabase.table("ai_generated_questions").select("id").execute()
            reading_response = self.supabase.table("ai_generated_reading_passages").select("id").execute()
            writing_response = self.supabase.table("ai_generated_writing_prompts").select("id").execute()
            
            # Get usage counts
            usage_response = self.supabase.table("user_question_usage").select("content_type").execute()
            
            total_questions = len(questions_response.data) if questions_response.data else 0
            total_reading = len(reading_response.data) if reading_response.data else 0
            total_writing = len(writing_response.data) if writing_response.data else 0
            
            # Calculate usage by content type
            usage_by_type = {}
            if usage_response.data:
                for item in usage_response.data:
                    content_type = item['content_type']
                    usage_by_type[content_type] = usage_by_type.get(content_type, 0) + 1
            
            return {
                "total_questions": total_questions,
                "total_reading_passages": total_reading,
                "total_writing_prompts": total_writing,
                "usage_by_type": usage_by_type,
                "total_usage": sum(usage_by_type.values())
            }
            
        except Exception as e:
            logger.error(f"🔍 POOL: Error getting pool statistics: {e}")
            return {}
    
    async def get_user_usage_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for a specific user."""
        
        try:
            response = self.supabase.table("user_question_usage").select(
                "content_type, usage_type"
            ).eq("user_id", user_id).execute()
            
            usage_by_type = {}
            usage_by_request_type = {}
            
            for item in response.data:
                content_type = item['content_type']
                usage_type = item['usage_type']
                
                usage_by_type[content_type] = usage_by_type.get(content_type, 0) + 1
                usage_by_request_type[usage_type] = usage_by_request_type.get(usage_type, 0) + 1
            
            return {
                "user_id": user_id,
                "total_quantitative_used": usage_by_type.get('quantitative', 0),
                "total_analogy_used": usage_by_type.get('analogy', 0),
                "total_synonyms_used": usage_by_type.get('synonyms', 0),
                "total_reading_used": usage_by_type.get('reading', 0),
                "total_writing_used": usage_by_type.get('writing', 0),
                "full_tests_generated": usage_by_request_type.get('full_test', 0),
                "custom_sections_generated": usage_by_request_type.get('custom_section', 0),
                "total_content_used": sum(usage_by_type.values()),
                "usage_by_type": usage_by_type,
                "usage_by_request_type": usage_by_request_type
            }
            
        except Exception as e:
            logger.error(f"🔍 POOL: Error getting user usage statistics: {e}")
            return {} 