# Production RAG Deployment Guide

Moving from local development to production involves several architectural changes for scale, reliability, and performance.

## Production Architecture

```
┌─────────────────┐
│   Load Balancer │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Django │──────┐
    │  App    │      │
    └─────────┘      │
                     │
         ┌───────────┴──────────┐
         │                      │
    ┌────▼─────┐         ┌──────▼──────┐
    │ Vector DB │         │  LLM API    │
    │ (Managed) │         │  (Claude)   │
    └───────────┘         └─────────────┘
```

## Option 1: Cloud Vector Database

### Pinecone (Recommended for ease)

```python
# production_rag_service.py
import pinecone
from sentence_transformers import SentenceTransformer

class ProductionRAGService:
    def __init__(self):
        # Initialize Pinecone
        pinecone.init(
            api_key="your-api-key",
            environment="us-west1-gcp"
        )
        
        # Create/connect to index
        if "tickets" not in pinecone.list_indexes():
            pinecone.create_index(
                "tickets",
                dimension=384,
                metric="cosine"
            )
        
        self.index = pinecone.Index("tickets")
        
        # Keep local embeddings (fast & cheap)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_ticket(self, ticket_data):
        ticket_id = str(ticket_data['id'])
        text = self.format_ticket_for_embedding(ticket_data)
        
        # Generate embedding locally
        embedding = self.embedding_model.encode(text).tolist()
        
        # Upload to Pinecone
        self.index.upsert(vectors=[
            {
                'id': ticket_id,
                'values': embedding,
                'metadata': {
                    'ticket_id': ticket_id,
                    'title': ticket_data['title'],
                    'status': ticket_data['status'],
                    'priority': ticket_data['priority'],
                }
            }
        ])
    
    def search_tickets(self, query, n_results=5):
        # Generate query embedding locally
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Search in Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True
        )
        
        return results['matches']
```

**Pricing**: ~$70/month for 100k tickets (1 pod)

### Qdrant Cloud

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantRAGService:
    def __init__(self):
        self.client = QdrantClient(
            url="https://your-cluster.qdrant.io",
            api_key="your-api-key"
        )
        
        # Create collection if not exists
        try:
            self.client.get_collection("tickets")
        except:
            self.client.create_collection(
                collection_name="tickets",
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_ticket(self, ticket_data):
        text = self.format_ticket_for_embedding(ticket_data)
        embedding = self.embedding_model.encode(text).tolist()
        
        self.client.upsert(
            collection_name="tickets",
            points=[
                PointStruct(
                    id=ticket_data['id'],
                    vector=embedding,
                    payload={
                        'title': ticket_data['title'],
                        'status': ticket_data['status'],
                        # ... other metadata
                    }
                )
            ]
        )
```

**Pricing**: Free tier available, ~$25/month for small workloads

### Weaviate Cloud

```python
import weaviate

class WeaviateRAGService:
    def __init__(self):
        self.client = weaviate.Client(
            url="https://your-cluster.weaviate.network",
            auth_client_secret=weaviate.AuthApiKey("your-api-key")
        )
        
        # Create schema
        schema = {
            "class": "Ticket",
            "vectorizer": "none",  # We provide vectors
            "properties": [
                {"name": "title", "dataType": ["text"]},
                {"name": "status", "dataType": ["text"]},
                {"name": "priority", "dataType": ["text"]},
            ]
        }
        
        try:
            self.client.schema.create_class(schema)
        except:
            pass
    
    def add_ticket(self, ticket_data):
        text = self.format_ticket_for_embedding(ticket_data)
        embedding = self.embedding_model.encode(text).tolist()
        
        self.client.data_object.create(
            data_object={
                "title": ticket_data['title'],
                "status": ticket_data['status'],
                # ... other fields
            },
            class_name="Ticket",
            vector=embedding
        )
```

**Pricing**: Free tier available, ~$25/month minimum

## Option 2: API-Based Embeddings

If you want to avoid running embedding models, use API services:

### OpenAI Embeddings

```python
import openai

class OpenAIEmbeddingService:
    def __init__(self):
        openai.api_key = "your-api-key"
        self.model = "text-embedding-3-small"  # 1536 dimensions
    
    def get_embedding(self, text):
        response = openai.Embedding.create(
            input=text,
            model=self.model
        )
        return response['data'][0]['embedding']
```

**Pricing**: $0.02 per 1M tokens (~$0.50 for 10k tickets)

### Cohere Embeddings

```python
import cohere

class CohereEmbeddingService:
    def __init__(self):
        self.co = cohere.Client("your-api-key")
    
    def get_embedding(self, text):
        response = self.co.embed(
            texts=[text],
            model="embed-english-v3.0"
        )
        return response.embeddings[0]
```

**Pricing**: Free tier available, $0.10 per 1M tokens

## Option 3: Production LLM Service

### Using Claude API (Recommended)

```python
import anthropic

class ClaudeGenerationService:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key="your-api-key"
        )
    
    def generate_answer(self, query, context_tickets):
        context = self._build_context(context_tickets)
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Based on these tickets:

