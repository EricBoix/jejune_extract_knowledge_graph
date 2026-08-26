import json
import os
import sys
import argparse
import dotenv
from traceloop.sdk import Traceloop

from langchain_core.documents import Document

from graph_utils import (
    DEBUG_PROMPT,
    create_neo4j_database,
    extract_graph,
    initialize_llm,
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract graph from LangChain Document JSON files and store in Neo4j."
    )
    parser.add_argument(
        "--load_json_document",
        action="append",
        metavar="JSON_FILE",
        help="Load documents from a JSON file (repeatable; all files are concatenated).",
    )
    parser.add_argument(
        "--use_llm_telemetry_server",
        type=bool,
        metavar="BOOL",
        help="Whether to use an llm OpenTelemetry server or not.",
    )
    return parser.parse_args()


def load_documents_from_json(json_path):
    def as_document(dct):
        if "__document__" in dct:
            return Document(metadata=dct["metadata"], page_content=dct["page_content"])
        return dct

    with open(json_path, "r") as in_file:
        try:
            documents = json.load(fp=in_file, object_hook=as_document)
        except ValueError as e:
            print(DEBUG_PROMPT, "Invalid json: %s" % e)
            sys.exit()
    return documents


def load_documents(args):
    documents = []
    for json_path in (args.load_json_document or []):
        documents.extend(load_documents_from_json(json_path))
    if not documents:
        print(DEBUG_PROMPT + "No documents loaded. Exiting.")
        sys.exit()
    print(
        DEBUG_PROMPT + "Number of documents for LLMGraphTransformer to deal with: ",
        len(documents),
    )
    return documents


def main():
    dotenv.load_dotenv()
    args = parse_arguments()
    if args.use_llm_telemetry_server:
        Traceloop.init(
            disable_batch=True,
            app_name="jj-build-knowledge-graph",
            api_endpoint=os.environ.get("TRACELOOP_BASE_URL", "http://localhost:4318"),
        )
    documents = load_documents(args)
    llm = initialize_llm()
    graph_documents = extract_graph(llm, documents)
    create_neo4j_database(graph_documents)


if __name__ == "__main__":
    main()
