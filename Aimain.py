import os
import json
import logging
import sqlite3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elysia-ai")

app = FastAPI(title="ELYSIA AI", version="0.1.0")

# Database initialization
DB_PATH = "elysia.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_logs (
            id TEXT PRIMARY KEY,
            interaction_type TEXT,
            raw_payload TEXT,
            summary TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class PreferenceUpdate(BaseModel):
    key: str
    value: str

@app.get("/")
def read_root():
    web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>ELYSIA Core Frontend Not Found</h1>", status_code=404)

@app.get("/health")
def health_check():
    return {"status": "online", "system": "ELYSIA Core", "version": "0.1.0"}

@app.post("/v1/preferences")
def update_preference(pref: PreferenceUpdate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)", (pref.key, pref.value))
    conn.commit()
    conn.close()
    return {"status": "success", "key": pref.key}

@app.get("/v1/preferences")
def get_preferences():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_preferences")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

@app.websocket("/v1/cognitive/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to ELYSIA stream.")
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event = payload.get("event")
            
            # Simple agent decision-making simulator
            if event == "message":
                user_msg = payload.get("text", "")
                logger.info(f"User message received: {user_msg}")
                
                # Mock reasoning stages
                await websocket.send_json({
                    "event": "cognitive_state",
                    "state": "thinking",
                    "detail": "Analyzing message intent and checking memory logs..."
                })
                
                # Record to episodic memory in SQLite
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                import uuid
                cursor.execute(
                    "INSERT INTO episodic_logs (id, interaction_type, raw_payload, summary) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), "text", user_msg, f"User asked: {user_msg[:50]}")
                )
                conn.commit()
                conn.close()
                
                # Generate ELYSIA personality response
                response_text = f"I'm here, analyzing your command. You said: '{user_msg}'. Let me coordinate that task for you."
                
                await websocket.send_json({
                    "event": "cognitive_state",
                    "state": "responding",
                    "detail": "Formulating natural language audio response"
                })
                
                await websocket.send_json({
                    "event": "message",
                    "text": response_text,
                    "avatar_state": "speaking"
                })
            else:
                await websocket.send_json({
                    "event": "info",
                    "text": f"Unrecognized event payload: {event}"
                })
    except WebSocketDisconnect:
        logger.info("Client disconnected from ELYSIA stream.")
