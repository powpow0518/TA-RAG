import os
import sys
import shutil
import uuid
import traceback
import time
import re
import zipfile
import tarfile
import datetime
from typing import List, Optional, Set
import hashlib

from dotenv import load_dotenv
load_dotenv()

os.environ["SCARF_NO_ANALYTICS"] = "true"

# --- LangChain & RAG ---
from langchain_community.document_loaders import (
    PyMuPDFLoader,              # 專讀 PDF
    Docx2txtLoader,             # 專讀 Word
    UnstructuredPowerPointLoader, # 專讀 PPT
    UnstructuredExcelLoader,    # 專讀 Excel
    CSVLoader,                  # 專讀 CSV
    TextLoader,                 # 專讀 txt/md
    DirectoryLoader
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed import SparseTextEmbedding

# --- Database ---
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, Session

# 讓腳本能找到 app 資料夾內的 model
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models.rag import SourceDocument, Base
from app.models.course import Course
from app.models.user import User

from app.core.config import settings


# 建立資料庫連線
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("⚠️ 警告: 找不到 DATABASE_URL，嘗試使用預設值")
    db_url = "postgresql://demo_user:demo_password@db:5432/ta_rag"

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 設定區塊 ---
DOWNLOAD_PATH = "./downloads"
ARCHIVE_PATH = "./archive"
STAGING_PATH = "./staging"

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

VECTOR_SIZE = 1024
EMBEDDING_MODEL_NAME = "voyage-3"
RETENTION_PERIOD_YEARS = 3

def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def clean_text_for_postgres(text: str) -> str:
    return text.replace('\x00', '') if text else text

def secure_basename(path_from_zip: str) -> str:
    name = os.path.basename(path_from_zip)
    if len(name) > 1 and name[1] == ':': name = name[2:]
    name = name.lstrip('/\\')
    if name in ['.', '..']: return ''
    return name

def parse_and_save_course_metadata(filename: str, db: Session) -> str:
    base_name = os.path.splitext(filename)[0]
    cleaned_name = re.sub(r'_\d{8}$', '', base_name)
    pattern = re.compile(r'^(\d{3})(\d{1})(.*?)\[(\d+)\].*?$')
    match = pattern.match(cleaned_name)

    if match:
        year, semester, raw, code = match.groups()
        raw_name = raw.strip()
        standard_id = f"{year}{semester}{code}"
        display_semester = f"{year}-{semester}"

        try:
            existing = db.query(Course).filter_by(course_id=standard_id).first()
            if not existing:
                db.add(Course(course_id=standard_id, course_name=raw_name, semester=display_semester, course_code=code))
            else:
                existing.course_name = raw_name
                existing.semester = display_semester
                existing.course_code = code
            db.commit()
            return standard_id
        except Exception as e:
            db.rollback()
            print(f"❌ 儲存 Course metadata 失敗: {e}")
            return standard_id
    else:
        print(f"⚠️ 檔名格式不符，使用原檔名: {cleaned_name}")
        return cleaned_name

# --- 核心邏輯：單一 壓縮檔 處理流程 ---
def process_single_archive(filename: str):
    print(f"\n📦 [開始處理] {filename}")

    archive_path = os.path.join(DOWNLOAD_PATH, filename)
    db = SessionLocal()

    # 1. 解析檔名並建立資料庫 Course 紀錄
    course_id = parse_and_save_course_metadata(filename, db)
    db.close()

    # 2. 解壓縮 -> Staging
    extract_path = os.path.join(STAGING_PATH, course_id)
    if os.path.exists(extract_path): shutil.rmtree(extract_path)
    os.makedirs(extract_path)

    try:
        if filename.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    try: decoded = member.filename.encode('cp437').decode('big5')
                    except: decoded = member.filename
                    safe_name = secure_basename(decoded)
                    if not safe_name: continue
                    target = os.path.join(extract_path, safe_name)
                    if member.is_dir() or target.startswith(os.path.join(extract_path, '__MACOSX')): continue
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zip_ref.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        elif filename.endswith('.tar'):
            with tarfile.open(archive_path, 'r') as tar_ref:
                tar_ref.extractall(path=extract_path)
    except Exception as e:
        print(f"❌ 解壓失敗，跳過此檔案: {e}")
        return

    # 3. 同步資料庫 (Sync DB)
    try:
        changed = sync_single_course_db(course_id, extract_path)

        # 4. 重建向量 (Rebuild Vector)
        if changed:
            rebuild_vector_index_for_course(course_id)
        else:
            print(f"  💤 資料無變動。")

    except Exception as e:
        print(f"❌ 處理課程內容時發生錯誤: {e}")
        traceback.print_exc()

    # 5. 清理 Staging (釋放空間)
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)

    # 6. 移動 Archive
    try:
        os.makedirs(ARCHIVE_PATH, exist_ok=True)
        shutil.move(archive_path, os.path.join(ARCHIVE_PATH, filename))
    except Exception as e:
        print(f"移動存檔失敗: {e}")

