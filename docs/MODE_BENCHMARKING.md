# Research Mode Benchmarking Guide

**Geo-RAG Platform v0.1.0-MVP**

Detailed explanation of the three analysis modes designed for systematic performance and quality evaluation.

---

## Overview

The Geo-RAG system includes **three distinct analysis modes** for research purposes:

1. **LLM-Only**: Baseline without retrieval
2. **RAG Baseline**: Simple semantic search
3. **RAG Advanced**: Hybrid search + GIS enrichment

These modes enable **controlled comparison** of how different information sources affect answer quality.

---

## Mode 1: LLM-Only (No Retrieval)

### Purpose

Establish a **baseline** for what the LLM can infer from satellite imagery alone, without external knowledge.

### Research Question

> "How well does the LLM reason about urban patterns using only extracted visual features?"

### Pipeline

```
Image
  ↓
[Vision] Extract 6 features
  ↓
[Format] Create prompt with features + question
  ↓
[LLM] Generate answer WITHOUT knowledge base
  ↓
Answer (no external grounding)
```

### Input to LLM

```
You are an urban planning analyst specializing in satellite imagery interpretation.

Analyze the following features extracted from a satellite image and answer the question.
Base your analysis ONLY on the provided image features. Do not speculate beyond what the features indicate.

=== IMAGE FEATURES ===
- Vegetation Density: low, approximately 5% coverage
- Building Density: high, tightly packed structures
- Road Network: moderate, mix of paved and unpaved
- Urban Pattern: irregular, informal layout
- Expansion Signs: active construction, new structures emerging
- Illegal Settlement Indicators: makeshift structures, no grid layout

=== QUESTION ===
Is there evidence of uncontrolled urban expansion or informal settlement?

Provide a clear, evidence-based answer. Reference specific features from the analysis above. Structure your response with:
1. Direct answer to the question
2. Supporting evidence from the features
3. Any limitations of the analysis
```

### Sample Response

```
Direct Answer:
Yes, there is strong evidence of uncontrolled urban expansion and informal settlement characteristics.

Supporting Evidence:
The satellite analysis reveals multiple indicators:
1. Irregular, informal urban layout with no discernible grid pattern
2. High building density with tightly packed structures
3. Active expansion signs with visible new construction
4. Makeshift structure indicators suggesting informal development
5. Low vegetation coverage (5%) indicating dense building footprint

Limitations:
The visual analysis cannot determine:
- Legal status (formal vs. informal ownership)
- Infrastructure quality or service provision
- Temporal development (when expansion occurred)
- Socioeconomic conditions
- Actual population density or building heights
```

### Evaluation Metrics

- **Accuracy**: Does answer match visual features?
- **Completeness**: Does answer address all relevant features?
- **Specificity**: Does answer cite features by name?
- **Limitations**: Does answer acknowledge what vision alone cannot determine?

### Benchmark Against

Compare LLM-Only to RAG modes to quantify knowledge base contribution:

```
Improvement = (RAG_Quality - LLM_Only_Quality) / LLM_Only_Quality × 100%
```

---

## Mode 2: RAG Baseline (Semantic Search Only)

### Purpose

Evaluate **simple semantic retrieval** independently, without keyword search or complex ranking.

### Research Question

> "Does semantic search of domain knowledge improve answer quality?"
> "What types of questions benefit most from semantic retrieval?"

### Pipeline

```
Image
  ↓
[Vision] Extract 6 features
  ↓
[Query Builder] Create retrieval query:
  - Original question
  - + Relevant features (filtered by topic keywords)
  ↓
[Semantic Search] ChromaDB cosine similarity
  - Top-5 chunks by embedding similarity
  - No keyword scoring, no ranking merge
  ↓
[Format] Create prompt with features + chunks + question
  ↓
[LLM] Generate answer GROUNDED IN KNOWLEDGE
  ↓
Answer (semantically relevant context)
```

### Retrieval Query Example

**Question**: "Is there evidence of illegal settlement?"

