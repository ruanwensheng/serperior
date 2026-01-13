# Serperior -  News & RAG System
![React App and 4 more pages - Personal - Microsoft_ Edge 2026-01-13 21-44-04 (1)](https://github.com/user-attachments/assets/58e7520f-c86c-45fb-8f78-a8ed2619c23f)

**Serperior** is my tiny tiny project designed to crawl, analyze, and interact with Vietnamese news data (specifically from Dân Trí). It combines automated web scraping, natural language processing (NLP), and Retrieval-Augmented Generation (RAG) so that you can read news in 5 seconds.

##  Key Features

*   **Automated News Crawling**: Fetches articles from *Dân Trí* based on date ranges and categories (Business, Current Events, Law, etc.).
*   **Intelligent Analysis**:
    *   **Entity Extraction**: Identifies key people, organizations, and locations using `UnderTheSea` and `PhoBERT`.
    *   **Sentiment Analysis**: Determines the emotional tone of articles.
    *   **Trend Detection**: Analyzes keyword frequency and emerging topics.
*   **RAG Chat Interface**: 
    *   Chat with your data using **Google Gemini Pro**.
    *   Context-aware answers based on the crawled articles stored in **ChromaDB**.
    *   Source citation for every answer.
*   **Interactive Dashboard**: A modern React frontend to visualize data, control the crawler, and chat with the AI.

##  Technology Stack

### Backend
*   **Framework**: Python `FastAPI`
*   **Database**: `ChromaDB` (Vector Database for semantic search)
*   **AI/LLM**: `Google Gemini` (via `google-generativeai`)
*   **NLP**: `Underthesea`, `PyVi`, `Sentence-Transformers` (Multilingual)
*   **Crawling**: `BeautifulSoup4`, `Requests`

### Frontend
*   **Library**: React.js
*   **Styling**: Modern CSS / Tailwind (inferred)
*   **Visualization**: Charts & Data Tables



##  Project Structure

<img width="2048" height="1250" alt="image" src="https://github.com/user-attachments/assets/ca69044b-11c5-40e0-95c6-7bba2b95a8a7" />


##  Getting Started

### Prerequisites
*   Python 3.10+ (Recommended via Conda)
*   Node.js & npm
*   Google Gemini API Key

### 1. Local Installation

**Backend:**
```bash
cd backend
# Create environment
conda create -n serperior python=3.10
conda activate serperior

# Install dependencies
pip install -r requirements.txt

# Set API Key (Important!)
conda env config vars set GEMINI_API_KEY=<YOUR_EXACT_API_KEY>
# Reactivate to apply
conda deactivate
conda activate serperior

# Run Server
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```
Access the app at `http://localhost:3000`.

### 2. Docker Deployment (Recommended)

Run the entire system with a single command:

1.  Create a `.env` file in the root directory:
    ```
    GEMINI_API_KEY=<YOUR_API_KEY>
    ```
2.  Start services:
    ```bash
    docker-compose up -d --build
    ```
    *   Frontend: `http://localhost`
    *   Backend API: `http://localhost:8000`

##  Usage Guide

1.  **Dashboard**: Use the sidebar to select a date range and news category (e.g., "Kinh doanh").
2.  **Fetch & Analyze**: Click the button to start crawling. The system will fetch articles, process them, and store them in the database.
3.  **View Insights**: Explore the generated charts and word clouds.
4.  **Chat**: Switch to the Chat tab to ask questions like "Tình hình kinh tế Việt Nam tuần qua thế nào?". The AI will answer using facts from the crawled news.

##  Security Note

*   API Keys are managed via environment variables (`GEMINI_API_KEY`).
*   `.env` files are excluded from version control to prevent leaks.
