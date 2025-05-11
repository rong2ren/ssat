create table ssat_questions (
    id bigint primary key generated always as identity,
    raw_text text,
    metadata jsonb,
    embedding vector(384),
    source_pdf text
)