{context}

Question: {query}

Provide a concise answer based only on the ticket information above."""
            }]
        )
        
        return message.content[0].text
    
    def _build_context(self, tickets):
        context_parts = []
        for ticket in tickets:
            context_parts.append(
                f"Ticket #{ticket['metadata']['ticket_id']}: "
                f"{ticket['metadata']['title']}\n"
                f"Status: {ticket['metadata']['status']}\n"
                f"Priority: {ticket['metadata']['priority']}\n"
            )
        return "\n".join(context_parts)
```

**Pricing**: 
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- Typical query: ~$0.01

### Using OpenAI GPT-4

```python
import openai

class GPT4GenerationService:
    def __init__(self):
        openai.api_key = "your-api-key"
    
    def generate_answer(self, query, context_tickets):
        context = self._build_context(context_tickets)
        
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You answer questions based on ticket information."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content
```

## Complete Production Architecture

```python
# production_config.py
import os
from typing import Optional

class ProductionConfig:
    # Vector Database
    VECTOR_DB = os.getenv('VECTOR_DB', 'pinecone')  # pinecone, qdrant, weaviate
    
    # Embeddings
    EMBEDDING_TYPE = os.getenv('EMBEDDING_TYPE', 'local')  # local, openai, cohere
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    
    # LLM
    LLM_TYPE = os.getenv('LLM_TYPE', 'claude')  # claude, openai, local
    LLM_MODEL = os.getenv('LLM_MODEL', 'claude-sonnet-4-20250514')
    
    # API Keys
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Caching
    REDIS_URL = os.getenv('REDIS_URL')
    CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))


# production_rag.py
from functools import lru_cache
import hashlib
import redis

class ProductionRAGSystem:
    def __init__(self, config: ProductionConfig):
        self.config = config
        
        # Initialize components based on config
        self.vector_db = self._init_vector_db()
        self.embedding_service = self._init_embedding_service()
        self.llm_service = self._init_llm_service()
        
        # Initialize Redis cache
        if config.REDIS_URL:
            self.cache = redis.from_url(config.REDIS_URL)
        else:
            self.cache = None
    
    def search_with_cache(self, query: str, n_results: int = 5):
        """Search with Redis caching"""
        if not self.cache:
            return self._search_no_cache(query, n_results)
        
        # Create cache key
        cache_key = f"rag:search:{hashlib.md5(query.encode()).hexdigest()}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Search
        results = self._search_no_cache(query, n_results)
        
        # Cache results
        self.cache.setex(
            cache_key,
            self.config.CACHE_TTL,
            json.dumps(results)
        )
        
        return results
    
    def _search_no_cache(self, query, n_results):
        # Generate embedding
        embedding = self.embedding_service.get_embedding(query)
        
        # Search vector DB
        results = self.vector_db.search(embedding, n_results)
        
        return results
    
    def generate_answer_with_cache(self, query: str, results):
        """Generate answer with caching"""
        if not self.cache:
            return self.llm_service.generate_answer(query, results)
        
        # Create cache key from query + result IDs
        result_ids = [r['id'] for r in results]
        cache_content = f"{query}:{','.join(map(str, result_ids))}"
        cache_key = f"rag:answer:{hashlib.md5(cache_content.encode()).hexdigest()}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached.decode('utf-8')
        
        # Generate
        answer = self.llm_service.generate_answer(query, results)
        
        # Cache answer
        self.cache.setex(cache_key, self.config.CACHE_TTL, answer)
        
        return answer
```

## Performance Optimization

### 1. Batch Processing

```python
class BatchRAGProcessor:
    def __init__(self, batch_size=100):
        self.batch_size = batch_size
        self.batch = []
    
    def add_ticket(self, ticket_data):
        self.batch.append(ticket_data)
        
        if len(self.batch) >= self.batch_size:
            self.flush()
    
    def flush(self):
        if not self.batch:
            return
        
        # Process batch
        texts = [self.format_ticket(t) for t in self.batch]
        embeddings = self.embedding_service.batch_encode(texts)
        
        # Bulk insert to vector DB
        self.vector_db.bulk_insert(
            ids=[t['id'] for t in self.batch],
            embeddings=embeddings,
            metadata=[self.get_metadata(t) for t in self.batch]
        )
        
        self.batch = []
```

### 2. Async Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncRAGService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def search_tickets_async(self, query):
        loop = asyncio.get_event_loop()
        
        # Run embedding generation in thread pool
        embedding = await loop.run_in_executor(
            self.executor,
            self.embedding_service.get_embedding,
            query
        )
        
        # Run vector search in thread pool
        results = await loop.run_in_executor(
            self.executor,
            self.vector_db.search,
            embedding
        )
        
        return results
```

### 3. Query Result Caching

```python
from django.core.cache import cache
from django.utils.encoding import force_bytes
import hashlib

def cached_search(query, n_results=5, ttl=3600):
    # Create cache key
    cache_key = f"rag_search_{hashlib.md5(force_bytes(query)).hexdigest()}"
    
    # Try cache
    results = cache.get(cache_key)
    if results:
        return results
    
    # Execute search
    results = rag_service.search_tickets(query, n_results)
    
    # Cache results
    cache.set(cache_key, results, ttl)
    
    return results
```

## Security Considerations

### 1. API Key Management

```python
# Use environment variables
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

# Never commit .env file to git
# Add to .gitignore:
# .env
# *.key
```

### 2. Rate Limiting

```python
from django.core.cache import cache
from django.http import JsonResponse

def rate_limit(max_requests=10, window=60):
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            user_id = request.user.id
            key = f"rate_limit:{user_id}"
            
            count = cache.get(key, 0)
            if count >= max_requests:
                return JsonResponse(
                    {'error': 'Rate limit exceeded'},
                    status=429
                )
            
            cache.set(key, count + 1, window)
            return view_func(request, *args, **kwargs)
        
        return wrapped
    return decorator
```

### 3. Input Sanitization

```python
def sanitize_query(query: str) -> str:
    # Limit length
    query = query[:500]
    
    # Remove potentially harmful content
    query = query.strip()
    
    # Basic validation
    if not query or len(query) < 3:
        raise ValueError("Query too short")
    
    return query
```

## Monitoring & Logging

```python
import logging
from prometheus_client import Counter, Histogram

# Metrics
search_counter = Counter('rag_searches_total', 'Total RAG searches')
search_duration = Histogram('rag_search_duration_seconds', 'RAG search duration')
llm_calls = Counter('llm_calls_total', 'Total LLM API calls')

class MonitoredRAGService:
    def search_tickets(self, query):
        search_counter.inc()
        
        with search_duration.time():
            results = self._search(query)
        
        logging.info(f"Search completed: {len(results)} results for query: {query[:50]}")
        
        return results
    
    def generate_answer(self, query, context):
        llm_calls.inc()
        
        try:
            answer = self.llm_service.generate(query, context)
            logging.info(f"Answer generated successfully")
            return answer
        except Exception as e:
            logging.error(f"LLM generation failed: {e}")
            raise
```

## Cost Optimization

### Recommended Production Setup

**For Small-Medium Scale (< 50k tickets)**:
- Embeddings: Local (sentence-transformers) - **$0/month**
- Vector DB: Qdrant Cloud free tier - **$0/month**
- LLM: Claude Sonnet with caching - **~$10-50/month**

**For Large Scale (> 50k tickets)**:
- Embeddings: Local (run on GPU) - **$0/month**
- Vector DB: Pinecone - **$70/month**
- LLM: Claude Sonnet - **~$50-200/month**
- Caching: Redis - **$15/month**

**Total Monthly Cost**: ~$85-285/month for production

## Deployment Checklist

- [ ] Set up cloud vector database
- [ ] Configure API keys in environment
- [ ] Enable Redis caching
- [ ] Set up monitoring/logging
- [ ] Configure rate limiting
- [ ] Test with production data
- [ ] Set up backup/restore procedures
- [ ] Document disaster recovery plan
- [ ] Configure auto-scaling (if needed)
- [ ] Set up alerts for errors/latency

## Further Reading

- [Pinecone Documentation](https://docs.pinecone.io)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Anthropic API Documentation](https://docs.anthropic.com)
- [ChromaDB Production Deployment](https://docs.trychroma.com/deployment)
