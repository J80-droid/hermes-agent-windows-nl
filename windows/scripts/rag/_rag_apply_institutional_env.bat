@echo off
rem Institutionele RAG-env defaults (zie scripts\rag_pipeline\rag_institutional_defaults.py).
if not defined HERMES_RAG_LIVE_STALE_SEC set "HERMES_RAG_LIVE_STALE_SEC=120"
if not defined HERMES_RAG_QUIET_TORCH set "HERMES_RAG_QUIET_TORCH=1"
if not defined HERMES_RAG_PERF_PROFILE set "HERMES_RAG_PERF_PROFILE=safe"
if not defined TRANSFORMERS_VERBOSITY set "TRANSFORMERS_VERBOSITY=error"
if not defined TOKENIZERS_PARALLELISM set "TOKENIZERS_PARALLELISM=false"
exit /b 0
