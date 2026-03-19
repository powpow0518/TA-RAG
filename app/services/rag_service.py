import re
import traceback
import asyncio
from typing import List, Generator, AsyncGenerator, Optional
from qdrant_client import models
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.providers.rag_runtime import rag_runtime
from app.repositories.rag_repository import rag_repository
import json

# 全域變數
INITIAL_SEARCH_K = 30
FINAL_K = 5

def initialize_rag_service():
    rag_runtime.initialize()

    # 避免重複初始化
    if qdrant_client is not None:
        return

    print("🚀 初始化 RAG 服務 (Gemini 3 版)...")

    # 配置 Gemini
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-3-flash-preview")
    gemini_model_flash = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    # Init Voyage
    os.environ["VOYAGE_API_KEY"] = settings.VOYAGE_API_KEY
    dense_embedding_model = VoyageAIEmbeddings(model="voyage-3", batch_size=128)
    voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

    # Init Sparse & Qdrant
    sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    qdrant_client = QdrantClient(url=settings.QDRANT_URL)

    print("✅ RAG 服務初始化完成。")

def translate_query_if_needed(query: str) -> str:
    if re.search(r'[\u4e00-\u9fff]', query): return query
    try:
        # Prompt 文字保持不變
        response = rag_runtime.gemini_model_flash.generate_content(
            f"Translate to Traditional Chinese.\n\n{query}"
        )
        return response.text.strip()
    except Exception:
        return query

def perform_search(query: str, course_id: str, k: int = settings.RAG_FINAL_K) -> List[str]:
    # 確保服務已初始化
    if not rag_runtime.qdrant_client: initialize_rag_service()

    collection_name = course_id.lower()
    translated_query = translate_query_if_needed(query)

    print(f"🕵️ [Debug] 搜尋 Collection: {collection_name}")
    print(f"🕵️ [Debug] 翻譯後 Query: {translated_query}")

    try:
        dense_vec = rag_runtime.dense_embedding_model.embed_query(translated_query)
        sparse_vec = list(rag_runtime.sparse_embedding_model.embed([translated_query]))[0]

        search_result = rag_runtime.qdrant_client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vec,
                    using="dense",
                    limit=settings.RAG_INITIAL_K
                ),
                models.Prefetch(
                    query=models.SparseVector(**sparse_vec.as_object()),
                    using="sparse",
                    limit=settings.RAG_INITIAL_K
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=settings.RAG_INITIAL_K,
            with_payload=True
        )

        print(f"🕵️ [Debug] Qdrant 初搜結果數量: {len(search_result.points)}")
        initial_docs = [hit.payload['page_content'] for hit in search_result.points if hit.payload]
        if not initial_docs:
            return []

        reranking = rag_runtime.voyage_client.rerank(
            query=translated_query,
            documents=initial_docs,
            model="rerank-2",
            top_k=k
        )

        filtered_results = []
        for res in reranking.results:
            if res.relevance_score >= settings.RAG_SIMILARITY_THRESHOLD:
                filtered_results.append(res.document)

        return filtered_results

    except Exception as e:
        print(f"❌ Search Error: {e}")
        return []

def check_course_relevance(query: str, course_id: str) -> str:
    # Prompt 文字保持不變
    prompt = f"課程代碼：{course_id}。判斷問題類別：'relevant'(相關/知識), 'general'(閒聊), 'off_topic'(無關/惡意)。只回標籤。"
    try:
        res = rag_runtime.gemini_model_flash.generate_content([prompt, query])
        ans = res.text.strip().lower()
        if 'off_topic' in ans: return 'off_topic'
        if 'general' in ans: return 'general'
        return 'relevant'
    except: return 'relevant'

