# Q-Commerce Price Comparison Tool 🛒

An automated price comparison system that scrapes bread product data from three major quick commerce platforms (Zepto, JioMart, Amazon Fresh) and presents pricing insights through an interactive dashboard.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Components](#components)
- [Data Flow](#data-flow)
- [Dashboard Features](#dashboard-features)
- [Requirements](#requirements)

## 🎯 Overview

This project automates the process of comparing bread prices across 3 quick commerce platforms. It scrapes product information, matches identical products across platforms, calculates price differences, and presents actionable insights through an interactive Streamlit dashboard.

**Key Capabilities:**
- Scrapes 20-30+ bread products per platform (60-90+ total)
- Intelligent product matching across platforms
- Unit price calculation (price per 100g)
- Interactive filtering and search
- Automated data pipeline with dashboard integration

## ✨ Features

### Scraping
- **Multi-platform scraping**: Zepto, JioMart, Amazon Fresh
- **Dynamic content handling**: Selenium-based with scroll simulation
- **Smart filtering**: Excludes non-bread items (knives, toasters, etc.)
- **Comprehensive data extraction**: Product name, brand, weight, price, URL

### Data Processing
- **Intelligent cleaning**: Removes duplicates, handles missing values
- **Product matching**: Uses similarity scoring and keyword matching
- **Unit price calculation**: Normalizes prices to per-100g basis
- **Weight extraction**: Parses weight from product descriptions

### Analytics Dashboard
- **Interactive visualizations**: Plotly-powered charts and graphs
- **Advanced filtering**: By platform, brand, and price range
- **Product search**: Real-time search with instant results
- **Price comparison**: Side-by-side platform comparisons
- **Savings identification**: Highlights best deals

## 📁 Project Structure

```
qcommerce-price-comparison/
│
├── scraper/
│   └── scraper.py              # Web scraping logic
│
├── preprocess/
│   └── preprocess.py           # Data cleaning and matching
│
├── dashboard.py                # Streamlit dashboard
│
├── data/
│   ├── bread_products.csv      # Raw scraped data
│   ├── processed_products.csv  # Cleaned product data
│   ├── processed_matched.csv   # Matched products
│   ├── processed_price_comparison.csv
│   ├── processed_platform_summary.csv
│   └── processed_brand_summary.csv
│
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for Selenium)
- ChromeDriver (automatically managed by Selenium 4.6+)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/Jenisa-Merlin/Q-Commerce_Price_Comparison.git
cd Q-Commerce_Price_Comparison
```

2. **Create virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create data directory**
```bash
mkdir data
```

## 📖 Usage

### Method 1: Run Complete Pipeline

```bash
# 1. Scrape data from all platforms
python scraper/scraper.py

# 2. Process and match products
python preprocess/preprocess.py

# 3. Launch dashboard
streamlit run ui/dashboard.py
```

### Method 2: Use Dashboard Controls

1. Launch the dashboard:
```bash
streamlit run ui/dashboard.py
```

2. Use the sidebar buttons:
   - **Run Scraper**: Scrape fresh data
   - **Run Preprocess**: Process and match products
   - **Refresh Data**: Reload dashboard with latest data

3. The dashboard will open in your browser at `http://localhost:8501`


## 🔧 Components

### 1. Scraper (`scraper.py`)

**Key Classes:**
- `BreadScraper`: Main scraping orchestrator
- `Product`: Data structure for product information

**Key Methods:**
- `scrape_zepto()`: Scrapes Zepto website
- `scrape_jiomart()`: Scrapes JioMart website
- `scrape_amazon_fresh()`: Scrapes Amazon Fresh
- `scrape_all()`: Runs all scrapers sequentially

**Features:**
- Headless Chrome with anti-detection measures
- Dynamic content loading with scroll simulation
- Intelligent product filtering
- Regex-based price and weight extraction
- Brand recognition from 35+ known brands

### 2. Preprocessor (`preprocess.py`)

**Key Classes:**
- `DataPreprocessor`: Main data processing pipeline

**Key Methods:**
- `clean_data()`: Removes duplicates, handles missing values
- `calculate_unit_price()`: Computes price per 100g
- `match_products()`: Finds identical products across platforms
- `compare_prices()`: Calculates price differences and savings
- `run_full_pipeline()`: Executes complete preprocessing workflow

**Matching Algorithm:**
- String similarity scoring (SequenceMatcher)
- Keyword overlap analysis
- Weight matching (within 10% tolerance)
- Brand validation
- Combined scoring threshold (default: 0.7)

### 3. Dashboard (`dashboard.py`)

**Tabs:**

1. **Overview**
   - Price distribution by platform
   - Unit price comparison
   - Brand analysis
   - Platform comparison matrix

2. **Best Deals**
   - Top savings opportunities
   - Top 10 deals table
   - Savings visualization

3. **Price Analysis**
   - Price vs weight scatter plot
   - Platform statistics
   - Best price frequency analysis

4. **Product Search**
   - Real-time search functionality
   - Side-by-side price comparisons
   - Detailed product information

5. **Platform Summary**
   - Aggregate platform statistics
   - Brand summary table

**Interactive Features:**
- Multi-select filters (platform, brand)
- Price range slider
- Dynamic metric cards
- Exportable data tables

## 🔄 Data Flow

```
┌─────────────┐
│   Scraper   │  Scrapes Zepto, JioMart, Amazon Fresh
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ bread_products  │  Raw scraped data
│     .csv        │
└──────┬──────────┘
       │
       ▼
┌──────────────┐
│ Preprocessor │  Cleans, matches, calculates
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│  Processed CSVs     │  5 output files
│  - products         │
│  - matched          │
│  - price_comparison │
│  - platform_summary │
│  - brand_summary    │
└──────┬──────────────┘
       │
       ▼
┌──────────────┐
│  Dashboard   │  Interactive visualization
└──────────────┘
```

## 📊 Dashboard Features

### Key Metrics
- **Total Products**: Count of unique products in filtered view
- **Matched Products**: Number of products matched across platforms
- **Average Savings**: Mean potential savings per product
- **Total Savings**: Sum of all potential savings

### Visualizations
1. **Price Distribution Bar Chart**: Compare average prices by platform
2. **Unit Price Box Plot**: Analyze price per 100g variations
3. **Brand Analysis**: Top brands by product count and average price
4. **Comparison Matrix**: Heatmap of platform price competitiveness
5. **Savings Chart**: Horizontal bar chart of top savings opportunities
6. **Scatter Plot**: Price vs weight analysis
7. **Pie Chart**: Best price frequency by platform

### Filters
- **Platform**: Multi-select (Zepto, JioMart, Amazon Fresh)
- **Brand**: Multi-select from available brands
- **Price Range**: Slider for min/max price filtering

## 📦 Requirements

```txt
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.17.0
selenium>=4.15.0
```

**System Requirements:**
- RAM: 4GB minimum, 8GB recommended
- Storage: 100MB for application and data
- Internet: Stable connection for scraping

## 👥 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Email: 21pw08@psgtech.ac.in

