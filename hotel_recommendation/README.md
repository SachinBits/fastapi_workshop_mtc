# Smart Hotel Recommendation API

Welcome to the **"Smart Recommendation API with FastAPI"** workshop! In this project, we have built a backend system that mimics real-world hotel booking engines.

## Features
- **FastAPI Backend**: High-performance, async-first API framework.
- **Advanced Architecture**:
    - **Middleware**: Custom `ProcessTimeMiddleware` to intercept and time requests.
    - **Dependency Injection**: Reusable logic for Auth (`verify_token`) and Pagination (`pagination_parameters`).
    - **Background Tasks**: Async email simulation for non-blocking user experience.
- **Search & Filter**: Powerful search with multiple criteria and pagination.
- **Admin System**: secure CRUD endpoints for managing hotel data.
- **AI-Powered Reranking**: Uses Google's Gemini API to contextually rank hotels based on detailed descriptions (e.g., "vibes").

## Setup Instructions

### 1. Prerequisites
- Python 3.9+ installed
- Basic understanding of Python and REST APIs

### 2. Installation
Clone the repository and navigate to the folder:
```bash
cd hotel_recommendation
```

Create a virtual environment (optional but recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install dependencies:
```bash
pip install fastapi uvicorn pydantic python-dotenv google-generativeai supabase
```

### 3. Configuration

#### Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

#### Database Setup (Supabase)
1.  Create a new Supabase project.
2.  Go to the **SQL Editor** in the Supabase Dashboard.
3.  Copy and paste the contents of `schema.sql` (found in this repo) to create the `hotels` table.
4.  Run the seed script to populate data:
    ```bash
    python3 seed_db.py
    ```

### 4. Running the Server in Development Mode
Start the local server with live reloading:
```bash
uvicorn main:app --reload
```

## Usage

### Interactive Documentation (Swagger UI)
Open your browser and go to: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
Here you can interactively test all endpoints.

### Professional Frontend
We have included a modern, "Glassmorphism" UI for the project.
Open your browser and visit: **[http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)**

## Endpoints Overview

### Public Endpoints
- **`GET /hotels`**: Search hotels with pagination (`?skip=0&limit=10`).
- **`POST /recommendations`**: AI-powered personalized recommendations.

### Protected / Advanced Endpoints
*Requires header: `x-token: secret-token`*
- **`POST /bookings`**: Simulates booking (triggers Background Task).
- **`POST /admin/hotels`**: Add a hotel.
- **`PUT /admin/hotels/{id}`**: Update hotel price.
- **`DELETE /admin/hotels/{id}`**: Delete a hotel.

## Workshop Concepts Covered
1. **Application Structure**: Modular design (`main`, `logic`, `models`, `db`).
2. **Pydantic**: Data validation (`BookingRequest`, `Hotel`).
3. **Advanced FastAPI**:
    - **Middleware**: Global request processing.
    - **Dependency Injection**: Auth and Query params.
    - **BackgroundTasks**: Async operations.
4. **Hybrid AI**: Combining deterministic rules with LLM creativity (Gemini).
