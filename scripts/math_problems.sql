create table math_problems (
    id uuid primary key default gen_random_uuid(),

    source text,                -- e.g., "SSAT", "AMC8", "Math Kangaroo"
    year int,                             -- e.g., 2025
    level text,                           -- e.g., "Elementary", "Middle", "High"
    difficulty int,                       -- e.g., 1–5 scale

    question_text text,          -- full question text in any language
    solution_text text,                   -- full solution text in any language

    image_urls text[] default '{}',       -- array of image URLs
    image_descriptions text[] default '{}', -- array of image descriptions

    tags text[] default '{}',             -- categories, e.g., ["geometry", "algebra"]

    created_at timestamp with time zone default now()
);