**Query Builder Logic**:
1. Detect "illegal" keyword in question
2. Map to relevant features: `illegal_settlement_indicators`, `urban_pattern`, `road_density`
3. Extract feature values from vision output
4. Build query: `"Is there evidence of illegal settlement? illegal settlement indicators: makeshift structures, no grid layout urban pattern: irregular, informal layout road density: moderate, unpaved"`

**ChromaDB Search**:
- Encode query using all-MiniLM-L6-v2
- Find top-5 closest chunks by cosine similarity
- Return chunks with semantic scores

### Input to LLM

```
You are an urban planning analyst with access to domain knowledge.
You analyze satellite imagery features and use retrieved knowledge to provide well-grounded answers.

=== IMAGE FEATURES ===
[6 vision features]

=== RELEVANT KNOWLEDGE ===
[1] (source: settlement_patterns.txt, relevance: 0.91)
Informal settlements often develop on marginal land without proper planning or infrastructure...

[2] (source: urban_planning.txt, relevance: 0.87)
Satellite imagery can identify settlement patterns through spectral analysis and texture...

[3] (source: settlement_patterns.txt, relevance: 0.84)
Unplanned urban development typically exhibits irregular spatial patterns...

=== QUESTION ===
Is there evidence of illegal settlement?

Provide a clear, evidence-based answer that:
1. References specific features from the image analysis
2. Grounds your reasoning in the retrieved knowledge (cite sources by number, e.g., [1])
3. Clearly distinguishes between what you observe and what the knowledge base says
4. Notes any contradictions between observed features and retrieved knowledge
```

### Sample Response

```
Direct Answer:
Yes, there is credible evidence of informal/illegal settlement based on visual analysis and domain knowledge.

Evidence Integration:
Image features indicate irregular urban layout [1], makeshift structures, and no grid street pattern,
which according to retrieved knowledge [3] are hallmarks of unplanned urban development. The high
building density combined with informal settlement indicators suggests this could be an informal
settlement area.

Observation vs. Knowledge Distinction:
OBSERVED: Irregular layout, makeshift structures, minimal vegetation
KNOWLEDGE [1]: This pattern matches known characteristics of informal settlements

Knowledge Gaps:
The retrieved knowledge [2] mentions spectral satellite analysis methods but doesn't provide
definitive thresholds for determining legality. Visual patterns alone cannot conclusively
determine legal status—this would require administrative records.
```

### Evaluation Metrics

- **Grounding**: Does LLM cite retrieved chunks?
- **Relevance**: Do retrieved chunks answer the question?
- **Integration**: Does LLM blend visual + knowledge?
- **Precision**: Does LLM distinguish between observed vs. knowledge?

### Note on Retrieval Quality

If semantic search returns irrelevant chunks, the LLM may:
- Ignore them (if too different from question)
- Hallucinate connections (if somewhat similar)
- Dilute focus (noise in context)

This is the **retrieval quality bottleneck** to optimize in research.

---

## Mode 3: RAG Advanced (Hybrid + GIS)

### Purpose

Evaluate **full information utilization**: hybrid retrieval + rule-based GIS enrichment for best-case answer quality.

### Research Question

> "Does hybrid retrieval (semantic + keyword) outperform semantic-only?"
> "Does GIS enrichment provide actionable metrics for problem-solving?"

### Pipeline

```
Image
  ↓
[Vision] Extract 6 features
  ↓
[Query Builder] Create retrieval query (same as baseline)
  ↓
[Semantic Search] Top-5 by embedding similarity
  ↓
[Keyword Search] Top-3 by BM25 scoring
  ↓
[Merge] Reciprocal Rank Fusion deduplication + reranking
  ↓
[GIS Enrichment] Rule-based metrics from vision features
  ↓
[Format] Create prompt with features + merged chunks + GIS + question
  ↓
[LLM] Generate comprehensive answer WITH CONFIDENCE
  ↓
Answer (full context + metrics + confidence assessment)
```

### Hybrid Retrieval Mechanics

#### Semantic Search (Top-5)
```
[1] 0.91 - Informal settlements often lack infrastructure...
[2] 0.87 - Satellite imagery can identify patterns...
[3] 0.84 - Unplanned urban development exhibits irregular patterns...
[4] 0.79 - Dense construction often indicates inadequate planning...
[5] 0.76 - Vegetation near urban areas provides amenity...
```