def sync_single_course_db(course_id: str, course_path: str) -> bool:
    db: Session = SessionLocal()
    has_changes = False
    try:
        db_docs = db.query(SourceDocument).filter_by(course_id=course_id).all()
        db_files_map = {doc.file_name: doc.content_hash for doc in db_docs}

        staging_files_map = {}
        for root, dirs, files in os.walk(course_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel_name = os.path.relpath(fpath, course_path)
                staging_files_map[rel_name] = file_sha256(fpath)

        to_delete = set(db_files_map.keys()) - set(staging_files_map.keys())
        if to_delete:
            db.query(SourceDocument).filter(SourceDocument.course_id == course_id, SourceDocument.file_name.in_(to_delete)).delete(synchronize_session=False)
            has_changes = True

        for rel_name, fhash in staging_files_map.items():
            if rel_name in db_files_map and db_files_map[rel_name] == fhash: continue

            fpath = os.path.join(course_path, rel_name)
            loader = None
            ext = rel_name.lower()
            if ext.endswith('.pdf'): loader = PyMuPDFLoader(fpath)
            elif ext.endswith('.docx'): loader = Docx2txtLoader(fpath)
            elif ext.endswith('.txt') or ext.endswith('.md'): loader = TextLoader(fpath, encoding="utf-8")
            elif ext.endswith('.csv'): loader = CSVLoader(fpath, encoding="utf-8")
            elif ext.endswith('.xlsx') or ext.endswith('.xls'): loader = UnstructuredExcelLoader(fpath)
            elif ext.endswith('.pptx') or ext.endswith('.ppt'):
                try: loader = UnstructuredPowerPointLoader(fpath)
                except: continue

            if not loader: continue

            try:
                docs = loader.load()
                raw = "\n\n".join(d.page_content for d in docs if d.page_content)
                full = clean_text_for_postgres(raw)
                if not full.strip(): continue

                existing = db.query(SourceDocument).filter_by(course_id=course_id, file_name=rel_name).first()
                now = datetime.datetime.utcnow()

                if existing:
                    existing.content = full
                    existing.content_hash = fhash
                    existing.last_modified = now
                else:
                    db.add(SourceDocument(course_id=course_id, file_name=rel_name, content=full, content_hash=fhash, last_modified=now))
                has_changes = True
                print(f"    ✅ 已讀取: {rel_name}")
            except Exception as e:
                print(f"    ❌ 讀取失敗 {rel_name}: {e}")

        db.commit()
        return has_changes
    finally:
        db.close()

def rebuild_vector_index_for_course(course_id: str):
    db: Session = SessionLocal()
    qdrant = QdrantClient(url=QDRANT_URL, timeout=60)

    try:
        dense_model = VoyageAIEmbeddings(model=EMBEDDING_MODEL_NAME, batch_size=128)
        sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

        collection = course_id.lower()
        try: qdrant.delete_collection(collection)
        except: pass

        qdrant.create_collection(
            collection_name=collection,
            vectors_config={"dense": models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE)},
            sparse_vectors_config={"sparse": models.SparseVectorParams(index=models.SparseIndexParams(on_disk=False))}
        )

        docs = db.query(SourceDocument).filter_by(course_id=course_id).all()
        if not docs: return

        all_texts, all_metas = [], []
        for d in docs:
            all_texts.append(d.content)
            all_metas.append({"filename": d.file_name})

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.create_documents(all_texts, metadatas=all_metas)

        chunk_texts = [c.page_content for c in chunks]
        chunk_metas = [c.metadata for c in chunks]

        if not chunk_texts: return

        dense_vecs = dense_model.embed_documents(chunk_texts)
        sparse_vecs = list(sparse_model.embed(chunk_texts))

        points = []
        for i, (txt, meta, dense, sparse) in enumerate(zip(chunk_texts, chunk_metas, dense_vecs, sparse_vecs)):
            points.append(models.PointStruct(
                id=i,
                payload={"page_content": txt, "filename": meta.get("filename"), "source": meta.get("filename")},
                vector={"dense": dense, "sparse": sparse.as_object()}
            ))

        batch_size = 100
        for i in range(0, len(points), batch_size):
            qdrant.upsert(collection_name=collection, points=points[i:i+batch_size], wait=True)

        print(f"    ✅ 向量重建完成 ({course_id})")

    except Exception as e:
        print(f"❌ 向量處理失敗: {e}")
    finally:
        db.close()

def cleanup_outdated_courses():
    db: Session = SessionLocal()
    qdrant = QdrantClient(url=QDRANT_URL, timeout=60)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=RETENTION_PERIOD_YEARS * 365)
    try:
        courses = db.query(Course).all()
        for c in courses:
            last_mod = db.query(func.max(SourceDocument.last_modified)).filter_by(course_id=c.course_id).scalar()
            if last_mod and last_mod < cutoff:
                print(f"🚨 課程 {c.course_id} 已過期，執行刪除...")
                try: qdrant.delete_collection(c.course_id.lower())
                except: pass
                db.query(SourceDocument).filter_by(course_id=c.course_id).delete()
                db.delete(c)
                db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    os.makedirs(STAGING_PATH, exist_ok=True)
    os.makedirs(ARCHIVE_PATH, exist_ok=True)

    # 支援 .zip 與 .tar
    archives = [f for f in os.listdir(DOWNLOAD_PATH) if f.endswith('.zip') or f.endswith('.tar')]

    if not archives:
        print("沒有新檔案需要處理。")
    else:
        print(f"發現 {len(archives)} 個新檔案，開始處理...")
        for archive in archives:
            process_single_archive(archive)

    cleanup_outdated_courses()
    if os.path.exists(STAGING_PATH): shutil.rmtree(STAGING_PATH)
    print("\n✅ 所有任務完成！")
