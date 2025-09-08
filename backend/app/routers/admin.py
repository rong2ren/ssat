"""Admin endpoints for SSAT API."""


from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from supabase import create_client

from app.models.user import UserProfile
from app.models.requests import QuestionGenerationRequest, CompleteTestRequest, TrainingExamplesRequest
from app.models.responses import QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse
from app.auth import get_current_user
from app.services.daily_limit_service import DailyLimitService
from app.services.content_generation_service import ContentGenerationService
from app.services.ai_content_service import AIContentService
from app.services.training_examples_service import TrainingExamplesService
from app.services.embedding_service import get_embedding_service
from app.config.app_config import get_app_config
from pydantic import BaseModel

# Initialize configuration
def get_config():
    """Get application configuration."""
    return get_app_config()

router = APIRouter(prefix="/admin", tags=["admin"])

# Initialize services - will be refactored later with dependency injection (singleton pattern)
content_service = None

def get_content_service():
    global content_service
    if content_service is None:
        content_service = ContentGenerationService()
    return content_service

def get_ai_content_service():
    """Get AI content service."""
    return AIContentService()

def get_training_examples_service():
    """Get training examples service with configuration."""
    return TrainingExamplesService(
        create_client(get_config().supabase_url, get_config().supabase_key),
        get_embedding_service()
    )

class RoleUpdateRequest(BaseModel):
    role: str


def check_admin_access(current_user: UserProfile):
    """Helper function to check admin access."""
    if current_user.role != 'admin':
        logger.warning("🔍 ADMIN: User is not admin")
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )


@router.get("/users")
async def get_all_users(current_user: UserProfile = Depends(get_current_user)):
    """Get all users with their daily limits (admin only)."""
    try:
        logger.info("🔍 ADMIN: Starting get_all_users function")
        
        # Check if user is admin using the role from the dependency
        check_admin_access(current_user)
        
        logger.info("🔍 ADMIN: User is admin, proceeding with admin operations")
        
        # Use service role key for admin operations
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        logger.info("🔍 ADMIN: Service role key found, creating admin client")
        supabase_url = get_config().supabase_url
        admin_client = create_client(supabase_url, service_role_key)
        
        # Get all users from auth.users
        logger.info("🔍 ADMIN: Calling admin_client.auth.admin.list_users()")
        response = admin_client.auth.admin.list_users()
        users = response
        logger.info(f"🔍 ADMIN: Retrieved {len(users)} users from auth.users")
        
        # Get daily limits for all users
        logger.info("🔍 ADMIN: Calling admin_client.table('user_daily_limits').select('*').execute()")
        limits_response = admin_client.table('user_daily_limits').select('*').execute()
        limits_data = {row['user_id']: row for row in limits_response.data} if limits_response.data else {}
        logger.info(f"🔍 ADMIN: Retrieved limits data for {len(limits_data)} users")
        
        # Combine user data with limits
        logger.info("🔍 ADMIN: Combining user data with limits")
        users_with_limits = []
        for user in users:
            user_limits = limits_data.get(user.id, {})
            user_metadata = user.user_metadata or {}
            # Determine user role and limits
            role = user_metadata.get('role', 'free')
            if role == 'admin':
                limits = DailyLimitService.UNLIMITED_LIMITS
            elif role == 'premium':
                limits = DailyLimitService.PREMIUM_LIMITS
            else:
                custom_limits = user_metadata.get('daily_limits', {})
                limits = {
                    "quantitative": custom_limits.get("quantitative", DailyLimitService.DEFAULT_LIMITS["quantitative"]),
                    "analogy": custom_limits.get("analogy", DailyLimitService.DEFAULT_LIMITS["analogy"]),
                    "synonym": custom_limits.get("synonym", DailyLimitService.DEFAULT_LIMITS["synonym"]),
                    "reading_passages": custom_limits.get("reading_passages", DailyLimitService.DEFAULT_LIMITS["reading_passages"]),
                    "writing": custom_limits.get("writing", DailyLimitService.DEFAULT_LIMITS["writing"])
                }
            users_with_limits.append({
                "id": user.id,
                "email": user.email,
                "role": role,
                "created_at": user.created_at,
                "last_sign_in_at": user.last_sign_in_at,
                "limits": limits,
                "usage": {
                    "quantitative_generated": user_limits.get('quantitative_generated', 0),
                    "analogy_generated": user_limits.get('analogy_generated', 0),
                    "synonym_generated": user_limits.get('synonym_generated', 0),
                    "reading_passages_generated": user_limits.get('reading_passages_generated', 0),
                    "writing_generated": user_limits.get('writing_generated', 0),
                    "last_reset_date": user_limits.get('last_reset_date')
                }
            })
        
        logger.info(f"🔍 ADMIN: Successfully processed {len(users_with_limits)} users with limits")
        return {
            "success": True,
            "data": users_with_limits
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error getting all users: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Failed to get users"
        )


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role_request: RoleUpdateRequest, current_user: UserProfile = Depends(get_current_user)):
    """Update user role (admin only)."""
    try:
        check_admin_access(current_user)
        
        role = role_request.role
        
        # Validate role
        valid_roles = ['free', 'premium', 'admin', 'unlimited']
        if role not in valid_roles:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid role: {role}. Must be one of: {valid_roles}"
            )
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get current user data
        user_response = admin_client.auth.admin.get_user_by_id(user_id)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user metadata with new role
        current_metadata = user_response.user.user_metadata or {}
        updated_metadata = current_metadata.copy()
        updated_metadata['role'] = role
        
        # Update user in auth system
        admin_client.auth.admin.update_user_by_id(
            user_id,
            {"user_metadata": updated_metadata}
        )
        
        return {
            "success": True,
            "message": f"User role updated to {role}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user role"
        )