#### Keyword Search (Top-3, BM25)
```
[A] 5.2  - Illegal settlement indicators include makeshift structures...
[B] 4.1  - Road density assessment in informal areas...
[C] 3.8  - Urban pattern classification for planners...
```

#### Reciprocal Rank Fusion Merge

Formula:
```
RRF_score(doc) = Σ [1 / (k + rank)]
where k = 60 (constant for tie-breaking)
```

Scoring:
```
[1] (rank 1 in semantic):   1/(60+1) = 0.0164
[A] (rank 1 in keyword):    1/(60+1) = 0.0164
    Combined: 0.0328 (best score!)

[2] (rank 2 in semantic):   1/(60+2) = 0.0159
    Combined: 0.0159

[3] (rank 3 in semantic):   1/(60+3) = 0.0154
[C] (rank 3 in keyword):    1/(60+3) = 0.0154
    Combined: 0.0308

[B] (rank 2 in keyword):    1/(60+2) = 0.0159
    Combined: 0.0159

[4] (rank 4 in semantic):   1/(60+4) = 0.0149

[5] (rank 5 in semantic):   1/(60+5) = 0.0145
```

**Reranked Order**:
```
1. [A] + [1] = 0.0328 (hit in both lists!)
2. [C] + [3] = 0.0308 (hit in both lists!)
3. [2] = 0.0159
4. [B] = 0.0159
5. [4] = 0.0149
```

**Dedup Result (top-5)**:
```
[A] Illegal settlement indicators... (score: 0.0328)
[C] Urban pattern classification... (score: 0.0308)
[1] Informal settlements often... (score: 0.0159)
[B] Road density assessment... (score: 0.0159)
[2] Satellite imagery can... (score: 0.0145)
```

**Key Property**: Documents appearing in BOTH lists rank higher than those in only one. This captures both semantic meaning AND keyword relevance.

### GIS Enrichment (Rule-Based)

Rule engine derives structured metrics from vision features:

```python
Features: {
  "urban_pattern": "irregular, informal layout",
  "building_density": "high, tightly packed",
  "road_density": "unpaved, low network density",
  "vegetation_density": "low, sparse"
}

Rules Applied:
  IF urban_pattern contains "irregular" OR "informal":
    pattern_class = "informal/unplanned settlement pattern"

  IF building_density contains "high" AND road_density contains "unpaved":
    infra_issues += "limited paved road network"

  IF building_density contains "high":
    est_buildings = "high (estimated 50+ structures visible)"
    density_metric = "~30-50 structures per hectare"

Output:
  {
    "pattern_classification": "informal/unplanned settlement pattern",
    "infrastructure_assessment": "limited paved road network; no planned street grid detected",
    "estimated_building_count": "high (estimated 50+ structures visible)",
    "density_metric": "approximately 30-50 structures per hectare"
  }
```

**Note on "GIS"**: This is NOT actual GIS querying (OpenStreetMap, satellite indices, etc.). It's rule-based pattern matching on vision features. Future work could integrate real GIS databases.

### Input to LLM

```
You are an expert urban planning analyst with access to domain knowledge and structured geospatial data.
You provide comprehensive analyses by combining satellite imagery features, retrieved knowledge, and GIS metrics.

=== IMAGE FEATURES ===
[6 vision features]

=== RELEVANT KNOWLEDGE ===
[A] Illegal settlement indicators include...
[C] Urban pattern classification for planners...
[1] Informal settlements often...
[B] Road density assessment...
[2] Satellite imagery can...

=== GIS DATA ===
- Estimated Building Count: high (estimated 50+ structures visible)
- Infrastructure Assessment: limited paved road network; no planned street grid detected
- Settlement Pattern Classification: informal/unplanned settlement pattern
- Density Metric: approximately 30-50 structures per hectare

=== QUESTION ===
Is there evidence of illegal settlement?

Provide a comprehensive, evidence-based answer that:
1. References specific features from the image analysis
2. Grounds your reasoning in the retrieved knowledge (cite sources by number, e.g., [1])
3. Incorporates the GIS data metrics where relevant
4. Clearly distinguishes between:
   - Observed features (from satellite analysis)
   - Knowledge-based reasoning (from retrieved documents)
   - Data-driven metrics (from GIS data)
5. Provides a confidence assessment (low/medium/high) for your conclusions with justification
```