def extract_keywords_sync(query: str, answer: str, course_name: str = "一般課程") -> str:
    try:
        # Prompt 文字保持不變
        system_prompt = f"""
        你現在是「{course_name}」這門課程的知識庫管理員。
        任務：從使用者的問題與 AI 的回答中，提取 3-5 個具備「學術檢索價值」的關鍵字。

        【提取規則】
        1. **只保留專有名詞**：如特定理論、公式、軟體功能、專有名詞 (例如：Kurtosis, ANOVA, 迴歸分析)。
        2. **過濾通用詞彙**：絕對不要包含「請問」、「怎麼算」、「謝謝」、「教授」、「為什麼」這類通用詞。
        3. **格式**：只輸出關鍵字，用逗號分隔，不要有任何前綴。
        """

        response = rag_runtime.gemini_model_flash.generate_content(f"{system_prompt}\n問題：{query}\n回答：{answer}")
        return response.text.strip()
    except:
        return ""

def generate_and_review_followup(query: str, answer: str, context_str: str) -> str:
    # Prompt 文字保持不變
    prompt = f"""
你是一個嚴謹的教學引導者，請根據下方「上下文」與「回答」，決定是否應該提出一個後續問題。

【上下文】
{context_str}

【剛才的回答】
{answer}

請嚴格遵守以下流程（在心中完成，不要輸出過程）：
1. 判斷上下文與回答是否「足以支撐一個有意義、具體、不臆測」的問題。
2. 若可以，請從以下兩種策略中「擇一」構思問題：
   - 反問（Concept Check）：確認使用者是否真正理解剛才的核心概念。(例如：「所以您知道...為什麼會...嗎？」)
   - 追問（Follow-up）：引導使用者探索上下文中**已明確出現**的相關概念。(例如：「您想進一步了解...嗎？」)
3. 自為審查：
   - 問題中的所有概念，**必須能在上下文或回答中找到依據**。
   - 問題接在剛才回答後，必須自然、不突兀。

【輸出規則（非常重要）】
- 若通過以上自我審查：只輸出「一個完整的問題句子」。
- 若任何一項不符合：只輸出大寫字串「NONE」。
- 不要輸出理由、標註、前綴或多餘說明。
"""

    try:
        response = rag_runtime.gemini_model_flash.generate_content(prompt)
        result = response.text.strip()
        if result == "NONE":
            return ""
        return result
    except Exception as e:
        return ""

def contextualize_query(query: str, history: list) -> str:
    if not history:
        return query
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    last_msg = history[-1]
    has_followup = "[系統追問]" in last_msg.get('content', '')
    short_responses = {"想", "好", "要", "是的", "對", "沒錯", "可以", "不用", "沒關係", "ok"}
    is_short_response = query.strip().lower() in short_responses or len(query.strip()) < 4

    if has_followup and is_short_response:
        # Prompt 文字保持不變
        prompt = f"""
        對話歷史：
        {history_str}

        使用者剛才的簡短回應：{query}

        上一輪對話中，AI 提出了一個追問（標記為 [系統追問]）。
        任務：
        1. 如果使用者的回應是「肯定」(如：想、好)，請直接將「追問的核心內容」改寫成一個完整問題。
           (例如：追問是「想了解計算公式嗎？」，使用者回「想」，請輸出「請告訴我計算公式」)
        2. 如果使用者的回應是「否定」，請輸出「DECLINE」。
        3. 如果無法判斷，輸出原文。

        只輸出改寫後的問題，不要解釋。
        """
        try:
            res = rag_runtime.gemini_model_flash.generate_content(prompt)
            result = res.text.strip()
            if result == "DECLINE": return query
            return result
        except:
            return query

    pronouns = ["他", "她", "它", "這", "那", "其", "此", "上一", "個", "相關"]
    has_pronoun = any(p in query for p in pronouns)
    if not has_pronoun and len(query) > 4:
        return query

    # Prompt 文字保持不變
    prompt = f"""
    Chat History:
    {history_str}
    Latest: {query}
    Rewrite to standalone question if needed (Traditional Chinese):
    """
    try:
        res = rag_runtime.gemini_model_flash.generate_content(prompt)
        return res.text.strip() or query
    except: return query

import time
class Timer:
    def __init__(self):
        self.t = time.perf_counter()
    def mark(self, name):
        now = time.perf_counter()
        print(f"⏱ {name}: {(now - self.t)*1000:.1f} ms")
        self.t = now

