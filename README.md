# Supply Chain Operations Insight Platform with Local RAG Assistant

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django&logoColor=white">
  <img alt="Pandas" src="https://img.shields.io/badge/Pandas-Data%20Engineering-150458?style=for-the-badge&logo=pandas&logoColor=white">
  <img alt="Chart.js" src="https://img.shields.io/badge/Chart.js-Dashboards-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white">
  <img alt="Scikit-learn" src="https://img.shields.io/badge/scikit--learn-Local%20RAG-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  <img alt="Render" src="https://img.shields.io/badge/Render-Ready-46E3B7?style=for-the-badge&logo=render&logoColor=000000">
  <img alt="Neon" src="https://img.shields.io/badge/Neon-Postgres%20Ready-00E599?style=for-the-badge&logo=neon&logoColor=000000">
</p>

<p align="center">
  <strong>Django analytics platform for supply-chain KPI engineering, operational dashboards, research experiments, and a local report-grounded RAG assistant.</strong>
</p>

Local Django portfolio project for extracting business insights from operational and supply-chain data. It uses SQLite, pandas, Chart.js, Django authentication, a simple experiment-tracking module, and a local TF-IDF RAG assistant over generated reports.

The project runs locally and in Docker. Render and Neon configuration files are included for deployment readiness only; no deployment is performed automatically. Google Cloud, Firebase production auth, OpenAI API, LangChain, ChromaDB, and paid external APIs are not used.

## Portfolio Highlights

| Area | What This Project Shows |
| --- | --- |
| Data engineering | ZIP ingestion, recursive CSV detection, column normalization, cleaning, and feature generation |
| Business analytics | Revenue, profit, late delivery risk, country, region, category, and shipping-mode KPIs |
| Full-stack Django | Local auth, management commands, models, forms, templates, JSON endpoints, and SQLite metadata storage |
| Visualization | Bootstrap dashboard with Chart.js charts powered by Django API endpoints |
| AI/RAG | Local scikit-learn retrieval over generated business reports with no paid API key |
| Research workflow | Experiment creation, participant responses, condition summaries, and CSV export |
| Deployment readiness | Docker local testing plus Render and Neon configuration for a later manual deployment |

## Why This Matches A GRA Supply-Chain / Business-Insights Role

This project demonstrates practical research-assistant skills:

- Data collection workflow from a raw ZIP dataset.
- Data cleaning, column normalization, and resilient metric generation.
- Supply-chain KPI design for revenue, profit, delivery risk, region, category, and shipping mode.
- Django full-stack development with local authentication and SQLite.
- Front-end dashboarding with Bootstrap and Chart.js.
- Local AI-style retrieval using scikit-learn TF-IDF instead of external APIs.
- Experiment tracking for research studies and decision-support evaluation.

## Dataset Placement

You can upload the DataCo SMART Supply Chain ZIP from the app's **Data Pipeline** page after logging in.

You can also place the ZIP file manually inside:

```text
Dataset/
```

If more than one ZIP file is present, the app uses the largest ZIP file.

## Workflow

```text
ZIP dataset upload or Dataset/ placement
  -> extract into extracted_data/
  -> detect main supply-chain CSV recursively
  -> clean and normalize operational data
  -> export cleaned_supply_chain_data.csv
  -> generate KPI JSON and business report
  -> create local RAG documents
  -> show dashboards, order samples, reports, experiments, and chatbot
```

## Folder Structure

```text
supply_chain_operations_platform/
    Dataset/
    extracted_data/
    outputs/
        cleaned_supply_chain_data.csv
        business_kpi_summary.json
        generated_business_report.md
        rag_documents/
            kpi_summary.txt
            dataset_dictionary.txt
            operational_insights.txt
            experiment_notes.txt
    supplychain_platform/
    analytics/
    experiments/
    Dockerfile
    docker-compose.yml
    render.yaml
    Procfile
    runtime.txt
    .env.example
    README.md
    requirements.txt
    manage.py
```

In this workspace, the current folder is the project root.

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Local Commands

Run these from the project root:

```bash
python manage.py migrate
python manage.py extract_dataset
python manage.py process_supply_chain_data
python manage.py seed_demo_user
python manage.py smoke_test_app
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Demo login:

```text
username: admin
password: admin123
```

This demo user is for local development only.

## Run With Docker

Docker support is for local testing. The Docker setup still uses SQLite unless you explicitly provide a `DATABASE_URL`.

Build the image:

```bash
docker compose build
```

Start the app:

```bash
docker compose up
```

Open:

```text
http://127.0.0.1:8000/
```

The Docker container runs:

- database migrations
- static file collection
- Gunicorn on port `8000`

The compose setup mounts the project folder into the container, so local files such as `db.sqlite3`, `Dataset/`, `outputs/`, and `extracted_data/` remain available for local testing.

Useful Docker checks:

```bash
docker compose ps
```

```bash
docker compose logs web
```

Health check endpoint:

```text
http://127.0.0.1:8000/health/
```

Stop the app:

```bash
docker compose down
```

## Render And Neon Deployment Readiness

This repository includes deployment-readiness files only:

- `render.yaml`
- `Procfile`
- `runtime.txt`

Do not put real secrets in source code. Add production secrets only in the Render dashboard.

### 1. Push Code To GitHub

Create a GitHub repository, then run these commands from the project root:

```bash
git init
git add .
git commit -m "Prepare Django app for Render and Neon"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

