import google.generativeai as genai
from fastembed import SparseTextEmbedding
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client import QdrantClient

from app.core.config import settings


class QuizRuntime:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-3-flash-preview")
        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        self.dense_model = VoyageAIEmbeddings(
            model="voyage-3",
            batch_size=128,
            voyage_api_key=settings.VOYAGE_API_KEY,
        )
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


quiz_runtime = QuizRuntime()
