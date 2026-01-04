from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from typing import List, Any
from pydantic import PrivateAttr
import time

class TimedRetriever(BaseRetriever):
    """Wrapper retriever that tracks retrieval latency."""
    
    _retriever: Any = PrivateAttr()
    _metrics_tracker: Any = PrivateAttr()
    
    def __init__(self, retriever: Any, metrics_tracker: Any, **kwargs):
        super().__init__(**kwargs)
        self._retriever = retriever
        self._metrics_tracker = metrics_tracker

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        start = time.perf_counter()
        try:
            # Prefer modern Runnable interface if present
            if hasattr(self._retriever, "invoke"):
                docs = self._retriever.invoke(query, config={"callbacks": run_manager.get_child()} if run_manager else None)
            elif hasattr(self._retriever, "get_relevant_documents"):
                docs = self._retriever.get_relevant_documents(query, callbacks=run_manager.get_child() if run_manager else None)
            else:
                docs = self._retriever._get_relevant_documents(query, run_manager=run_manager)
            return docs
        finally:
            self._metrics_tracker.record_retrieval_latency((time.perf_counter() - start) * 1000)

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        start = time.perf_counter()
        try:
            if hasattr(self._retriever, "ainvoke"):
                docs = await self._retriever.ainvoke(query, config={"callbacks": run_manager.get_child()} if run_manager else None)
            elif hasattr(self._retriever, "aget_relevant_documents"):
                docs = await self._retriever.aget_relevant_documents(query, callbacks=run_manager.get_child() if run_manager else None)
            else:
                docs = await self._retriever._aget_relevant_documents(query, run_manager=run_manager)
            return docs
        finally:
            self._metrics_tracker.record_retrieval_latency((time.perf_counter() - start) * 1000)
