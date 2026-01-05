# Storage and Metastores

This document provides a technical overview of how Persona manages data storage and metadata.

## Overview

Persona distinguishes between two types of storage:

1.  **File Store:** Responsible for storing the actual content of roles and skills (Markdown files, scripts, assets).
2.  **Meta Store:** Responsible for storing searchable metadata, including vector embeddings for similarity search.

## File Store

The File Store handles the physical storage of your Persona library.

### Architecture

Persona uses the `fsspec` (Filesystem Spec) library to abstract file operations. This allows the core logic to remain independent of the underlying storage medium.

### Supported Backends

| Backend | Type | Description |
| :--- | :--- | :--- |
| **Local** | `local` | Stores roles and skills on the local filesystem. This is the default. |

### Directory Structure

Regardless of the backend, Persona maintains a consistent directory structure within the configured `root` directory:

*   `/roles/`: Contains subdirectories for each persona role.
*   `/skills/`: Contains subdirectories for each persona skill.
*   `/index/`: Default location for metadata index files.

## Meta Store

The Meta Store provides indexing and search capabilities, enabling Persona to "match" queries to the most relevant roles or skills.

### Architecture

The Meta Store uses a **Bridge Pattern** to separate the storage engine from the indexing logic. It primarily stores:

*   **Metadata:** Names, descriptions, tags, and UUIDs.
*   **Embeddings:** 384-dimensional vector representations of descriptions for similarity search.

### Supported Backends

| Backend | Type | Description |
| :--- | :--- | :--- |
| **DuckDB** | `duckdb` | An in-memory database that persists its state to Parquet files on the File Store. |

### How DuckDB Meta Store Works

1.  **Connection:** Upon starting, Persona creates an in-memory DuckDB instance.
2.  **Bootstrapping:** It attempts to load existing index data from Parquet files located in the `/index/` directory of the File Store.
3.  **Operation:** Search and listing operations are performed against the in-memory tables for high performance.
4.  **Persistence:** When the database connection is closed, the in-memory tables are exported as Parquet files, **overwriting** the existing indexes on the File Store.

> **Technical Note:** Because the total number of roles and skills in a typical registry is expected to be relatively small (thousands at most), overwriting the entire index upon each write-session closure is an efficient and safe way to ensure the Meta Store remains in sync with the File Store.

## Technical Details

### Embedding Model

Persona currently uses the `all-MiniLM-L6-v2` model (quantized for efficiency) to generate vector embeddings.

*   **Dimensions:** 384
*   **Distance Metric:** Cosine Distance (used by the Meta Store to find relevant matches).

### Atomicity and Transactions

Persona implements a basic transaction mechanism for operations that modify both the File Store and the Meta Store. This ensures that:

*   If a file fails to save, the metadata index is not updated.
*   Changes are rolled back if an error occurs during the process.
