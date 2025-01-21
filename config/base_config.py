funda_rules = {
    "energy_level": "",
    "living_area": "",
    "property_agent": "",
    "city": "",
    "bedroom_count": "",
    "street_address": "",
    "monthly_rent": "",
    "postal_code": "",
    "house_price": "",
}
funda_detail_rules = {}
HEADLESS = False

search_date = "20241206"

funda_crawl_type = "basic"

funda_headers = {
    "Host": "listing-search-wonen.funda.io",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Accept": "application/x-ndjson",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.funda.nl/",
    "content-type": "application/x-ndjson",
    "Origin": "https://www.funda.nl",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "Sec-GPC": "1",
    "Priority": "u=4",
    "TE": "trailers",
}
