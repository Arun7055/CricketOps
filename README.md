# 🏏 CricketOps: Real-Time Auction & Analytics Simulator

CricketOps is a high-performance, full-stack cricket auction simulator and analytics dashboard. Designed to replicate the intense, fast-paced environment of a live franchise draft, the platform combines a robust real-time bidding engine with deep, data-driven scouting reports backed by a custom ETL pipeline and LLM-generated insights.

## 🚀 Live Environments
* **Frontend (Next.js):** [[Insert Vercel URL](https://cricket-ops.vercel.app/)]
* **Backend (FastAPI):** [[Insert Render URL](https://cricketops.onrender.com)]

---

## ⚡ Deep Dive: Core Features

### 1. The Real-Time Auction Engine
The main feature of the platform is the live bidding arena, engineered for zero-latency synchronization across multiple connected clients.
* **WebSocket Synchronization:** A continuous, bi-directional `wss://` connection ensures that the current player on the block, the highest bidder, and the active purse balances are updated instantly for all users in the lobby.
* **Concurrency & Race Condition Handling:** Built with **RabbitMQ**, the backend queues incoming bids. If two users bid at the exact same millisecond, the message broker ensures they are processed sequentially, preventing database race conditions and double-spending.
* **Host-Controlled Draft Flow:** Secure lobby creation dictates that only the room creator can initialize the draft and control the progression, ensuring a structured draft environment.
* **Live Constraint Validations:** The backend actively rejects bids if a franchise attempts to exceed their max squad size (e.g., 25 players) or outbid their remaining purse balance.

### 2. The Player Analytics Lab
A comprehensive scouting dashboard that aggregates historical data into actionable, visual insights.
* **360° DNA Radar:** Visualizes a player's core archetype (Batting SR, Average, Boundary %, Economy, Bowling SR) normalized onto a 0-100 scale using custom math algorithms, rendered beautifully via Recharts.
* **Multi-Year Trajectory Streams:** Parses raw JSON match data from 2018–2025 to create a dynamic, year-by-year timeline. Users can toggle between:
  * **Batting Volume:** Runs scored (Bars) vs. Strike Rate (Line).
  * **Bowling Pressure:** Wickets taken (Bars) vs. Economy Rate (Line).
* **Fielding Agility Stack:** A dedicated stacked bar chart visualizing total career fielding contributions (Catches, Stumpings).
* **LLM Scouting Reports:** Features in-depth, Wikipedia-scraped and Groq API-generated `cricbuzz_profile` and `injury_profile` narratives for all 210 players.

### 3. Post-Draft Squad Analytics
The moment the final player is sold, the lobby is seamlessly routed to an automated post-auction analysis dashboard.
* **Purse Efficiency Metrics:** Calculates how effectively each franchise utilized their budget vs. the actual output of the players acquired.
* **Dynamic Squad Balance Grids:** Visualizes the roster construction, breaking down the squad into precise roles (Top Order, All-Rounders, Pace, Spin) to identify gaps.
* **Premium Buy Highlights:** Automatically isolates and flags the highest-impact and most expensive acquisitions of the draft.


### 4. AI-Driven Cricket News Feed
To keep the ecosystem immersive, the platform includes a dynamic news generation engine.
* **Contextual Storytelling:** Leverages the Groq LLM API to generate realistic, in-universe news articles, injury updates, and draft rumors, adding a layer of unpredictability and narrative to the scouting phase.

---

## 🏗️ System Architecture & Tech Stack

* **Frontend:** Next.js, React, Tailwind CSS, Recharts (Deployed on Vercel)
* **Backend:** Python, FastAPI, Uvicorn (Deployed on Render)
* **Database:** PostgreSQL (Neon DB), SQLAlchemy ORM, Alembic Migrations
* **Real-Time Engine:** WebSockets, RabbitMQ (Message Queue), `aio-pika`
* **Data Pipeline:** Python (Pandas, Numpy), Groq (LLM)

## 📊 The Data Pipeline (ETL)
The player database is built on a highly customized data generation pipeline:
1. **Base Dataset:** A core CSV containing 210 players with base attributes (Name, Role, Batting Style, Bowling Style) was imported into a Neon DB PostgreSQL table.
2. **LLM Enrichment:** We utilized the **Groq API** paired with Wikipedia scraping to dynamically generate comprehensive, realistic scouting profiles for the entire roster.
3. **Statistical Aggregation:** Raw JSON match data spanning from 2018 to 2025 was processed, accumulated, and normalized using Pandas to feed the REST endpoints that power the Player Lab.

---