The `.gitignore` file keeps local-only files out of GitHub, including `.env`, `.venv/`, `db.sqlite3`, dataset ZIP files, extracted raw CSVs, `staticfiles/`, and the cleaned raw output CSV.

### 2. Create A Free Neon Postgres Database

In Neon:

1. Create a new project on the free plan.
2. Open the database connection details.
3. Copy the PostgreSQL connection string.
4. Keep the connection string private.

Use the Neon connection string as the `DATABASE_URL` value in Render.

### 3. Create A Render Web Service

In Render:

1. Create a new **Web Service**.
2. Connect the GitHub repository.
3. Select the Python runtime.
4. Use this build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

5. Use this start command:

```bash
python manage.py migrate && gunicorn supplychain_platform.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

6. Set the health check path:

```text
/health/
```

### 4. Add Render Environment Variables

Add these in the Render dashboard:

```text
SECRET_KEY=<generate a secure Django secret key in Render>
DEBUG=False
ALLOWED_HOSTS=<your-render-service-name>.onrender.com
DATABASE_URL=<your Neon PostgreSQL connection string>
PYTHON_VERSION=3.11.11
```

Optional:

```text
CSRF_TRUSTED_ORIGINS=https://<your-render-service-name>.onrender.com
```

The app automatically falls back to SQLite when `DATABASE_URL` is not set, so local development remains unchanged.

### 5. After The First Render Build

After Render finishes the first build, use the Render shell only if you need to seed the demo account:

```bash
python manage.py seed_demo_user
```

If you want cloud demo data, upload the dataset ZIP from the **Data Pipeline** page and process it there. Render free services use an ephemeral filesystem, so uploaded raw files and generated local output files should be treated as demo-only unless you add persistent storage later.

No Render deployment is started from this README. These steps are for you to run manually when ready.

### Render Docker Runtime

If you select **Docker** as the Render runtime, leave Render's **Docker Command** field empty. The `Dockerfile` already starts the app with migrations, demo-user seeding, static file collection, and Gunicorn bound to Render's `PORT` variable.

Use these settings:

```text
Runtime: Docker
Branch: main
Root Directory: leave blank
Dockerfile Path: ./Dockerfile
Docker Command: leave blank
```

## KPI Formulas

- Revenue = existing sales/order total column when available, otherwise quantity x product price.
- Profit = existing profit/benefit column when available, otherwise 0 with a report limitation.
- Profit Margin = profit / revenue when revenue is greater than 0.
- Delivery Delay = real shipping days - scheduled shipping days.
- Late Delivery Rate = late orders / total orders x 100.

If a metric cannot be calculated from available columns, the app records a limitation and uses safe local fallbacks instead of crashing.

## Dashboard

The dashboard includes:

- Total Revenue
- Total Orders
- Late Delivery Rate
- Average Delivery Delay
- Top Category
- Best Region
- Monthly Revenue Trend
- Revenue by Category
- Late Delivery Rate by Region
- Shipping Mode Performance
- Top 10 Countries by Revenue

Charts fetch JSON from Django endpoints and render with Chart.js.

## Local RAG Assistant

The assistant reads only files in:

```text
outputs/rag_documents/
```

It uses `TfidfVectorizer` from scikit-learn, retrieves the top matching chunks, and answers from those generated documents. It does not use OpenAI, LangChain, ChromaDB, or external APIs.

If the generated reports do not contain enough evidence, it returns:

```text
I could not find enough information in the generated reports to answer that confidently.
```

Example questions:

- Which region has the highest late delivery rate?
- What product category generates the most revenue?
- What are the main operational risks?
- How can the company reduce late deliveries?
- Which shipping mode has the highest order volume?
- Summarize the monthly revenue trend.
- What recommendations does the report provide?

## Experiment Module

Researchers can:

- Create an experiment with a research question.
- Define control and treatment conditions.
- Add participant responses manually.
- Capture decision, confidence score, response time, and notes.
- View condition-level summaries.
- Export responses as CSV.

This supports lightweight studies on whether operational dashboards or AI summaries improve supply-chain decision-making.

