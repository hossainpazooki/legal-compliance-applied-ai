# Rule Embedding Service

Vector embeddings for regulatory rules, enabling semantic similarity search across multiple dimensions.

## Overview

The embedding service generates 4 types of vector embeddings per rule, allowing multi-faceted similarity search:

```
Rule
 ├── Semantic Embedding    → Natural language meaning
 ├── Structural Embedding  → Decision logic structure
 ├── Entity Embedding      → Data fields and operators
 └── Legal Embedding       → Legal citations and sources
```

## Embedding Types

### 1. Semantic Embedding

**Source:** Rule name, description, and decision explanation.

```python
# Example source text
"Income Eligibility Check. Verify applicant meets minimum income requirements. Decision: eligible"
```

**Use case:** Find rules with similar meaning, even if they use different terminology.

### 2. Structural Embedding

**Source:** Serialized conditions and decision logic.

```python
# Example source text
"applicant.annual_income gte 50000 | applicant.age gte 18 | OUTCOME:eligible | CONFIDENCE:1.0"
```

**Use case:** Find rules with similar decision structures (e.g., same number of conditions, similar operators).

### 3. Entity Embedding

**Source:** Extracted field names and operators.

```python
# Example source text
"age annual applicant eligible gte income"
```

**Use case:** Find rules that operate on the same data fields, regardless of their logic.

### 4. Legal Embedding

**Source:** Legal citations and document references.

```python
# Example source text
"Consumer Credit Act Section 4.2 cca_2023"
```

**Use case:** Find all rules derived from the same legal source.

## Data Model

### RuleEmbedding Table

```sql
CREATE TABLE rule_embeddings (
    id INTEGER PRIMARY KEY,
    rule_id INTEGER REFERENCES embedding_rules(id),
    embedding_type VARCHAR(20),  -- semantic/structural/entity/legal
    vector_json TEXT,            -- JSON array of floats (SQLite)
    embedding_vector BLOB,       -- Serialized numpy array (PostgreSQL)
    vector_dim INTEGER,          -- Default: 384
    model_name VARCHAR(100),     -- e.g., "all-MiniLM-L6-v2"
    source_text TEXT,            -- Text used to generate embedding
    created_at TIMESTAMP
);
```

### Storage Options

| Database | Storage Method | Performance |
|----------|----------------|-------------|
| SQLite | `vector_json` (JSON arrays) | Good for dev/small datasets |
| PostgreSQL | `embedding_vector` (bytes) or pgvector | Production-ready, ANN search |

The model supports both formats with helper methods:

```python
# Get vector as numpy array (prefers bytes, falls back to JSON)
embedding = rule_embedding.get_vector_as_numpy()  # -> np.ndarray

# Set vector from numpy array (stores in both formats)
rule_embedding.set_vector_from_numpy(my_vector)
```

To upgrade to pgvector:
```python
from pgvector.sqlalchemy import Vector

vector: list[float] = Field(sa_column=Column(Vector(384)))
```

## API Usage

### Creating Rules with Embeddings

```python
from backend.rule_embedding_service.app.services import (
    EmbeddingRuleService, RuleCreate
)

rule_data = RuleCreate(
    rule_id="income_check_001",
    name="Income Eligibility Check",
    description="Verify applicant meets minimum income requirements",
    conditions=[
        {"field": "applicant.annual_income", "operator": "gte", "value": "50000"},
        {"field": "applicant.age", "operator": "gte", "value": "18"},
    ],
    decision={"outcome": "eligible", "confidence": 1.0},
    legal_sources=[{"citation": "Consumer Credit Act Section 4.2", "document_id": "cca_2023"}],
    generate_embeddings=True,  # Auto-generate all 4 embedding types
)

service = EmbeddingRuleService(session)
rule = service.create_rule(rule_data)
```

### Similarity Search

```python
# Search across all embedding types
results = service.search_similar(
    query="income requirements for loan eligibility",
    limit=10,
    min_score=0.5,
)

# Search only semantic embeddings
results = service.search_similar(
    query="income requirements",
    embedding_types=["semantic"],
    limit=5,
)

# Search by legal citation
results = service.search_similar(
    query="Consumer Credit Act",
    embedding_types=["legal"],
)
```

### Response Format

```python
[
    {
        "rule_id": "income_check_001",
        "rule_name": "Income Eligibility Check",
        "score": 0.87,  # Cosine similarity (0-1)
        "embedding_type": "semantic",
        "matched_text": "Income Eligibility Check. Verify applicant...",
    },
    ...
]
```

### Regenerating Embeddings

```python
# Regenerate after model update
service.regenerate_embeddings("income_check_001")

# Or via update with flag
service.update_rule(
    "income_check_001",
    RuleUpdate(regenerate_embeddings=True)
)
```

## Embedding Generation

### ML Mode (Default)

Uses `sentence-transformers` with `all-MiniLM-L6-v2`:
- 384-dimensional dense vectors
- Trained on 1B+ sentence pairs
- ~22M parameters, fast inference

```python
from backend.rule_embedding_service.app.services import ml_available

if ml_available():
    print("Using ML embeddings")
```

### Fallback Mode

When `sentence-transformers` is unavailable:
- Deterministic hash-based vectors
- Maintains API compatibility
- Not suitable for semantic similarity (only exact matching)

```python
generator = EmbeddingGenerator(use_ml=False)  # Force fallback
```

### Direct Numpy API

For direct numpy array access (useful for custom similarity calculations):

```python
from backend.rule_embedding_service.app.services import EmbeddingGenerator

generator = EmbeddingGenerator()

# Generate semantic embedding from text
vector = generator.generate_semantic_embedding("income eligibility")
# -> np.ndarray of shape (384,)

# Generate structural embedding from rule
structural_vec = generator.generate_structural_embedding(rule)
# -> np.ndarray of shape (384,)

# Serialize rule structure to text
structure_text = generator.serialize_rule_structure(rule)
# -> "applicant.income gte 50000 | OUTCOME:eligible | CONFIDENCE:1.0"

# Extract entity names from rule
entities = generator.extract_entities(rule)
# -> ["applicant", "eligible", "gte", "income"]
```

## Performance Considerations

### SQLite (Development)

- Linear scan for similarity search
- Suitable for < 10,000 rules
- No index required

### PostgreSQL + pgvector (Production)

```sql
-- Create HNSW index for fast ANN search
CREATE INDEX ON rule_embeddings
USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query with index
SELECT rule_id, 1 - (vector <=> query_vector) AS similarity
FROM rule_embeddings
WHERE embedding_type = 'semantic'
ORDER BY vector <=> query_vector
LIMIT 10;
```

## Integration Points

### With Consistency Engine

Use embeddings to find potentially inconsistent rules:

```python
# Find rules with similar structure but different outcomes
structural_similar = service.search_similar(
    query=rule_structural_text,
    embedding_types=["structural"],
)

for result in structural_similar:
    if result["rule_id"] != current_rule.rule_id:
        # Check for decision conflicts
        pass
```

### With RAG Service

Combine embedding search with BM25 for hybrid retrieval:

```python
# Semantic search
embedding_results = embedding_service.search_similar(query)

# Keyword search
bm25_results = rag_service.search(query)

# Merge and rerank
combined = hybrid_merge(embedding_results, bm25_results)
```

## Configuration

Environment variables:

```bash
# Enable/disable ML embeddings
ENABLE_ML_EMBEDDINGS=true

# Model selection (if using ML)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Vector dimension (must match model)
EMBEDDING_DIM=384
```
