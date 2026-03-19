import json
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime
import random
import string

# RAG / Vector DB 相關
from qdrant_client import models
from app.providers.quiz_runtime import quiz_runtime
from app.repositories.quiz_repository import quiz_repository

# 引入 Model 和 Schema
from app.schemas.quiz import QuizCreateRequest

class QuizService:
    def __init__(self):
        self.runtime = quiz_runtime
        # 配置 Gemini

    def _search_quiz_context(self, topic: str, course_id: str, selected_files: List[str], k: int = 5) -> str:
        try:
            file_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="filename",
                        match=models.MatchAny(any=selected_files)
                    )
                ]
            )

            dense_vec = self.runtime.dense_model.embed_query(topic)
            sparse_res = list(self.runtime.sparse_model.embed([topic]))[0]
            sparse_vec = models.SparseVector(
                indices=sparse_res.indices.tolist(),
                values=sparse_res.values.tolist()
            )

            results = self.runtime.qdrant_client.query_points(
                collection_name=course_id.lower(),
                prefetch=[
                    models.Prefetch(query=sparse_vec, using="sparse", filter=file_filter, limit=k),
                    models.Prefetch(query=dense_vec, using="dense", filter=file_filter, limit=k),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=k
            )

            docs = [hit.payload["page_content"] for hit in results.points]
            return "\n\n".join(docs) if docs else "無法在選定的檔案中找到相關內容。"

        except Exception as e:
            print(f"❌ Quiz 搜尋失敗: {e}")
            return "搜尋發生錯誤，請依據主題自行發揮。"

    def generate_quiz_draft(self, topic: str, course_id: str, selected_files: List[str], difficulty: str):
        print(f"📝 [Quiz] 正在生成問答題... (Course: {course_id}, Topic: {topic})")

        context_str = self._search_quiz_context(topic, course_id, selected_files)

        # Prompt 文字保持不變
        system_prompt = f"""
        你是一位大學教授。請根據使用者提供的【指定教材】，設計一份包含 **5 題問答題 (Essay Questions)** 的測驗卷。

        設定：
        - 難度：{difficulty}
        - 主題：{topic}

        【指定教材內容】
        {context_str}

        請輸出 JSON 格式，結構如下 (不需要提供標準答案)：
        {{
            "questions": [
                {{
                    "question": "題目內容...",
                    "grading_criteria": "列出評分重點 (例如：提到 A 概念得 5 分)"
                }},
                ... (共 5 題，每個題目總分為10分，不能過少或超過)
            ]
        }}
        """

        try:
            # 使用 Gemini 生成 JSON
            response = self.runtime.gemini_model.generate_content(
                system_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ Gemini 生成失敗: {e}")
            raise e

    def create_quiz(self, db: Session, req: QuizCreateRequest):
        while True:
            access_code = "".join(random.choices(string.digits, k=6))
            if not quiz_repository.access_code_exists(db, access_code):
                break

        final_title = req.title
        if not final_title or final_title.strip() == "":
             final_title = datetime.now().strftime("%Y-%m-%d 測驗")

        questions_data = [q.model_dump() for q in req.questions]

        return quiz_repository.create_quiz(
            db,
            course_id=req.course_id,
            title=final_title,
            source_files=req.source_files,
            questions_content=questions_data,
            access_code=access_code,
        )

    def grade_quiz(self, access_code: str, student_id: str, student_answers: List[str], db: Session):
        quiz = quiz_repository.get_by_access_code(db, access_code)
        if not quiz:
            raise ValueError(f"quiz code '{access_code}' not exist")

        existing_submission = quiz_repository.get_submission(db, quiz.quiz_id, student_id)
        if existing_submission:
            raise ValueError(f"該學生以記錄過一次,無法重複回答")

        if len(student_answers) != len(quiz.questions_content):
            raise ValueError(f" DB題目數量: {len(quiz.questions_content)} 實際收到: {len(student_answers)}")

        results = []
        passed_count = 0
        for idx, (q_data, answer) in enumerate(zip(quiz.questions_content, student_answers)):
            question_text = q_data.get("question", "")
            grading_criteria = q_data.get("grading_criteria", "")
            grade_result = self._grade_single_question(
                question=question_text,
                grading_criteria=grading_criteria,
                student_answer=answer
            )

            result_status = grade_result["result"]
            if result_status == "pass":
                passed_count += 1

            results.append({
                "question": question_text,
                "student_answer": answer,
                "result": result_status
            })

        quiz_repository.create_submission(
            db,
            quiz_id=quiz.quiz_id,
            student_id=student_id,
            student_answers=student_answers,
            results=results,
            passed_count=passed_count,
            total_count=len(quiz.questions_content),
        )

        return {
            "quiz_id": quiz.quiz_id,
            "title": quiz.title,
            "results": results
        }

    def _grade_single_question(self, question: str, grading_criteria: str, student_answer: str) -> dict:
        # Prompt 文字保持不變
        system_prompt = f"""
你是一位批改助手，請嚴格按照【評分標準】計算學生答案的得分。

【題目】
{question}

【評分標準】
{grading_criteria}

【學生答案】
{student_answer}

【批改規則】
1. 每題滿分 10 分
2. **嚴格按照評分標準給分**：逐項檢查學生答案是否符合評分標準中的各個得分點，符合就給該項的分數
3. 空白答案一律 0 分
4. 不要自行發揮，只按評分標準判斷

請計算總得分。

**輸出 JSON 格式：**
{{
    "score": 數字 (0-10)
}}
"""

        try:
            # 使用 Gemini 生成 JSON
            response = self.runtime.gemini_model.generate_content(
                system_prompt,
                generation_config={"response_mime_type": "application/json"}
            )

            result = json.loads(response.text)
            score = result.get("score", 0)
            if not isinstance(score, (int, float)):
                score = 0
            score = max(0, min(10, score))

            result["result"] = "pass" if score >= 6 else "not pass"
            result["score"] = score
            return result

        except Exception as e:
            print(f"Gemini error: {e}")
            return {"result": "not pass", "score": 0}

quiz_service = QuizService()
