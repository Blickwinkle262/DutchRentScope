import asyncio
import copy
import json
import re
from typing import Callable, Dict, List, Optional, Union, Any
from urllib.parse import parse_qs, unquote, urlencode

import httpx
from lxml import etree
from httpx import Response


class FundaRequest:
    def __init__(self):
        pass
