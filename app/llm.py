import os
import hashlib
import logging
import chromadb
from openai import OpenAI
from app.config import Config
from app.prompt_builder import build_sql_generation_prompt
from app.utils import strip_markdown_fences

logger = logging.getLogger(__name__)
CHROMA_CACHE_DIR = "data/chroma_cache"


def get_chroma_collection():
    """Lazily initialize persistent ChromaDB client and retrieve cache collection."""
    # Ensure cache directory exists
    os.makedirs(CHROMA_CACHE_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_CACHE_DIR)
    return client.get_or_create_collection(
        name="sql_queries",
        metadata={"hnsw:space": "cosine"}
    )


def get_openai_embedding(text: str, client: OpenAI) -> list[float]:
    """Generate text embeddings using OpenAI API."""
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def generate_sql(user_question: str) -> str:
    """Generate SQL from natural language query with semantic caching using ChromaDB."""
    if not Config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Please add it to your .env file.")

    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    # Clean the input query
    clean_question = user_question.strip()
    question_hash = hashlib.sha256(clean_question.lower().encode("utf-8")).hexdigest()
    
    # generate an embedding so we can check the semantic cache first
    logger.info("Generating embedding for user question...")
    try:
        query_embedding = get_openai_embedding(clean_question, client)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # Fallback to direct LLM execution if embeddings fail
        query_embedding = None

    # check the cache before hitting the API
    if query_embedding is not None:
        try:
            collection = get_chroma_collection()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=1
            )
            
            # Check if there is a match and if the cosine distance is within the 90% similarity threshold
            # Cosine distance = 1 - cosine_similarity. Similarity > 90% (0.90) => distance < 0.10
            if results and results["distances"] and results["distances"][0]:
                distance = results["distances"][0][0]
                similarity = 1.0 - distance
                logger.info(f"Nearest semantic cache match distance: {distance:.4f} (Similarity: {similarity * 100:.2f}%)")
                
                if distance < 0.10:
                    cached_sql = results["metadatas"][0][0]["sql"]
                    logger.info("Semantic cache HIT! Serving cached SQL statement.")
                    return cached_sql
                    
        except Exception as e:
            logger.warning(f"Semantic cache lookup failed: {e}")

    # cache miss - go to OpenAI
    logger.info("Semantic cache MISS. Querying OpenAI GPT model...")
    prompt = build_sql_generation_prompt(clean_question)

    response = client.chat.completions.create(
        model=Config.MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a precise PostgreSQL analytics SQL generator.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    sql = strip_markdown_fences(content).strip()
    
    # only cache it if it passes validation
    if query_embedding is not None:
        from app.validator import validate_sql  # Lazy import to prevent circular references
        
        is_valid, _ = validate_sql(sql)
        if is_valid:
            try:
                collection = get_chroma_collection()
                collection.upsert(
                    documents=[clean_question],
                    embeddings=[query_embedding],
                    metadatas=[{"sql": sql}],
                    ids=[question_hash]
                )
                logger.info("Successfully cached new verified query-SQL pair.")
            except Exception as e:
                logger.warning(f"Failed to cache generated SQL: {e}")
        else:
            logger.warning("Generated SQL failed safety validation; bypassing cache write.")

    return sql
