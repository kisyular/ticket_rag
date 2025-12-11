# Ticket RAG System Architecture

## Local Development Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                        Django Application                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Ticket     │      │   RAG        │      │   LLM        │  │
│  │   Model      │──────│   Service    │──────│   Service    │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                      │                      │          │
│         │                      │                      │          │
│    ┌────▼────┐          ┌─────▼─────┐         ┌──────▼──────┐  │
│    │ Django  │          │ Sentence  │         │   Ollama    │  │
│    │ Signals │          │Transformer│         │  (Optional) │  │
│    └─────────┘          │  (Local)  │         │   (Local)   │  │
│                         └───────────┘         └─────────────┘  │
│                                │                                │
│                         ┌──────▼──────┐                        │
│                         │   ChromaDB  │                        │
│                         │   (Local)   │                        │
│                         └─────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## How It Works - Step by Step

### 1. Ticket Created/Updated
```
User creates ticket → Django saves to DB → Signal triggered → RAG service notified
```

### 2. Embedding Generation
```
Ticket data → Format as text → Sentence Transformer → 384-dim vector
                                      (Local, fast)
```

### 3. Vector Storage
```
Vector + Metadata → ChromaDB → Stored on disk
                    (./chroma_db/)
```

### 4. User Search Query
```
User types: "show me email issues" → Sentence Transformer → Query vector
```

### 5. Similarity Search
```
Query vector → ChromaDB → Find similar vectors → Return top N tickets
              (Cosine similarity, <100ms)
```

### 6. LLM Generation (Optional)
```
Retrieved tickets + Query → Ollama/Mock → Natural language answer
                           (Local or Mock)
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. INDEXING FLOW (Happens on ticket create/update)               │
└──────────────────────────────────────────────────────────────────┘

Ticket Object
    ↓
Format to Text
    "Ticket #123: Login page not loading
     Status: open
     Priority: high
     Description: Users report blank screen..."
    ↓
Sentence Transformer (all-MiniLM-L6-v2)
    [0.234, -0.567, 0.123, ..., 0.456]  (384 numbers)
    ↓
ChromaDB Storage
    {
      id: "123",
      vector: [...],
      metadata: {title, status, priority, ...}
    }


┌──────────────────────────────────────────────────────────────────┐
│ 2. SEARCH FLOW (Happens on user query)                           │
└──────────────────────────────────────────────────────────────────┘

User Query: "show me login problems"
    ↓
Sentence Transformer
    [0.245, -0.543, 0.134, ..., 0.432]
    ↓
ChromaDB Similarity Search
    Compare query vector with all ticket vectors
    ↓
    Find closest matches (cosine similarity)
    ↓
Retrieve Top 5 Results
    [
      {ticket_id: 123, relevance: 0.89, metadata: {...}},
      {ticket_id: 456, relevance: 0.76, metadata: {...}},
      ...
    ]
    ↓
(Optional) LLM Generation
    Context: Retrieved tickets
    Prompt: "Answer based on these tickets..."
    ↓
    Natural language answer
    ↓
Return to User
```

## Component Breakdown

### Sentence Transformers (Local)
- **Purpose**: Convert text to vectors
- **Model**: all-MiniLM-L6-v2 (80MB)
- **Speed**: 100-500 tickets/second
- **Runs on**: CPU or GPU (faster)
- **Cost**: FREE

### ChromaDB (Local)
- **Purpose**: Store and search vectors
- **Storage**: Disk (./chroma_db/)
- **Speed**: <100ms for 10k tickets
- **Scalability**: Up to 100k tickets locally
- **Cost**: FREE

### Ollama (Optional, Local)
- **Purpose**: Generate natural language answers
- **Models**: llama2, mistral, etc.
- **Speed**: 2-10 seconds per answer
- **Runs on**: CPU or GPU (much faster)
- **Cost**: FREE

## Performance Characteristics

### Indexing
```
Small dataset (< 1k tickets):    < 30 seconds
Medium dataset (1k-10k tickets): 1-5 minutes
Large dataset (10k-100k):        5-30 minutes
```

### Search
```
Query processing:       < 50ms
Vector search:          < 100ms
LLM generation:         2-10 seconds
Total (with LLM):       2-10 seconds
Total (without LLM):    < 200ms
```

### Storage
```
Per ticket:         ~2KB
1,000 tickets:      ~2MB
10,000 tickets:     ~20MB
100,000 tickets:    ~200MB
```

## Production Architecture (for reference)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Production Setup                            │
└─────────────────────────────────────────────────────────────────┘

Django App (Multiple instances)
    ↓
Load Balancer
    ↓
┌────────────────────┬─────────────────────┐
│                    │                     │
Sentence Transformer │   Claude API        │   Pinecone/Qdrant
(Still local!)       │   (Cloud)           │   (Cloud)
                     │                     │
                     └─────────────────────┘
                             │
                      Natural language
                         answers
```

## Key Decisions Made

### Local Embeddings
- **Why**: Fast, free, no API calls
- **Trade-off**: Need to run on your servers

### ChromaDB for Development
- **Why**: Simple, no setup, persistent
- **Trade-off**: Not ideal for huge scale (100k+ tickets)

### Optional LLM
- **Why**: System works fine with just search
- **Trade-off**: Better UX with LLM, but slower

### Automatic Sync via Signals
- **Why**: Always up-to-date, no manual work
- **Trade-off**: Slight performance hit on ticket saves

## Scaling Considerations

### When to upgrade components:

**Embeddings** (keep local even in production):
- Local is fast and free
- Only upgrade if you need specialized embeddings

**Vector DB** (upgrade at ~50k tickets):
- ChromaDB local → Pinecone/Qdrant Cloud
- Reason: Better performance at scale

**LLM** (upgrade based on usage):
- Mock → Ollama (free) → Claude API (paid)
- Reason: Quality and speed
