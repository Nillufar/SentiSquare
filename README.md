# SentiLearn 🇰🇷
A Korean language–learning platform that uses AI to simplify news articles for different TOPIK (Test of Proficiency in Korean) levels.

## Features

- **Multi-level Article Simplification**  
  Articles simplified for all TOPIK levels (1–6)

- **Automatic Translation**  
  English translations generated for each simplified version

- **Sentiment Analysis** across four dimensions:  
  - Positive / Negative tone  
  - Technical vs. General content  
  - Social vs. Individual focus  
  - Educational vs. Entertainment value

- **Vocabulary Lists**  
  Essential vocabulary extracted per TOPIK level

- **Category Organization**  
  Articles organized into curated learning domains:  
  - Startup Knowledge  
  - Fashion & K-Beauty  
  - Economics  
  - International Relations  
  - Legal Issues for Businesses

- **URL Import**  
  Import articles directly from Korean news websites

---

## Prerequisites

- Python 3.13+
- [Ollama](https://ollama.ai) installed and running locally
- A suitable Korean-capable model installed in Ollama  
  (e.g., `llama3.2:latest` or similar)

---

## Installation

1. Clone the repository and navigate into the project directory.

2. Install dependencies:
   ```bash
   uv sync
