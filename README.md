# Hands on lowbrow exploration of GraphRAG in Python<!-- omit in toc -->

## Table of contents<!-- omit in toc -->

- [Introduction](#introduction)
- [Running things: the simple extraction use case](#running-things-the-simple-extraction-use-case)
- [Running with Docker](#running-with-docker)
- [Visually explore the resulting knowledge graph (with neo4j web UI)](#visually-explore-the-resulting-knowledge-graph-with-neo4j-web-ui)
- [Use the knowledge graph programmatically](#use-the-knowledge-graph-programmatically)
- [Dump/Restore the database content for later usage](#dumprestore-the-database-content-for-later-usage)
- [LLM (calls) observability](#llm-calls-observability)
- [References](#references)
- [Next steps](#next-steps)

## Introduction

This directory explores, with a direct hands-on approach, a process of graph extraction (and exploitation) that is described in the ["Local GraphRAG with LLaMa 3.1 - LangChain, Ollama & Neo4j" youtube tutorial](https://www.youtube.com/watch?v=nkbyD4joa0A).
The original associated code, from which this work is partly derived, is available through [this Coding Crash Courses git repository](https://github.com/Coding-Crashkurse/GraphRAG-with-Llama-3.1.git).

## Running things: the simple extraction use case

### Configure and start a Neo4j database (to collect the extracted graph)

Install and configure [`jejune_cli`](https://github.com/EricBoix/jejune_cli), then verify the setup:

```bash
uv tool install git+https://github.com/EricBoix/jejune_cli
jejune configuration doc-steward init
# Proceed with the configuration of the files located in .jejune/
jejune doctor
```

Define a convenience variable for the results directory, then start Neo4j:

```bash
export RESULTS_DIR=`pwd`/result_data
jejune neo4j start $RESULTS_DIR
```

### Note: run the chunk splitters first

Before extracting, produce a JSON document from your `jejune_doc_*` repository
using [`jejune_chunk_splitters`](https://github.com/EricBoix/jejune_chunk_splitters). Refer to that repository for installation, available strategies (by headers, by paragraphs, by sentences), output flags, and Docker usage. Usage boils down to commands alike

```bash
jejune chunk-splitters split /path/to/jejune_doc_<name>
```

The output JSON is written beside the source markdown file with an auto-generated name, e.g. `<stem>_-_Headers_as_LangChain_document.json`.

### Realize the graph extraction

```bash
# Prepare the virtual environment
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```bash
# Retrieve some input data e.g.
git clone https://github.com/EricBoix/jejune_doc_Four_Noble_Truths.git

# Extract the knowledge graph and store it in Neo4j
python extract_kg_graph.py \
  --load_json_document \
  jejune_doc_Four_Noble_Truths/original_data/<stem>_-_Headers_as_LangChain_document.json
```

### Notes

- when the extraction is too lengthy (or running on a remote ssh server) consider using

    ```bash
    python extract_kg_graph.py --load_json_document by_headers.json > extract.log &
    tail -f extract.log
    ```

- when a pre-existing neo4j database content exists (look a the content of the `./data` directory or run `jejune neo4j stats`, and depending on your filesystem rights setup) you might get an error message. Then try running `jejune neo4j delete ./data`

## Running with Docker

Build the image:

```bash
# Extractor image (this repository)
docker build -t jejuneness:extract_knowledge_graph \
  https://github.com/EricBoix/jejune_extract_knowledge_graph.git#:DockerContext
```

Shallow testing of the extractor image:

```bash
docker run jejuneness:extract_knowledge_graph extract_kg_graph.py --help
```

Run the extraction (adjust paths and `.env` as needed):

```bash
docker run --rm \
  -v /path/to/jejune_doc_<name>:/data \
  --env-file .env \
  jejuneness:extract_knowledge_graph \
  extract_kg_graph.py \
  --load_json_document /data/original_data/<stem>_-_Headers_as_LangChain_document.json
```

### Blending multiple documents into a single extraction

Supply multiple `--load_json_document` arguments to `extract_kg_graph.py` to
blend JSON files produced by any splitter:

```bash
python extract_kg_graph.py \
  --load_json_document result_data/blended_-_Sentences_as_LangChain_document.json \
  --load_json_document result_data/Rob_Burbea_-_Sentences_as_LangChain_Document.json
```

## Visually explore the resulting knowledge graph (with neo4j web UI)

Interactively explore the extracted graph through neo4j web UI

```bash
# For exact hostname/port refer to the NEO4J_URI entry of your `/.env` # configuration file):
open http://localhost:7474/
```

Run [`cypher (queries)`](https://neo4j.com/docs/cypher-manual/current/introduction/) like

```bash
# Assert the UI is connected to the proper db server (has to match what was 
# configured in you .env file)
$:server connect   
# Make sure you are connect to the right database (again this has to match 
# with what was configured in you .env file)
$:use neo4j
# Display all the nodes of the full extracted graph. Caveat emptor: 
# within the UI settings, the "Initial node display" integer parameter 
# controls the number of nodes displayed which defaults to 300
neo4j$ MATCH (n) RETURN n
# Display all nodes AND edges
neo4j$ MATCH (n) MATCH ()-[r]->() RETURN n, r

# Display the nodes with the "Person" label
neo4j$ MATCH (n) WHERE n:Person RETURN n
# Display the nodes NOT having the "Person" label
neo4j$ MATCH (n) WHERE NOT n:Person RETURN n
# Display the nodes not having "Document" as single label
neo4j$ MATCH (n) WHERE NOT(SIZE(LABELS(n)) = 1 AND n:Document) RETURN n
# A composition of the above
neo4j$ MATCH (n) WHERE NOT(SIZE(LABELS(n)) = 1 AND n:Document) and NOT n:Person RETURN n
# Nodes that are not documents together with their relations
neo4j$ MATCH (n) WHERE NOT n:Document OPTIONAL MATCH (n)-[r]-(c) WHERE NOT c:Document RETURN n,r,c
...
```

## Use the knowledge graph programmatically

### Displaying knowledge graph main characteristics

```bash
python display_neo4jdb_graph_characteristics.py
```

### Searching the database

For example search the graph database with a Natural Language query by running the provided python script

```bash
python extract_from_knowledge_graph.py
```

Or search both the knowledge graph and the embedding space structures with

```bash
python vector_and_graph_hybrid_search.py
```

## Dump/Restore the database content for later usage

Use `jejune neo4j dump` and `jejune neo4j restore` — refer to [`jejune_cli`](https://github.com/EricBoix/jejune_cli) for details.

## LLM (calls) observability

Refer to [`Observability/README.md`](Observability/README.md) for installation, backend launch, and a guided analysis walkthrough of LLM observability.

Here are a few numerical results showing the number of [LangChain documents](https://reference.langchain.com/python/langchain-core/documents) sent to the LLM per splitting strategy.

| Book | By headers | By paragraphs | By sentences | # llm calls |
| ---- | ---------- | ------------- | ------------ | ----------- |
| [Four Noble Truths](https://github.com/EricBoix/jejune_doc_Four_Noble_Truths) | 1 | — | — | 1 |
| [Rob Burbea](https://github.com/EricBoix/jejune_doc_Rob_Burbea) | 7 | — | 258 | 265 |
| [Collecting Gold Dust](https://github.com/EricBoix/jejune_doc_Collecting_Gold_Dust) | FIXME | FIXME | FIXME | FIXME |
| [Zen flesh, zen bones](https://github.com/EricBoix/jejune_doc_Zen_Flesh_Zen_Bones) | 45 | — | 2479 | 2524 |

## References

- [GraphRAG: The Marriage of Knowledge Graphs and RAG: Emil Eifrem](https://www.youtube.com/watch?v=knDDGYHnnSI)
- [Introduction to Neo4j](https://www.youtube.com/watch?v=YDWkPFijKQ4cdt)
- [Build a RAG agent with LangChain](https://docs.langchain.com/oss/python/langchain/rag#ollama)
- Calling [LLM through OpenwebUI examples](https://github.com/UDL-LIRIS/python-openwebui-bootstraping-examples)

## Next steps

### Improve graph extraction: define and use ontologies

- Refer to this inadequate yet inspiring, [OWL Ontology of Consciousness](https://www.researchgate.net/publication/383227961_An_OWL_Ontology_of_Consciousness)
- [Knowledge graphs organizing principles tutorial](https://medium.com/@michelleloh.tech/day-15-learn-knowledge-graphs-part-2-organizing-principles-17c76eb3686b)

### Improve graph extraction: more stuff to try

- [Read this and improve the script](https://neo4j.com/blog/developer/knowledge-graph-extraction-challenges/)

### Improve graph extraction: explore additional splitting strategies

[RAG chunking strategies article](https://dev.to/sreeni5018/rag-chunking-strategies-4i3a) mentions 6 strategies (checked boxes indicate strategies implemented in this repo)

- Fixed-size chunking (`CharacterTextSplitter`)
- Recursive character chunking (`RecursiveCharacterTextSplitter`)
- Semantic chunking
- Document structure-aware chunking:
  - [x] Header-section splitting (`split_by_headers.py` — uses `markdown-it-py`)
  - [x] Paragraph splitting (`split_by_paragraphs.py`)
  - [x] Sentence splitting (`split_by_sentences.py` — uses `nltk.sent_tokenize`)
- Hierarchical (parent/child) chunking — naturally expressible with the existing splitters
- LLM-based chunking

References:

- [`SemanticChunker` class](https://github.com/langchain-ai/langchain-experimental/blob/main/libs/experimental/langchain_experimental/text_splitter.py#L99) as offered by [langchain_experimental](https://github.com/langchain-ai/langchain-experimental/tree/main)
- ["A Visual Exploration of Semantic Text Chunking" article](https://towardsdatascience.com/a-visual-exploration-of-semantic-text-chunking-6bb46f728e30/)
- [Langchain's tutorial: Build a semantic search engine with LangChain](https://docs.langchain.com/oss/python/langchain/knowledge-base)