@router.post("/generate")
async def admin_generate_content(
    request: QuestionGenerationRequest,
    current_user: UserProfile = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate SSAT content with admin privileges (no daily limits)."""
    import time
    import uuid
    start_time = time.time()
    
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} generating {request.count} {request.question_type.value} content")
        logger.info(f"🔍 ADMIN: Request input_format: {getattr(request, 'input_format', 'NOT_SET')}")
        logger.info(f"🔍 ADMIN: Request use_custom_examples: {getattr(request, 'use_custom_examples', 'NOT_SET')}")
        logger.info(f"🔍 ADMIN: Request custom_examples: {getattr(request, 'custom_examples', 'NOT_SET')}")
        
        # Create session for admin generation
        session_id = str(uuid.uuid4())
        
        # Create session for admin generation
        await get_ai_content_service().create_generation_session(session_id, {
            "question_type": request.question_type.value,
            "count": request.count,
            "difficulty": request.difficulty.value if request.difficulty else None,
            "topic": request.topic,
            "provider": request.provider.value if request.provider else None,
            "admin_generation": True  # Mark as admin generation
        }, current_user.id)
        
        # Prepare user metadata for admin generation
        user_metadata = {
            'role': current_user.role,
            'grade_level': current_user.grade_level
        }
        
        # Generate content using the service with admin privileges (force LLM generation)
        result = await get_content_service().generate_individual_content(
            request, 
            force_llm_generation=True,
            user_id=str(current_user.id),
            user_metadata=user_metadata
        )
        
        # Save AI-generated content to database
        try:
            training_example_ids = result.metadata.training_example_ids if hasattr(result.metadata, 'training_example_ids') else []
            
            if isinstance(result, WritingGenerationResponse):
                # WritingGenerationResponse has .prompts
                logger.info(f"🔍 ADMIN GENERATE: Saving writing prompts to database - session: {session_id}, prompts count: {len(result.prompts)}")
                saved_prompt_ids = await get_ai_content_service().save_writing_prompts(session_id, {"writing_prompts": result.prompts}, training_example_ids)
                
                # Assign the database IDs back to the WritingPrompt objects
                for i, prompt in enumerate(result.prompts):
                    if i < len(saved_prompt_ids):
                        prompt.id = saved_prompt_ids[i]
                        logger.debug(f"Assigned database ID {saved_prompt_ids[i]} to writing prompt {i}")
                
                logger.info(f"🔍 ADMIN GENERATE: Successfully saved writing prompts to database")
            elif isinstance(result, ReadingGenerationResponse):
                # ReadingGenerationResponse has .passages
                logger.info(f"🔍 ADMIN GENERATE: Saving reading content to database - session: {session_id}, passages count: {len(result.passages)}")
                saved_ids = await get_ai_content_service().save_reading_content(
                    session_id, 
                    {"reading_sections": result.passages}, 
                    training_example_ids,
                    topic=request.topic or ""  # Pass the topic for tagging, default to empty string
                )
                
                # Assign the database IDs back to the ReadingPassage objects
                for i, passage in enumerate(result.passages):
                    if i < len(saved_ids.get('passage_ids', [])):
                        passage.id = saved_ids['passage_ids'][i]
                        logger.debug(f"Assigned database ID {saved_ids['passage_ids'][i]} to passage {i}")
                
                logger.info(f"🔍 ADMIN GENERATE: Successfully saved reading content to database")
            elif isinstance(result, QuestionGenerationResponse):
                # Regular questions (quantitative, analogy, synonym)
                # QuestionGenerationResponse has .questions
                section_mapping = {
                    "quantitative": "Quantitative",
                    "analogy": "Verbal",    # Analogies are part of Verbal section in database
                    "synonym": "Verbal"    # Synonyms are part of Verbal section in database
                }
                section_name = section_mapping.get(request.question_type.value, "Verbal")
                
                # Use AI-determined subsection - DO NOT OVERRIDE the AI's intelligent categorization
                if request.question_type.value == "analogy":
                    subsection = "Analogies"  # Fixed subsection for analogy questions
                elif request.question_type.value == "synonym":
                    subsection = "Synonyms"  # Fixed subsection for synonyms questions
                else:
                    # For quantitative and verbal questions, ALWAYS use AI-determined subsection
                    # The AI has analyzed the content and provided specific, educational categorization
                    subsection = None  # Will be extracted per question in save_generated_questions
                
                # Get training example IDs from the result metadata
                training_example_ids = result.metadata.training_example_ids
                logger.debug(f"Using training example IDs from result metadata: {training_example_ids}")
                
                # Save questions to database and get the generated IDs
                saved_question_ids = await get_ai_content_service().save_generated_questions(
                    session_id, 
                    result.questions,
                    section_name, 
                    subsection or "",  # Convert None to empty string
                    training_example_ids
                )
                
                # Assign the database IDs back to the Question objects
                for i, question in enumerate(result.questions):
                    if i < len(saved_question_ids):
                        question.id = saved_question_ids[i]
                        logger.debug(f"Assigned database ID {saved_question_ids[i]} to question {i}")
                
                logger.info(f"🔍 ADMIN GENERATE: Successfully saved {len(saved_question_ids)} questions to database")
            
            # Update session status to completed
            await get_ai_content_service().update_session_status(session_id, "completed")
            
        except Exception as save_error:
            logger.error(f"🔍 ADMIN GENERATE: Failed to save content to database: {save_error}")
            # Update session status to failed
            await get_ai_content_service().update_session_status(session_id, "failed")
            raise save_error
        
        # Calculate generation time
        generation_time = time.time() - start_time
        logger.info(f"🔍 ADMIN: Successfully generated {request.count} {request.question_type.value} for admin {current_user.id} in {generation_time:.2f}s")
        
        # Return response in the format expected by the frontend
        response_data = {
            "session_id": session_id,
            "generation_time_ms": int(generation_time * 1000),  # Convert to milliseconds
            "provider_used": request.provider.value if request.provider else "auto",
            "content": result,
            "status": "success",
            "count": request.count,
            "question_type": request.question_type.value
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin content generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate admin content"
        )


@router.post("/generate/complete-test")
async def admin_generate_complete_test(
    request: CompleteTestRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Generate complete SSAT test with admin privileges."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} generating complete test (FORCING LLM GENERATION)")
        
        # Create user metadata for admin user
        user_metadata = {
            'full_name': current_user.full_name,
            'grade_level': current_user.grade_level.value if current_user.grade_level else None,
            'role': current_user.role,
        }
        
        # Use content service for admin complete test generation with force LLM generation
        result = await get_content_service().generate_complete_test_async(
            request, 
            str(current_user.id), 
            force_llm_generation=True,
            user_metadata=user_metadata
        )
        
        # Get the job_id from the result
        job_id = result.get("job_id")
        
        # Determine which counts are being used (like in the backup version)
        from app.specifications import get_official_question_counts
        official_counts = get_official_question_counts()
        
        # Use official counts if is_official_format is True, otherwise use custom counts
        actual_counts = official_counts if request.is_official_format else request.custom_counts
        
        # Return detailed response like the backup version
        detailed_result = {
            "success": True,
            "message": f"Complete test generation started with {len(request.include_sections)} sections",
            "session_id": job_id,  # Use job_id as session_id for consistency
            "sections": [s.value for s in request.include_sections],
            "custom_counts": actual_counts,
            "is_official_format": request.is_official_format,
            "job_id": job_id,  # Keep job_id for compatibility
            "status": result.get("status", "started"),
            "estimated_time_minutes": result.get("estimated_time_minutes", 10)
        }
        
        logger.info(f"🔍 ADMIN: Complete test generation started for admin {current_user.id}")
        return detailed_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin complete test generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate admin complete test"
        )


@router.post("/save-training-examples")
async def save_training_examples(
    request: TrainingExamplesRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Save training examples to database (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} saving training examples")
        
        # Use training examples service with correct method signature
        result = await get_training_examples_service().save_training_examples(request, str(current_user.id))
        
        logger.info(f"🔍 ADMIN: Successfully saved training examples")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save training examples: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save training examples"
        )


@router.post("/migrate-training-to-pool")
async def migrate_training_to_pool(
    current_user: UserProfile = Depends(get_current_user)
):
    """Migrate training examples to pool questions (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} starting training to pool migration")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get migration statistics before migration
        stats_response = admin_client.rpc('get_migration_statistics').execute()
        before_stats = stats_response.data[0] if stats_response.data else {}
        
        # Run the migration
        migration_response = admin_client.rpc('migrate_all_training_to_pool').execute()
        migration_result = migration_response.data[0] if migration_response.data else {}
        
        # Get migration statistics after migration
        stats_response_after = admin_client.rpc('get_migration_statistics').execute()
        after_stats = stats_response_after.data[0] if stats_response_after.data else {}
        
        return {
            "success": True,
            "message": "Training examples successfully migrated to user pool",
            "migration_results": {
                "questions_migrated": migration_result.get('migrated_questions', 0),
                "passages_migrated": migration_result.get('migrated_passages', 0),
                "reading_questions_migrated": migration_result.get('migrated_reading_questions', 0),
                "writing_prompts_migrated": migration_result.get('migrated_writing_prompts', 0),
                "total_skipped": migration_result.get('total_skipped', 0),
                "total_errors": migration_result.get('total_errors', 0)
            },
            "before_migration": {
                "training_questions": before_stats.get('training_questions_count', 0),
                "training_passages": before_stats.get('training_passages_count', 0),
                "training_reading_questions": before_stats.get('training_reading_questions_count', 0),
                "training_writing_prompts": before_stats.get('training_writing_prompts_count', 0),
                "pool_questions": before_stats.get('pool_questions_count', 0),
                "pool_passages": before_stats.get('pool_passages_count', 0),
                "pool_reading_questions": before_stats.get('pool_reading_questions_count', 0),
                "pool_writing_prompts": before_stats.get('pool_writing_prompts_count', 0)
            },
            "after_migration": {
                "pool_questions": after_stats.get('pool_questions_count', 0),
                "pool_passages": after_stats.get('pool_passages_count', 0),
                "pool_reading_questions": after_stats.get('pool_reading_questions_count', 0),
                "pool_writing_prompts": after_stats.get('pool_writing_prompts_count', 0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to migrate training examples"
        )


@router.get("/migration-statistics")
async def get_migration_statistics(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get migration statistics (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} requesting migration statistics")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get migration statistics using RPC function
        stats_response = admin_client.rpc('get_migration_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        statistics = {
            "training_content": {
                "questions": stats.get('training_questions_count', 0),
                "passages": stats.get('training_passages_count', 0),
                "reading_questions": stats.get('training_reading_questions_count', 0),
                "writing_prompts": stats.get('training_writing_prompts_count', 0)
            },
            "pool_content": {
                "questions": stats.get('pool_questions_count', 0),
                "passages": stats.get('pool_passages_count', 0),
                "reading_questions": stats.get('pool_reading_questions_count', 0),
                "writing_prompts": stats.get('pool_writing_prompts_count', 0)
            },
            "migrated_content": {
                "questions": stats.get('migrated_questions_count', 0),
                "passages": stats.get('migrated_passages_count', 0),
                "reading_questions": stats.get('migrated_reading_questions_count', 0),
                "writing_prompts": stats.get('migrated_writing_prompts_count', 0)
            }
        }
        
        logger.info(f"🔍 ADMIN: Migration statistics retrieved successfully")
        return {
            "success": True,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get migration statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get migration statistics"
        )


@router.post("/cleanup-migrated-content")
async def cleanup_migrated_content(
    current_user: UserProfile = Depends(get_current_user)
):
    """Clean up migrated training examples (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} starting cleanup of migrated content")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Cleanup migrated content using RPC function
        cleanup_response = admin_client.rpc('cleanup_migrated_content').execute()
        cleanup_result = cleanup_response.data[0] if cleanup_response.data else {}
        
        cleaned_count = cleanup_result.get('removed_questions', 0) + cleanup_result.get('removed_passages', 0) + cleanup_result.get('removed_reading_questions', 0) + cleanup_result.get('removed_writing_prompts', 0)
        
        logger.info(f"🔍 ADMIN: Successfully archived {cleaned_count} migrated training examples")
        return {
            "success": True,
            "message": f"Successfully archived {cleaned_count} migrated training examples",
            "cleaned_count": cleaned_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup migrated content"
        )


@router.get("/statistics/overview")
async def get_admin_statistics_overview(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get admin dashboard statistics overview."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} requesting statistics overview")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get user statistics
        total_users = admin_client.auth.admin.list_users()
        user_count = len(total_users) if total_users else 0
        
        # Get user role distribution
        role_distribution = {}
        for user in total_users:
            user_metadata = user.user_metadata or {}
            role = user_metadata.get('role', 'free')
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        # Get overview statistics using database function (same as backup version)
        stats_response = admin_client.rpc('get_platform_overview_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        # Get usage statistics from daily limits
        today = datetime.now().date().isoformat()
        daily_usage = admin_client.table('user_daily_limits').select('*').gte('last_reset_date', today).execute()
        
        total_daily_usage = 0
        if daily_usage.data:
            for usage in daily_usage.data:
                total_daily_usage += (
                    usage.get('quantitative_generated', 0) +
                    usage.get('analogy_generated', 0) +
                    usage.get('synonym_generated', 0) +
                    usage.get('reading_passages_generated', 0) +
                    usage.get('writing_generated', 0)
                )
        
        statistics = {
            "users": {
                "total_users": stats.get('total_users', user_count),  # Use function result, fallback to auth count
                "role_distribution": role_distribution
            },
            "content": {
                "total_training_content": stats.get('total_training_content', 0),
                "total_ai_generated_content": stats.get('total_ai_generated_content', 0)
            },
            "generation": {
                "total_generation_sessions": stats.get('total_generation_sessions', 0),
                "successful_generations_last_7_days": stats.get('successful_generations_last_7_days', 0),
                "failed_generations_last_7_days": stats.get('failed_generations_last_7_days', 0),
                "success_rate_percentage": float(stats.get('success_rate_percentage', 0))
            },
            "usage": {
                "daily_generations_today": total_daily_usage,
                "active_users_today": len(daily_usage.data) if daily_usage.data else 0
            }
        }
        
        logger.info(f"🔍 ADMIN: Statistics overview retrieved successfully")
        return {
            "success": True,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get statistics overview: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get statistics overview"
        )

@router.get("/statistics/content")
async def admin_get_content_statistics(
    current_user: UserProfile = Depends(get_current_user)
):
    """Admin endpoint to get content breakdown statistics."""
    try:
        check_admin_access(current_user)
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get content statistics
        stats_response = admin_client.rpc('get_content_breakdown_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        return {
            "success": True,
            "statistics": {
                "training_content": {
                    "quantitative": stats.get('training_quantitative', 0),
                    "analogies": stats.get('training_analogies', 0),
                    "synonyms": stats.get('training_synonyms', 0),
                    "reading_passages": stats.get('training_reading_passages', 0),
                    "reading_questions": stats.get('training_reading_questions', 0),
                    "writing_prompts": stats.get('training_writing_prompts', 0)
                },
                "ai_generated_content": {
                    "quantitative": stats.get('ai_quantitative', 0),
                    "analogies": stats.get('ai_analogies', 0),
                    "synonyms": stats.get('ai_synonyms', 0),
                    "reading_passages": stats.get('ai_reading_passages', 0),
                    "reading_questions": stats.get('ai_reading_questions', 0),
                    "writing_prompts": stats.get('ai_writing_prompts', 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN STATISTICS: Error getting content statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get content statistics: {str(e)}"
        )


@router.get("/statistics/pool")
async def admin_get_pool_statistics(
    current_user: UserProfile = Depends(get_current_user)
):
    """Admin endpoint to get pool utilization statistics."""
    try:
        check_admin_access(current_user)
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get pool statistics
        stats_response = admin_client.rpc('get_pool_utilization_statistics').execute()
        logger.info(f"🔍 ADMIN POOL STATS: Raw response: {stats_response}")
        logger.info(f"🔍 ADMIN POOL STATS: Response data: {stats_response.data}")
        
        stats = stats_response.data[0] if stats_response.data else {}
        logger.info(f"🔍 ADMIN POOL STATS: Parsed stats: {stats}")
        
        # If no stats returned, provide default values
        if not stats:
            logger.warning("🔍 ADMIN POOL STATS: No stats returned from database function, using defaults")
            stats = {}
        
        result = {
            "success": True,
            "statistics": {
                "quantitative": {
                    "used": stats.get('quantitative_used', 0),
                    "remaining": stats.get('quantitative_remaining', 0)
                },
                "analogy": {
                    "used": stats.get('analogy_used', 0),
                    "remaining": stats.get('analogy_remaining', 0)
                },
                "synonym": {
                    "used": stats.get('synonym_used', 0),
                    "remaining": stats.get('synonym_remaining', 0)
                },
                "reading": {
                    "used": stats.get('reading_used', 0),
                    "remaining": stats.get('reading_remaining', 0)
                },
                "writing": {
                    "used": stats.get('writing_used', 0),
                    "remaining": stats.get('writing_remaining', 0)
                }
            }
        }
        
        logger.info(f"🔍 ADMIN POOL STATS: Final result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"🔍 ADMIN STATISTICS: Error getting pool statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool statistics: {str(e)}"
        )


@router.get("/statistics/pool/user-usage")
async def admin_get_pool_user_usage_statistics(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get pool usage statistics for all users."""
    try:
        check_admin_access(current_user)
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get all users
        users_response = admin_client.auth.admin.list_users()
        users = users_response if users_response else []
        
        # Get usage statistics for each user
        user_usage_stats = []
        
        for user in users:
            user_id = user.id
            user_email = user.email
            
            # Get user's pool usage statistics
            usage_response = admin_client.table("user_question_usage").select(
                "content_type, usage_type, created_at"
            ).eq("user_id", user_id).execute()
            
            # Calculate usage by content type
            usage_by_type = {}
            total_usage = 0
            
            for item in usage_response.data:
                content_type = item['content_type']
                usage_by_type[content_type] = usage_by_type.get(content_type, 0) + 1
                total_usage += 1
            
            # Get user metadata for role
            user_metadata = user.user_metadata or {}
            role = user_metadata.get('role', 'free')
            
            user_usage_stats.append({
                "user_id": user_id,
                "email": user_email,
                "role": role,
                "total_usage": total_usage,
                "quantitative_used": usage_by_type.get('quantitative', 0),
                "analogy_used": usage_by_type.get('analogy', 0),
                "synonym_used": usage_by_type.get('synonym', 0),
                "reading_used": usage_by_type.get('reading', 0),
                "writing_used": usage_by_type.get('writing', 0),
                "usage_by_type": usage_by_type
            })
        
        # Sort by total usage (descending)
        user_usage_stats.sort(key=lambda x: x['total_usage'], reverse=True)
        
        result = {
            "success": True,
            "user_count": len(user_usage_stats),
            "users": user_usage_stats
        }
        
        logger.info(f"🔍 ADMIN POOL USER USAGE: Retrieved usage stats for {len(user_usage_stats)} users")
        return result
        
    except Exception as e:
        logger.error(f"🔍 ADMIN STATISTICS: Error getting pool user usage statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool user usage statistics: {str(e)}"
        )


@router.get("/debug/difficulties")
async def get_difficulty_values(
    current_user: UserProfile = Depends(get_current_user)
):
    """Debug endpoint to see what difficulty values exist in the database."""
    try:
        check_admin_access(current_user)
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get distinct difficulty values from ssat_questions
        quantitative_response = admin_client.table('ssat_questions').select('difficulty').eq('section', 'Quantitative').execute()
        analogy_response = admin_client.table('ssat_questions').select('difficulty').eq('section', 'Verbal').eq('subsection', 'Analogies').execute()
        synonym_response = admin_client.table('ssat_questions').select('difficulty').eq('section', 'Verbal').eq('subsection', 'Synonyms').execute()
        
        # Get distinct difficulty values from reading_questions
        reading_response = admin_client.table('reading_questions').select('difficulty').execute()
        
        return {
            "quantitative_difficulties": list(set([item['difficulty'] for item in quantitative_response.data if item.get('difficulty')])),
            "analogy_difficulties": list(set([item['difficulty'] for item in analogy_response.data if item.get('difficulty')])),
            "synonym_difficulties": list(set([item['difficulty'] for item in synonym_response.data if item.get('difficulty')])),
            "reading_difficulties": list(set([item['difficulty'] for item in reading_response.data if item.get('difficulty')])),
        }
        
    except Exception as e:
        logger.error(f"Failed to get difficulty values: {e}")
        raise HTTPException(status_code=500, detail="Failed to get difficulty values")


@router.get("/training-examples")
async def get_training_examples(
    section: str = None,
    difficulty: str = None,
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all training examples grouped by section (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} requesting training examples with difficulty={difficulty}, section={section}")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Initialize training examples structure
        training_examples = {
            "quantitative": [],
            "analogy": [],
            "synonym": [],
            "reading": [],
            "writing": []
        }
        
        # If specific section requested, only fetch that section
        if section:
            logger.info(f"🔍 ADMIN: Fetching specific section: {section}")
            
            if section == "quantitative":
                try:
                    query = admin_client.table('ssat_questions').select('*').eq('section', 'Quantitative')
                    if difficulty:
                        logger.info(f"🔍 ADMIN: Adding difficulty filter: '{difficulty}'")
                        query = query.eq('difficulty', difficulty)
                    else:
                        logger.info(f"🔍 ADMIN: No difficulty filter applied")
                    quantitative_response = query.execute()
                    logger.info(f"🔍 ADMIN: Quantitative query returned {len(quantitative_response.data) if quantitative_response.data else 0} results")
                    if quantitative_response.data:
                        # Log a sample of the difficulties we got
                        sample_difficulties = [item.get('difficulty') for item in quantitative_response.data[:3]]
                        logger.info(f"🔍 ADMIN: Sample difficulties in results: {sample_difficulties}")
                        training_examples["quantitative"] = quantitative_response.data
                except Exception as e:
                    logger.warning(f"Failed to get quantitative training examples: {e}")
            
            elif section == "analogy":
                try:
                    query = admin_client.table('ssat_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Analogies')
                    if difficulty:
                        query = query.eq('difficulty', difficulty)
                    analogy_response = query.execute()
                    if analogy_response.data:
                        training_examples["analogy"] = analogy_response.data
                except Exception as e:
                    logger.warning(f"Failed to get analogy training examples: {e}")
            
            elif section == "synonym":
                try:
                    query = admin_client.table('ssat_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Synonyms')
                    if difficulty:
                        query = query.eq('difficulty', difficulty)
                    synonym_response = query.execute()
                    if synonym_response.data:
                        training_examples["synonym"] = synonym_response.data
                except Exception as e:
                    logger.warning(f"Failed to get synonym training examples: {e}")
            
            elif section == "reading":
                try:
                    reading_passages_response = admin_client.table('reading_passages').select('*').execute()
                    if reading_passages_response.data:
                        # For each passage, get its questions
                        for passage in reading_passages_response.data:
                            passage_id = passage['id']
                            query = admin_client.table('reading_questions').select('*').eq('passage_id', passage_id)
                            if difficulty:
                                query = query.eq('difficulty', difficulty)
                            questions_response = query.execute()
                            passage['questions'] = questions_response.data if questions_response.data else []
                        # Filter out passages that have no questions after difficulty filtering
                        training_examples["reading"] = [p for p in reading_passages_response.data if p.get('questions')]
                except Exception as e:
                    logger.warning(f"Failed to get reading training examples: {e}")
            
            elif section == "writing":
                try:
                    writing_response = admin_client.table('writing_prompts').select('*').execute()
                    if writing_response.data:
                        training_examples["writing"] = writing_response.data
                except Exception as e:
                    logger.warning(f"Failed to get writing training examples: {e}")
        else:
            # Fetch all sections
            logger.info("🔍 ADMIN: Fetching all training examples")
            
            # Get quantitative training questions
            try:
                query = admin_client.table('ssat_questions').select('*').eq('section', 'Quantitative')
                if difficulty:
                    query = query.eq('difficulty', difficulty)
                quantitative_response = query.execute()
                if quantitative_response.data:
                    training_examples["quantitative"] = quantitative_response.data
            except Exception as e:
                logger.warning(f"Failed to get quantitative training examples: {e}")
            
            # Get analogy training questions
            try:
                query = admin_client.table('ssat_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Analogies')
                if difficulty:
                    query = query.eq('difficulty', difficulty)
                analogy_response = query.execute()
                if analogy_response.data:
                    training_examples["analogy"] = analogy_response.data
            except Exception as e:
                logger.warning(f"Failed to get analogy training examples: {e}")
            
            # Get synonym training questions
            try:
                query = admin_client.table('ssat_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Synonyms')
                if difficulty:
                    query = query.eq('difficulty', difficulty)
                synonym_response = query.execute()
                if synonym_response.data:
                    training_examples["synonym"] = synonym_response.data
            except Exception as e:
                logger.warning(f"Failed to get synonym training examples: {e}")
            
            # Get reading training examples (passages with questions)
            try:
                reading_passages_response = admin_client.table('reading_passages').select('*').execute()
                if reading_passages_response.data:
                    # For each passage, get its questions
                    for passage in reading_passages_response.data:
                        passage_id = passage['id']
                        query = admin_client.table('reading_questions').select('*').eq('passage_id', passage_id)
                        if difficulty:
                            query = query.eq('difficulty', difficulty)
                        questions_response = query.execute()
                        passage['questions'] = questions_response.data if questions_response.data else []
                    # Filter out passages that have no questions after difficulty filtering
                    training_examples["reading"] = [p for p in reading_passages_response.data if p.get('questions')]
            except Exception as e:
                logger.warning(f"Failed to get reading training examples: {e}")
            
            # Get writing training prompts
            try:
                writing_response = admin_client.table('writing_prompts').select('*').execute()
                if writing_response.data:
                    training_examples["writing"] = writing_response.data
            except Exception as e:
                logger.warning(f"Failed to get writing training examples: {e}")
        
        # Calculate summary statistics
        summary = {
            "quantitative": len(training_examples["quantitative"]),
            "analogy": len(training_examples["analogy"]),
            "synonym": len(training_examples["synonym"]),
            "reading_passages": len(training_examples["reading"]),
            "reading_questions": sum(len(p.get('questions', [])) for p in training_examples["reading"]),
            "writing": len(training_examples["writing"])
        }
        
        logger.info(f"🔍 ADMIN: Retrieved training examples - {summary}")
        
        return {
            "success": True,
            "summary": summary,
            "training_examples": training_examples
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get training examples: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get training examples"
        )


@router.delete("/training-examples/{example_id}")
async def delete_training_example(
    example_id: str,
    request: dict,
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete a training example (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} deleting training example {example_id}")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get table name from request body
        table_name = request.get('table')
        if not table_name:
            raise HTTPException(status_code=400, detail='Table name is required')
        
        # Validate table name for security
        valid_tables = ['ssat_questions', 'reading_passages', 'writing_prompts']
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail=f'Invalid table name. Must be one of: {valid_tables}')
        
        # Delete the training example
        try:
            response = admin_client.table(table_name).delete().eq('id', example_id).execute()
            logger.info(f"🔍 ADMIN: Deleted training example {example_id} from {table_name}")
            
            return {
                "success": True,
                "message": f"Training example {example_id} deleted successfully from {table_name}"
            }
        except Exception as e:
            logger.error(f"Failed to delete training example {example_id} from {table_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete training example: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete training example: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete training example"
        )


@router.put("/training-examples/{example_id}")
async def update_training_example(
    example_id: str,
    request: dict,
    current_user: UserProfile = Depends(get_current_user)
):
    """Update a training example (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} updating training example {example_id}")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get table name and updates from request body
        table_name = request.get('table')
        updates = request.get('updates', {})
        
        if not table_name:
            raise HTTPException(status_code=400, detail='Table name is required')
        
        if not updates:
            raise HTTPException(status_code=400, detail='Updates are required')
        
        # Validate table name for security
        valid_tables = ['ssat_questions', 'reading_passages', 'writing_prompts']
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail=f'Invalid table name. Must be one of: {valid_tables}')
        
        # Update the training example
        try:
            response = admin_client.table(table_name).update(updates).eq('id', example_id).execute()
            logger.info(f"🔍 ADMIN: Updated training example {example_id} in {table_name}")
            
            return {
                "success": True,
                "message": f"Training example {example_id} updated successfully in {table_name}",
                "data": response.data[0] if response.data else None
            }
        except Exception as e:
            logger.error(f"Failed to update training example {example_id} in {table_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update training example: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update training example: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update training example"
        )


@router.get("/pool-questions")
async def get_pool_questions(
    section: str = None,
    difficulty: str = None,
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all pool questions grouped by section (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} requesting pool questions")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Initialize pool questions structure
        pool_questions = {
            "quantitative": [],
            "analogy": [],
            "synonym": [],
            "reading": [],
            "writing": []
        }
        
        # If specific section requested, only fetch that section
        if section:
            logger.info(f"🔍 ADMIN: Fetching specific section: {section}")
            
            if section == "quantitative":
                try:
                    query = admin_client.table('ai_generated_questions').select('*').eq('section', 'Quantitative')
                    if difficulty:
                        query = query.eq('difficulty', difficulty)
                    quantitative_response = query.execute()
                    if quantitative_response.data:
                        pool_questions["quantitative"] = quantitative_response.data
                except Exception as e:
                    logger.warning(f"Failed to get quantitative pool questions: {e}")
            
            elif section == "analogy":
                try:
                    query = admin_client.table('ai_generated_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Analogies')
                    if difficulty:
                        query = query.eq('difficulty', difficulty)
                    analogy_response = query.execute()
                    if analogy_response.data:
                        pool_questions["analogy"] = analogy_response.data
                except Exception as e:
                    logger.warning(f"Failed to get analogy pool questions: {e}")
            
            elif section == "synonym":
                try:
                    query = admin_client.table('ai_generated_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Synonyms')
                    if difficulty:
                        query = query.eq('difficulty', difficulty)
                    synonym_response = query.execute()
                    if synonym_response.data:
                        pool_questions["synonym"] = synonym_response.data
                except Exception as e:
                    logger.warning(f"Failed to get synonym pool questions: {e}")
            
            elif section == "reading":
                try:
                    reading_passages_response = admin_client.table('ai_generated_reading_passages').select('*').execute()
                    if reading_passages_response.data:
                        # For each passage, get its questions
                        for passage in reading_passages_response.data:
                            passage_id = passage['id']
                            query = admin_client.table('ai_generated_reading_questions').select('*').eq('passage_id', passage_id)
                            if difficulty:
                                query = query.eq('difficulty', difficulty)
                            questions_response = query.execute()
                            passage['questions'] = questions_response.data if questions_response.data else []
                        # Filter out passages that have no questions after difficulty filtering
                        pool_questions["reading"] = [p for p in reading_passages_response.data if p.get('questions')]
                except Exception as e:
                    logger.warning(f"Failed to get reading pool questions: {e}")
            
            elif section == "writing":
                try:
                    writing_response = admin_client.table('ai_generated_writing_prompts').select('*').execute()
                    if writing_response.data:
                        pool_questions["writing"] = writing_response.data
                except Exception as e:
                    logger.warning(f"Failed to get writing pool questions: {e}")
        else:
            # Fetch all sections
            logger.info("🔍 ADMIN: Fetching all pool questions")
            
            # Get quantitative pool questions
            try:
                query = admin_client.table('ai_generated_questions').select('*').eq('section', 'Quantitative')
                if difficulty:
                    query = query.eq('difficulty', difficulty)
                quantitative_response = query.execute()
                if quantitative_response.data:
                    pool_questions["quantitative"] = quantitative_response.data
            except Exception as e:
                logger.warning(f"Failed to get quantitative pool questions: {e}")
            
            # Get analogy pool questions
            try:
                query = admin_client.table('ai_generated_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Analogies')
                if difficulty:
                    query = query.eq('difficulty', difficulty)
                analogy_response = query.execute()
                if analogy_response.data:
                    pool_questions["analogy"] = analogy_response.data
            except Exception as e:
                logger.warning(f"Failed to get analogy pool questions: {e}")
            
            # Get synonym pool questions
            try:
                query = admin_client.table('ai_generated_questions').select('*').eq('section', 'Verbal').eq('subsection', 'Synonyms')
                if difficulty:
                    query = query.eq('difficulty', difficulty)
                synonym_response = query.execute()
                if synonym_response.data:
                    pool_questions["synonym"] = synonym_response.data
            except Exception as e:
                logger.warning(f"Failed to get synonym pool questions: {e}")
            
            # Get reading pool questions (passages with questions)
            try:
                reading_passages_response = admin_client.table('ai_generated_reading_passages').select('*').execute()
                if reading_passages_response.data:
                    # For each passage, get its questions
                    for passage in reading_passages_response.data:
                        passage_id = passage['id']
                        query = admin_client.table('ai_generated_reading_questions').select('*').eq('passage_id', passage_id)
                        if difficulty:
                            query = query.eq('difficulty', difficulty)
                        questions_response = query.execute()
                        passage['questions'] = questions_response.data if questions_response.data else []
                    # Filter out passages that have no questions after difficulty filtering
                    pool_questions["reading"] = [p for p in reading_passages_response.data if p.get('questions')]
            except Exception as e:
                logger.warning(f"Failed to get reading pool questions: {e}")
            
            # Get writing pool prompts
            try:
                writing_response = admin_client.table('ai_generated_writing_prompts').select('*').execute()
                if writing_response.data:
                    pool_questions["writing"] = writing_response.data
            except Exception as e:
                logger.warning(f"Failed to get writing pool questions: {e}")
        
        # Calculate summary statistics
        summary = {
            "quantitative": len(pool_questions["quantitative"]),
            "analogy": len(pool_questions["analogy"]),
            "synonym": len(pool_questions["synonym"]),
            "reading_passages": len(pool_questions["reading"]),
            "reading_questions": sum(len(p.get('questions', [])) for p in pool_questions["reading"]),
            "writing": len(pool_questions["writing"])
        }
        
        logger.info(f"🔍 ADMIN: Retrieved pool questions - {summary}")
        
        return {
            "success": True,
            "summary": summary,
            "pool_questions": pool_questions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pool questions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get pool questions"
        )


@router.delete("/pool-questions/{question_id}")
async def delete_pool_question(
    question_id: str,
    request: dict,
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete a pool question (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} deleting pool question {question_id}")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get table name from request body
        table_name = request.get('table')
        if not table_name:
            raise HTTPException(status_code=400, detail='Table name is required')
        
        # Validate table name for security
        valid_tables = ['ai_generated_questions', 'ai_generated_reading_passages', 'ai_generated_writing_prompts']
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail=f'Invalid table name. Must be one of: {valid_tables}')
        
        # Delete the pool question
        try:
            response = admin_client.table(table_name).delete().eq('id', question_id).execute()
            logger.info(f"🔍 ADMIN: Deleted pool question {question_id} from {table_name}")
            
            return {
                "success": True,
                "message": f"Pool question {question_id} deleted successfully from {table_name}"
            }
        except Exception as e:
            logger.error(f"Failed to delete pool question {question_id} from {table_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete pool question: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pool question: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete pool question"
        )


@router.put("/pool-questions/{question_id}")
async def update_pool_question(
    question_id: str,
    request: dict,
    current_user: UserProfile = Depends(get_current_user)
):
    """Update a pool question (admin only)."""
    try:
        check_admin_access(current_user)
        
        logger.info(f"🔍 ADMIN: Admin {current_user.id} updating pool question {question_id}")
        
        # Get admin database connection
        service_role_key = get_config().supabase_service_role_key
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        admin_client = create_client(get_config().supabase_url, service_role_key)
        
        # Get table name and updates from request body
        table_name = request.get('table')
        updates = request.get('updates', {})
        
        if not table_name:
            raise HTTPException(status_code=400, detail='Table name is required')
        
        if not updates:
            raise HTTPException(status_code=400, detail='Updates are required')
        
        # Validate table name for security
        valid_tables = ['ai_generated_questions', 'ai_generated_reading_passages', 'ai_generated_writing_prompts']
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail=f'Invalid table name. Must be one of: {valid_tables}')
        
        # Update the pool question
        try:
            response = admin_client.table(table_name).update(updates).eq('id', question_id).execute()
            logger.info(f"🔍 ADMIN: Updated pool question {question_id} in {table_name}")
            
            return {
                "success": True,
                "message": f"Pool question {question_id} updated successfully in {table_name}",
                "data": response.data[0] if response.data else None
            }
        except Exception as e:
            logger.error(f"Failed to update pool question {question_id} in {table_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update pool question: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pool question: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update pool question"
        )