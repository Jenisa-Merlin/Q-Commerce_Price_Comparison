Problem 1: Quick Commerce Price Comparison
Objective
Build an automated price comparison tool that scrapes product data of all breads
available from three quick commerce platforms and presents insights on pricing patterns.
Task
Write a Python script that:
1. Scrapes bread product information (product name, brand, weight/size, price)
from three quick commerce websites of your choice
2. Matches identical products across platforms
3. Compares pricing
4. Presents findings in either:
○ An interactive dashboard (using Plotly, Streamlit, or similar), OR
○ A well-formatted Google Sheet with summary statistics and insights
Key Requirements
● Clean, well-documented Python code with comments
● Proper error handling for failed requests or missing data
● Include at least 20-30 bread products per platform
● Identify price differences and flag best deals
Deliverables
1. Python script with clear instructions to run
2. Output (dashboard link or Google Sheet link)
3. Brief summary of methodology and key insights
4. requirements.txt file listing dependencies
Notes
● Implement rate limiting
● If a site blocks scraping, document your approach and pivot accordingly
● You may use libraries like BeautifulSoup, Scrapy, Selenium, or Playwright
● Bonus points for automated scheduling or alerts for price change