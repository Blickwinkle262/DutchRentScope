import requests
import json


def search_funda_listings(selected_area="leiden", page_from=60):
    """
    搜索 Funda 房源列表

    Args:
        selected_area (str): 搜索区域，默认为 "leiden"
        page_from (int): 分页起始位置，默认为 60

    Returns:
        dict: API 响应数据
    """
    url = "https://listing-search-wonen.funda.io/_msearch/template"

    # 设置请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Accept": "application/x-ndjson",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.funda.nl/",
        "Content-Type": "application/x-ndjson",
        "Origin": "https://www.funda.nl",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Sec-GPC": "1",
    }

    # 构建请求数据
    common_params = {
        "selected_area": [selected_area],
        "offering_type": "buy",
        "publication_date": {"no_preference": True},
        "availability": ["available", "negotiations"],
        "free_text_search": "",
        "page": {"from": page_from},
        "zoning": ["residential"],
        "type": ["single"],
        "sort": {
            "field": "relevancy_sort_order",
            "order": "desc",
            "offering_type": "both",
            "old_option": "relevance",
        },
        "open_house": {},
    }

    # 构建完整的请求体
    data = (
        '{"index":"listings-wonen-searcher-alias-prod"}\n'
        f'{{"id":"search_result_20241206","params":{json.dumps(common_params)}}}\n'
        '{"index":"listings-wonen-searcher-alias-prod"}\n'
        f'{{"id":"object_type_20241206","params":{json.dumps(common_params)}}}\n'
        '{"index":"listings-wonen-searcher-alias-prod"}\n'
        f'{{"id":"open_house_20241206","params":{json.dumps(common_params)}}}\n'
    )

    try:
        # 发送请求
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()  # 检查响应状态

        # 写入响应到文件
        with open("response.json", "w", encoding="utf-8") as f:
            f.write(response.text)

        # 返回响应数据
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None


# 使用示例
if __name__ == "__main__":
    # 使用默认参数搜索
    result = search_funda_listings()
