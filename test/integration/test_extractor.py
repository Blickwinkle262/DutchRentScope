import pytest
from pathlib import Path
from platforms.funda.help import FundaBuyExtractor

# Define the path to the fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_extract_details_from_parking_page():
    """
    Tests that the extractor can handle a "parking" type page,
    extracting the price correctly and gracefully handling the absence of living_area.
    """
    # Load the HTML content from a fixture file
    html_path = FIXTURES_DIR / "parking_sold_7446338.html"
    html_content = html_path.read_text(encoding="utf-8")

    # Initialize the extractor
    extractor = FundaBuyExtractor()

    # Perform the extraction
    house_details = await extractor.extract_details(
        id="7446338", page_content=html_content
    )

    # Assertions
    assert house_details.price == 45000.0
    assert house_details.living_area == 0  # Parking has no living area
    assert house_details.status == "Sold"