### Sample Response

```
Direct Answer:
There is HIGH confidence evidence of informal settlement (likely meeting legal definitions of "illegal settlement").

Comprehensive Analysis:

OBSERVED FEATURES:
The satellite analysis detected irregular urban layout, makeshift structures, no grid street
pattern, high building density (30-50 structures/hectare), and minimal vegetation coverage.

KNOWLEDGE GROUNDING:
These characteristics align precisely with academic definitions [A][1] of informal settlements,
which typically lack infrastructure and exhibit irregular spatial patterns [C]. The satellite
interpretation methods [2] support this classification.

GIS METRICS:
The density estimate of 30-50 structures per hectare is consistent with informal settlement
densities in similar geographic contexts. Infrastructure assessment confirms "no planned street
grid," which distinguishes this from planned urban areas [B].

CONFIDENCE ASSESSMENT: HIGH
Justification:
+ Multiple independent indicators align (visual + knowledge + GIS)
+ Pattern matches established definitions
- Legal determination would require administrative records
- Cannot assess building quality or service provision from imagery alone

LIMITATIONS:
This analysis identifies spatial patterns consistent with informal settlement but cannot
confirm legal status without property records, ownership documentation, or administrative
designation. The imagery cannot assess:
- Building tenure or ownership status
- Access to services (water, electricity, sanitation)
- Temporal development patterns
- Local legal context
```

### Evaluation Metrics

- **Context Richness**: Does answer integrate vision + knowledge + GIS?
- **Confidence**: Is confidence assessment justified and calibrated?
- **Actionability**: Could answer inform policy decisions?
- **Completeness**: Are all three information sources used?

---

## Comparative Analysis

### Mode Comparison Matrix

| Aspect | LLM-Only | RAG Baseline | RAG Advanced |
|--------|----------|--------------|--------------|
| **Vision features** | ✅ | ✅ | ✅ |
| **Knowledge retrieval** | ❌ | ✅ Semantic | ✅ Hybrid |
| **GIS enrichment** | ❌ | ❌ | ✅ Rule-based |
| **Answer complexity** | Simple | Moderate | Comprehensive |
| **Confidence rating** | ❌ | ❌ | ✅ |
| **Processing time** | ~4.5s | ~4.7s | ~5.2s |

### Quality Improvement Expected

```
Research Hypothesis:
  RAG_Advanced_Quality > RAG_Baseline_Quality > LLM_Only_Quality

Measurement:
  - Human evaluation (1-5 scale)
  - Metric F1 (if reference answers exist)
  - Reasoning trace coherence
  - Knowledge integration count
```

### Potential Findings

**Optimistic Scenario**:
- RAG Baseline: +25-40% quality improvement
- RAG Advanced: +35-60% quality improvement

