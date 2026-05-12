CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS rag;

ALTER DATABASE rag SET search_path TO rag, public;
ALTER ROLE rag_user SET search_path TO rag, public;
