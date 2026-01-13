from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware # cors để dashboard call được

from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import logging
from .dantri_crawler import DantriCrawler
from .analyzer import NewsAnalyzer

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Khởi tạo FastAPI app
app = FastAPI(
    title="Serperior News Crawler API",
    description="REST API để thu thập tin tức từ Dân Trí",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # allow all host to calll
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Pydantic models cho response
class ArticleResponse(BaseModel):
    date: str
    title: str
    body: str
    url: str

class CrawlResponse(BaseModel):
    success: bool
    message: str
    total_articles: int
    data: List[ArticleResponse]

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    success: bool
    error: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    success: bool
    error: Optional[str] = None

# Danh sách các field hợp lệ
VALID_FIELDS = ['kinh-doanh', 'thoi-su', 'phap-luat', 'du-lich', 'bat-dong-san']

# Phần áp dụng thuật toán trong hustack: Week 1 - Extract Year, Month, Date from a String YYYY-MM-DD
def validate_date_format(date_str: str) -> bool:
    """Kiểm tra định dạng ngày YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_date_range(start_date: str, end_date: str) -> bool:
    if len(start_date) != 10 or start_date[4] != '-' or start_date[7] != '-':
        return False
    if len(end_date) != 10 or end_date[4] != '-' or end_date[7] != '-':
        return False
    # Tách start_date
    start_parts = start_date.split('-')
    if len(start_parts) != 3:
        return False
    sy, sm, sd = start_parts
    # Kiểm tra start_date có phải toàn số không
    if not (sy.isdigit() and sm.isdigit() and sd.isdigit()):
        return False
    # Kiểm tra độ dài các phần của start_date
    if not (len(sy) == 4 and len(sm) == 2 and len(sd) == 2):
        return False
    # Tách end_date
    end_parts = end_date.split('-')
    if len(end_parts) != 3:
        return False
    ey, em, ed = end_parts
    # Kiểm tra end_date có phải toàn số không
    if not (ey.isdigit() and em.isdigit() and ed.isdigit()):
        return False
    # Kiểm tra độ dài các phần của end_date
    if not (len(ey) == 4 and len(em) == 2 and len(ed) == 2):
        return False
    # Chuyển sang số nguyên
    start_y, start_m, start_d = int(sy), int(sm), int(sd)
    end_y, end_m, end_d = int(ey), int(em), int(ed)
    # Kiểm tra tháng và ngày hợp lệ
    if not (1 <= start_m <= 12 and 1 <= start_d <= 31):
        return False
    if not (1 <= end_m <= 12 and 1 <= end_d <= 31):
        return False
    # So sánh: start_date >= end_date
    if start_y > end_y:
        return True
    elif start_y == end_y:
        if start_m > end_m:
            return True
        elif start_m == end_m:
            if start_d >= end_d:
                return True
    
    return False

@app.get("/")
async def root():
    
    return {
        "message": "Serperior News Crawler API",
        "version": "1.0.0",
        "endpoints": {
            "crawl": "/api/v1/crawl",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

from .vector_db import ArticleVectorDB

# Initialize Vector DB
vector_db = None
try:
    vector_db = ArticleVectorDB()
except Exception as e:
    logger.error(f"Failed to initialize Vector DB: {e}")

# Initialize RAG and LLM
from ..rag.rag_service import RAGService
from ..rag.llm_client import LLMClient
import os

rag_service = None
llm_client = None

try:
    if vector_db:
        rag_service = RAGService(vector_db)
        # Use env var if available, else rely on manual set or error later
        gemini_key = os.getenv("GEMINI_API_KEY") 
        if not gemini_key:
             raise ValueError("GEMINI_API_KEY not found in environment variables")
             
        llm_client = LLMClient(provider="gemini", api_key=gemini_key)
except Exception as e:
    logger.error(f"Failed to initialize RAG/LLM: {e}")

@app.get("/api/v1/crawl", response_model=CrawlResponse)
async def crawl_news(
    start_date: str = Query(..., description="Ngày bắt đầu (định dạng YYYY-MM-DD)", example="2024-12-16"),
    end_date: str = Query(..., description="Ngày kết thúc (định dạng YYYY-MM-DD)", example="2024-12-15"),
    field: str = Query("kinh-doanh", description=f"Lĩnh vực tin tức. Các giá trị hợp lệ: {', '.join(VALID_FIELDS)}", example="kinh-doanh"),
    num_articles: int = Query(5, ge=1, le=20, description="Số bài báo tối đa mỗi ngày (1-20)", example=5),
    save_to_db: bool = Query(True, description="Save crawled articles to database")
):

    if not validate_date_format(start_date):
        raise HTTPException(status_code=400, detail=f"Định dạng start_date không hợp lệ. Vui lòng dùng 'YYYY-MM-DD'. Nhận được: {start_date}")
    
    if not validate_date_format(end_date):
        raise HTTPException(status_code=400, detail=f"Định dạng end_date không hợp lệ. Vui lòng dùng 'YYYY-MM-DD'. Nhận được: {end_date}")
    
    if not validate_date_range(start_date, end_date):
        raise HTTPException(status_code=400, detail=f"start_date ({start_date}) phải >= end_date ({end_date})")

    if field not in VALID_FIELDS:
        raise HTTPException(status_code=400, detail=f"Field không hợp lệ. Các giá trị cho phép: {', '.join(VALID_FIELDS)}")
    
    try:
        logger.info(f"Bắt đầu crawl: field={field}, start={start_date}, end={end_date}, num={num_articles}")
        
        crawler = DantriCrawler(field=field, max_workers=5)
        
        results = crawler.crawl_by_date_range(
            start_date=start_date,
            end_date=end_date,
            num_articles=num_articles,
            save=False
        )
        
        if results is None:
            results = []
        
        logger.info(f"Crawl thành công: {len(results)} bài báo")

        if save_to_db and vector_db and results:
            try:
                count = vector_db.add_articles(results)
                logger.info(f"Saved {count} articles to database")
            except Exception as e:
                logger.error(f"Error saving to database: {e}")
        
        return CrawlResponse(
            success=True,
            message=f"Crawl thành công {len(results)} bài báo",
            total_articles=len(results),
            data=results
        )
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    
    except Exception as e:
        logger.error(f"Lỗi khi crawl: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi server khi crawl: {str(e)}")

@app.get("/api/v1/fields")
async def get_valid_fields():
    """Lấy danh sách các field hợp lệ"""
    return {
        "valid_fields": VALID_FIELDS,
        "descriptions": {
            "kinh-doanh": "Kinh doanh",
            "thoi-su": "Thời sự",
            "phap-luat": "Pháp luật",
            "du-lich": "Du lịch",
            "bat-dong-san": "Bất động sản"
        }
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )

@app.post("/api/v1/export/csv")
async def export_to_csv(
    articles: List[Dict] = Body(..., description="Danh sách bài báo cần export")
):
    """
    Export danh sách bài báo ra file CSV
    """
    try:
        if not articles:
            raise HTTPException(status_code=400, detail="No articles to export")
        
        import pandas as pd
        from datetime import datetime
        
        df = pd.DataFrame(articles)
        df = df.sort_values(by="date", ascending=False)
        
        # Tạo tên file với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dantri_export_{timestamp}.csv"
        
        # Lưu file
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return {
            "success": True,
            "message": f"Exported {len(articles)} articles",
            "filename": filename
        }
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# http://localhost:8000/api/v1/crawl?start_date=2024-12-20&end_date=2024-12-18&field=thoi-su&num_articles=3
analyzer = NewsAnalyzer()

@app.post("/api/v1/analyze/entity")
async def analyze_entity(
    articles: List[Dict] = Body(..., description="Danh sách bài báo cần phân tích")
):
    try:
        logger.info(f"Analyzing sentiment for {len(articles)} articles")
        
        result = analyzer.extract_entities_from_articles(articles)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/v1/analyze/full")
async def full_analysis(
    start_date: str = Query(...),
    end_date: str = Query(...),
    field: str = Query("kinh-doanh"),
    num_articles: int = Query(5, ge=1, le=20),
    reset_db: bool = Query(False, description="Clear database before crawling")
):
    """
    Crawl + Phân tích đầy đủ.
    If reset_db=True, clears DB first.
    Optimization: Checks DB first. If articles exist for range, use them. Else crawl and save.
    """
    try:
        articles = []
        is_cached = False
        
        # Step 0: Clear DB if requested
        if reset_db and vector_db:
            logger.info("Resetting database as requested.")
            vector_db.clear()

        # Step 1: Check DB (only if not reset)
        if vector_db and not reset_db:
            try:
                # Naive check: if we find *any* articles in this range, we assume we have data
                # A better approach would be to check if we have enough data or data for each day
                db_articles = vector_db.get_articles_by_date(start_date, end_date)
                if db_articles:
                    logger.info(f"Found {len(db_articles)} articles in DB. Using cached data.")
                    articles = db_articles
                    is_cached = True
            except Exception as e:
                logger.error(f"DB check failed: {e}")

        # Step 2: Crawl if not cached
        if not articles:
            logger.info(f"Full analysis: Data not in DB. Crawling...")
            crawler = DantriCrawler(field=field)
            articles = crawler.crawl_by_date_range(start_date, end_date, num_articles, save=False)
            
            # Save to DB for future use
            if vector_db and articles:
                vector_db.add_articles(articles)
        
        if not articles:
            return {
                "success": False,
                "message": "No articles found"
            }
        
        # Step 2: Analyze entity
        logger.info(f"Full analysis: Analyzing trend...")
        entity_result = analyzer.extract_entities_from_articles(articles)

        logger.info(f"Full analysis: Analyzing sentiment...")
        sentiment_result = None
        
        trend_result = analyzer.analyze_trend(articles)

        return {
            "success": True,
            "data": {
                "source": "database" if is_cached else "crawler",
                "articles": articles,
                "entity": entity_result,
                "trend": trend_result,
                "sentiment": sentiment_result
            }
        }
    except Exception as e:
        logger.error(f"Error in full analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the RAG system
    """
    try:
        if not rag_service or not llm_client:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        query = request.message
        
        # 1. Retrieve Context
        context = rag_service.retrieve_context(query)
        sources = []
        if context:
            # Quick parse to extract sources for UI (optional, naive parsing)
            lines = context.split('\n')
            for line in lines:
                if line.startswith("Source"):
                    sources.append(line)

        # 2. Format Prompt
        messages = rag_service.format_prompt(query, context)
        
        # 3. Generate Answer
        answer = llm_client.generate_answer(messages)
        
        return ChatResponse(
            success=True,
            response=answer,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return ChatResponse(
            success=False,
            response="Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu của bạn.",
            error=str(e)
        )