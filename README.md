# DutchRentScope

DutchRentScope is a comprehensive tool for analyzing the Dutch rental market, helping users better understand and navigate rental opportunities in the Netherlands. The tool primarily focuses on scraping housing data from websites like Funda using Playwright for browser simulation.

## Features

- **Web Scraping**: Automated data collection from housing websites
  - Support for both rental and sales listings
  - Detailed page crawling capability
  - Configurable image downloading
- **Multiple Cities Support**: Ability to scrape data from multiple cities simultaneously
- **Flexible Data Storage**: Save data in CSV format or directly to a database
- **Customizable Image Quality**: Multiple image size options for different needs
- **Browser Simulation**: Uses Playwright for reliable web scraping

## Prerequisites

- Python 3.x
- Playwright
- PostgreSQL (optional, for database storage)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Blickwinkle262/DutchRentScope.git
cd DutchRentScope

## Getting Started

pip install -r requirements.txt

## Install Playwright

playwright install

## Run Cralwer

python main.py --search_areas Amsterdam --end 3
python main.py --search_areas [cities] --end [number] [additional options]


Argument	Description	Options
--search_areas	Cities to search (multiple allowed)	e.g., Amsterdam Rotterdam
--end	Number of pages to crawl	Integer value
--crawl_type	Type of crawling	listing or detail
--download_img	Whether to download images	True or False
--img_size	Image size to download	large (1440x960), medium (720x480), small (360x240)
--save_option	Data storage method	csv or db
```