**Pessimistic Scenario** (poor knowledge base):
- RAG Baseline: -5-10% (noise in context)
- RAG Advanced: 0-5% (GIS rules don't apply)

**Mixed Scenario** (topic-dependent):
- Good topics: +50% improvement (knowledge highly relevant)
- Poor topics: -10% (irrelevant chunk distraction)

---

## Benchmarking Workflow

### Step 1: Prepare Test Dataset

Create diverse test cases:
- Urban formal settlement
- Informal settlement
- Urban sprawl
- Rural area
- Mixed development

For each: satellite image + reference question + ground truth answer

### Step 2: Run Comparison

```python
import requests
import json
import time

test_cases = [
    {
        "image": "test_01_formal_urban.png",
        "question": "Is this a planned urban development?",
        "ground_truth": "Yes, clear grid pattern with infrastructure"
    },
    # ... more test cases
]

results = {}

for case in test_cases:
    case_results = {}

    for mode in ["llm_only", "rag_baseline", "rag_advanced"]:
        start = time.time()

        response = requests.post(
            "http://localhost:8000/api/analyze",
            files={"image": open(case["image"], "rb")},
            data={
                "question": case["question"],
                "mode": mode
            }
        )

        elapsed = time.time() - start
        answer = response.json()

        case_results[mode] = {
            "answer": answer["answer"],
            "time_ms": answer["reasoning_trace"]["timing"]["total_ms"],
            "chunks_count": len(answer["retrieved_context"])
        }

    results[case["image"]] = case_results

# Save results
with open("benchmark_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Step 3: Evaluate Answers

**Manual (Human Evaluation)**:
```
Criteria:
1. Correctness (1-5): Does answer match ground truth?
2. Completeness (1-5): Does answer address all aspects?
3. Grounding (1-5): Is reasoning supported by evidence?
4. Confidence (1-5): Is confidence assessment appropriate?

For each mode, calculate average scores
```

**Automated (if reference answers exist)**:
```
BLEU Score: Measures n-gram overlap with reference
ROUGE Score: Recall-oriented understudy for gisting evaluation
Token F1: Precision/recall of key concepts

from nltk.translate.bleu_score import sentence_bleu

reference = ground_truth.split()
for mode in ["llm_only", "rag_baseline", "rag_advanced"]:
    hypothesis = results[mode].split()
    score = sentence_bleu([reference], hypothesis)
    print(f"{mode}: BLEU={score:.3f}")
```

### Step 4: Analyze Results

```python
# Aggregate scores
llm_only_avg = ...
rag_baseline_avg = ...
rag_advanced_avg = ...

# Improvement metrics
improvement_baseline = (rag_baseline_avg - llm_only_avg) / llm_only_avg
improvement_advanced = (rag_advanced_avg - llm_only_avg) / llm_only_avg

print(f"RAG Baseline improvement: {improvement_baseline*100:.1f}%")
print(f"RAG Advanced improvement: {improvement_advanced*100:.1f}%")

# Cost-benefit (performance vs. time)
cost_benefit_baseline = (rag_baseline_avg - llm_only_avg) / (timing_baseline - timing_llm)
cost_benefit_advanced = (rag_advanced_avg - llm_only_avg) / (timing_advanced - timing_llm)

print(f"Cost-benefit baseline: {cost_benefit_baseline:.3f} quality points per ms")
print(f"Cost-benefit advanced: {cost_benefit_advanced:.3f} quality points per ms")
```

### Step 5: Publish Results

Create a research report with:
- Test dataset description
- Mode comparisons (tables + graphs)
- Per-test-case analysis
- Statistical significance testing
- Recommendations for practitioners

---

## Frontend Comparison Feature

The frontend includes a **comparison toggle** to run all 3 modes on the same input:

```javascript
if (compareToggle.checked) {
    // Run all 3 modes sequentially
    for (mode of ["llm_only", "rag_baseline", "rag_advanced"]) {
        result = await analyze(image, question, mode);
        results.push(result);
    }
    // Display side-by-side
    renderComparisonCards(results);
}
```

Result display:
- Left: LLM-Only answer
- Center: RAG Baseline answer
- Right: RAG Advanced answer
- Overlay feature counts, timing, chunk counts for easy comparison

---

## Research Opportunities

1. **Knowledge Base Quality**: Vary amount and quality of ingested documents
2. **Retrieval Strategies**: Compare semantic vs. keyword vs. hybrid
3. **Prompt Engineering**: Optimize system prompts for each mode
4. **Model Selection**: Test different LLMs (Gemma, Mistral, Llama)
5. **Domain Specificity**: Evaluate on different domains (agriculture, mining, disaster)
6. **Temporal Analysis**: Analyze multi-date imagery to detect changes

---

## References

- Reciprocal Rank Fusion: https://plg.uwaterloo.ca/~gvcormac/rrf.html
- BLEU Score: https://en.wikipedia.org/wiki/BLEU
- ROUGE Score: https://github.com/google-research/google-research/tree/master/rouge
- Semantic Search: https://www.sbert.net/docs/usage/semantic_search.html
- BM25: https://en.wikipedia.org/wiki/Okapi_BM25
