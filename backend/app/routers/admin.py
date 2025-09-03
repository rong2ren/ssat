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
        
        # Generate content using the service with admin privileges (force LLM generation)
        result = await get_content_service().generate_individual_content(request, force_llm_generation=True)
        
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
        
        # Use content service for admin complete test generation with force LLM generation
        result = await get_content_service().generate_complete_test_async(request, str(current_user.id), force_llm_generation=True)
        
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