class RAGService:
    def __init__(self):
        pass

    def check_cache(self, course_id: str, query: str, db_session: Session) -> str:
        try:
            # 1. 精確匹配 (最快，不需向量)
            exact_hit = rag_repository.get_exact_cache(db_session, course_id, query)
            if exact_hit:
                print(f"🎯 精確匹配快取命中!")
                return exact_hit.answer

            # 2. 向量匹配
            t_q = translate_query_if_needed(query)
            query_vector = rag_runtime.dense_embedding_model.embed_query(t_q)
            # 將門檻放寬一點，提高命中率
            CACHE_THRESHOLD = 0.35
            cache_hit = rag_repository.get_semantic_cache_hit(db_session, course_id, query_vector)
            CACHE_THRESHOLD = 0.35
            cache_obj, distance = cache_hit
            if cache_obj is not None and distance is not None:
                if distance < CACHE_THRESHOLD:
                    print(f"🎯 向量匹配快取命中 (距離: {distance:.4f})")
                    return cache_obj.answer
            return None
        except:
            return None

    def is_cache_worthy(self, q: str) -> bool:
        q = q.strip()
        if len(q) <= 4 or q in {"想", "好", "是的", "不用", "不用了"}:
            return False
        return True

    def save_record(self, session_id, course_id, query, answer, user_id, follow_up_question=None, refined_query=None):
        with rag_repository.session_scope() as db_session:
            try:
                course_obj = rag_repository.get_course(db_session, course_id)
                course_name = course_obj.course_name if course_obj else course_id
                
                # 即使關鍵字提取失敗，也不要讓整個交易回滾
                try:
                    keywords = extract_keywords_sync(query, answer, course_name)
                except:
                    keywords = ""

                cache_vector = None
                
                # 修正過濾條件，使其能匹配到 ask_stream 定義的警語
                is_hallucination = "註：此答案由 GPT 生成" in answer or "資料庫中未找到相關資訊" in answer
                
                is_hallucination = "閮鳴?甇斤?獢 GPT ??" in answer or "鞈?摨思葉?芣?啁??閮?" in answer
                if refined_query and self.is_cache_worthy(refined_query) and not is_hallucination:
                    try:
                        t_q = translate_query_if_needed(refined_query)
                        cache_vector = rag_runtime.dense_embedding_model.embed_query(t_q)
                    except Exception as e:
                        print(f"⚠️ Cache Save Skip: {e}")
                
                rag_repository.save_conversation_bundle(
                    db_session,
                    session_id=session_id,
                    course_id=course_id,
                    user_id=user_id,
                    query=query,
                    answer=answer,
                    keywords=keywords,
                    follow_up_question=follow_up_question,
                    refined_query=refined_query if cache_vector is not None else None,
                    cache_vector=cache_vector,
                )
            except Exception as e:
                print(f"❌ Save Record Error: {e}")
                raise

    async def ask_stream(self, query, course_id, session_id, db_session, user, background_tasks, history=None) -> AsyncGenerator[str, None]:
        timer = Timer()
        course_obj = rag_repository.get_course(db_session, course_id)
        if not course_obj: yield "課程錯誤"; return
        course_name_str = course_obj.course_name if course_obj else course_id

        db_history = rag_repository.get_recent_history(db_session, session_id, limit=2)
        
        history_for_context = []
        for h in reversed(db_history):
            content_str = h.content or ""
            if h.role == "assistant" and h.follow_up_question: content_str += f"\n\n[系統追問]: {h.follow_up_question}"
            history_for_context.append({"role": h.role, "content": content_str})

        refined_query = contextualize_query(query, history_for_context)
        
        # 保持流程不變，但在這裡呼叫優化過的 check_cache
        cached_ans = await asyncio.to_thread(self.check_cache, course_id, refined_query, db_session)
        if cached_ans:
            yield cached_ans
            background_tasks.add_task(self.save_record, session_id=session_id, course_id=course_id, query=query, answer=cached_ans, user_id=user.user_id, refined_query=refined_query)
            return

        docs = await asyncio.to_thread(perform_search, refined_query, course_id)
        context_str = "\n\n".join(docs) if docs else "無 (資料庫中未找到相關文件)"
        # 警語字串維持原樣
        warning_suffix = "\n\n(註：此答案由 GPT 生成，課程資料庫中未找到相關資訊。)" if not docs else ""

        base_system_prompt = f"""
            你現在是「{course_name_str}」這門課程的專業助教。
            你的對象是具有大學以上程度，但尚未熟悉此領域概念的初學者。

            【任務判斷流程】
            請針對使用者的問題與提供的核心知識進行分析，並依序執行以下邏輯：

            1. **判斷是否為無關/閒聊（優先拒絕）**：
               - 若使用者輸入為純打招呼（如「哈囉」「你好」）、感謝語，
                 或明顯與課程無關的閒聊（如「今天天氣如何」）。
               - 請直接回答：
                 「您的問題與本課程無關，請重新輸入。」
               - 不需補充說明，不要嘗試延伸回答。

            2. **判斷是否有可用的「核心知識」**：
               - 若上方提供了【核心知識】，且其內容與使用者問題相關，
                 請**優先且僅依據該核心知識進行教學式回答**。

            3. **判斷是否為課程相關專業問題（RAG Miss 補救）**：
               - 若未提供【核心知識】，但問題屬於「{course_name_str}」相關之專業領域問題，
                 請運用你的專業知識進行回答，視為有效教學。

            4. **最終判定（拒答條件）**：
               - 若沒有核心知識，且問題也與本課程領域完全無關，
                 請回答：
                 「您的問題與本課程無關，請重新輸入。」

            ────────────────────
            【回答撰寫原則（僅在「決定回答」時適用）】

            請將內容整理成**課程講義式說明**，並遵守以下原則：

            1. **概念說明清楚**
               - 避免一次使用過多專業術語
               - 如需使用術語，請提供簡短定義或上下文說明

            2. **條理分段清楚**
               - 使用重點列表、定義、步驟或分類方式呈現
               - 讓讀者能快速掌握整體結構

            3. **適度舉例說明**
               - 可結合「{course_name_str}」的學習情境或工程實務案例輔助理解

            4. **內容完整但不偏離主題**
               - 補充必要背景知識，但不延伸至非核心內容

            5. **學術且客觀的語氣**
               - 維持正式、清楚、理性、教學導向的表達方式

            6. **禁止加入開頭導言**
                - 不要出現任何課程開場白或導入語句
                    （例如：「歡迎加入本課程」、「本講義將介紹」、「本章節將說明」等）
                - 回答必須**直接從概念說明開始**

            7. **回答起始格式限制**
                - 回答開頭不得包含寒暄、導言或背景描述
                - 第一行必須直接為：
                    - 定義
                    - 重點標題
                    - 或問題核心說明
            """

        user_message_content = f"核心知識：{context_str}\n使用者問題：{refined_query}"

        full_answer = ""
        try:
            response = rag_runtime.gemini_model.generate_content(
                f"{base_system_prompt}\n{user_message_content}",
                stream=True
            )
            for chunk in response:
                if chunk.text:
                    full_answer += chunk.text
                    yield chunk.text
            
            if warning_suffix and "與本課程無關" not in full_answer and len(full_answer) > 10:
                full_answer += warning_suffix
                yield warning_suffix

            is_rejection = "與本課程無關" in full_answer
            if len(full_answer) > 10 and not is_rejection:
                followup_ctx = context_str if docs else "無(GPT生成模式)"
                follow_up = generate_and_review_followup(refined_query, full_answer, followup_ctx)
                if follow_up:
                    followup_data = json.dumps({"type": "follow_up", "content": follow_up}, ensure_ascii=False)
                    yield f"\n{followup_data}"
            else:
                follow_up = None

            background_tasks.add_task(self.save_record, session_id=session_id, course_id=course_id, query=query, refined_query=refined_query, answer=full_answer, user_id=user.user_id, follow_up_question=follow_up)
        except Exception as e:
            yield f"生成錯誤: {str(e)}"

rag_service = RAGService()
