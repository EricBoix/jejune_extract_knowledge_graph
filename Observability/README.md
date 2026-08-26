# LLM Observability<!-- omit in toc -->

## Table of contents<!-- omit in toc -->

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Launching the backend](#launching-the-backend)
- [Configuring and running the instrumented script](#configuring-and-running-the-instrumented-script)
- [Trivial analysis walkthrough](#trivial-analysis-walkthrough)
- [References](#references)
- [Quick and dirty "logs": patch `langchain_ollama`](#quick-and-dirty-logs-patch-langchain_ollama)

## Introduction

This directory sets up end-to-end LLM observability for `extract_kg_graph.py`
using two fully free and open-source components:

- **Instrumentation: [Traceloop OpenLLMetry](https://github.com/traceloop/openllmetry)** a Python SDK that auto-instruments LangChain (and Ollama) calls and emits OpenTelemetry traces.
- **Backend: [grafana/otel-lgtm](https://github.com/grafana/docker-otel-lgtm)**  a single [Docker image](https://hub.docker.com/r/grafana/otel-lgtm) bundling (among others)
  - an [OTLP](https://github.com/open-telemetry) HTTP receiver: server for trace ingestion
  - Grafana: a web UI integrating tools
    - Tempo for trace analysis
    - Prometheus for metrics (on spans).

Note: the full LLM Observability pipeline uses an Collector component/stage (for optimization) e.g. [Grafana's Alloy on k8s](https://grafana.com/docs/opentelemetry/collector/grafana-alloy-kubernetes/).

## Prerequisites

- Docker (with Compose v2: `docker compose` command available).
- Python virtual environment activated (refer to [root `README.md`](../README.md)).

## Launching the backend

From this directory:

```bash
docker compose up -d
```

Verify that Grafana is up:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health
# expected: 200
```

| Service | URL | Usage |
| ------- | --- | ------------------- |
| Grafana UI | <http://localhost:3000> (Default credentials: admin / admin) | UI tool integration |
| Prometheus | <http://localhost:9090> | Metrics |
| OTLP HTTP receiver | <http://localhost:4318> | Ingestion |
| OTLP gRPC receiver | `localhost:4317` | Unused in this context |

To stop the backend:

```bash
docker compose down
```

## Configuring and running the instrumented script

Set the TRACELOOP_BASE_URL OTLP endpoint in `.env`) and run the extraction as usual:

```bash
python extract_kg_graph.py \
  --load_json_document path/to/chunks.json \
  --use_llm_telemetry_server true
```

Traceloop initialises automatically (see the `if __name__ == "__main__"` block in the script)
and forwards every LangChain and Ollama call as an OpenTelemetry trace to the collector.

## Trivial analysis walkthrough

### 1. Open Grafana

Navigate to <http://localhost:3000> and log in with `admin` / `admin`.

### 2. Explore traces in Tempo

1. In the left sidebar click **Explore** (compass icon).
2. Select the **Tempo** data source from the drop-down.
3. Switch to **Search** mode and set:
   - **Service name**: `jj-build-knowledge-graph`
4. Click **Run query**. Each run of the extraction script appears as one root trace.

### 3. Inspect a single trace

Click any trace row to open the flame graph. Key spans to look for:

| Span name | What it measures |
| --------- | --------------- |
| `langchain.ChatOllama` | End-to-end LLM call duration |
| `langchain.LLMGraphTransformer` | Graph extraction time per document chunk |
| `gen_ai.completion` | Token-level detail (prompt / completion tokens) |

### 4. Compare runs in Prometheus

1. In **Explore**, select the **Prometheus** data source.
2. Try this PromQL query to chart LLM call latency over time:

   ```promql
   histogram_quantile(0.95,
     sum by (le) (rate(gen_ai_client_operation_duration_bucket[5m]))
   )
   ```

3. Use the **Add to dashboard** button to save the panel for future reference.

### 5. What to look for

- **High `langchain.ChatOllama` duration** — the LLM is the bottleneck; consider a faster model
  or smaller chunk size.
- **Many short `LLMGraphTransformer` spans** — the document was split into many small chunks;
  consider increasing the chunk size or switching splitter strategy.
- **Token counts climbing** — prompts are growing; review the system prompt or context window
  usage in `graph_utils.py`.

## References

[Getting started with OpenTelemetry for LLM observability](https://www.youtube.com/watch?v=HAvbWZqoV34) talk by [Nir Gazit (CEO/co-founder of @Traceloop)](https://www.traceloop.com/author/nir-gazit).

## Quick and dirty "logs": patch `langchain_ollama`

Tracing LLM calls can be done by patching the `langchain_ollama` package:

```bash
cd venv/lib
patch -uNp1 python3.10/site-packages/langchain_ollama/chat_models.py ../../langchain_ollama_chat_models.patch
```

Note (in case the patch gets irrelevant because the `langchain_ollama` package is not pinned):
> this patch simply adds the following line as first line of the `_create_chat_stream` member function (within the `venv/lib/python3.10/site-packages/langchain_ollama/chat_models.py` file):
>
> ```python
> print(" (chat client call) ", end='', flush=True)  # EBO was here: added
> ```
