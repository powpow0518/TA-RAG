import os

import google.generativeai as genai
import voyageai
from fastembed import SparseTextEmbedding
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client import QdrantClient

from app.core.config import settings


class RAGRuntime:
    def __init__(self):
        self.dense_embedding_model = None
        self.sparse_embedding_model = None
        self.voyage_client = None
        self.qdrant_client = None
        self.gemini_model = None
        self.gemini_model_flash = None

    def initialize(self):
        if self.qdrant_client is not None:
            return

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-3-flash-preview")
        self.gemini_model_flash = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

        os.environ["VOYAGE_API_KEY"] = settings.VOYAGE_API_KEY
        self.dense_embedding_model = VoyageAIEmbeddings(model="voyage-3", batch_size=128)
        self.voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

        self.sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)


rag_runtime = RAGRuntime()
