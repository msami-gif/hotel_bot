from fastmcp import FastMCP
from pydantic import BaseModel
from hotel_service import AmadeusHotelService

# Create your MCP server instance
mcp = FastMCP(name="Hotel Booking MCP Server")

amadeus_service = AmadeusHotelService.AmadeusHotelService()

# Define the parameters model for your tool
class SearchHotelParams(BaseModel):
    city_code: str
    check_in: str
    check_out: str
    adults: int

# Use the decorator to register your tool on the MCP instance
@mcp.tool(
    name="search_hotel",
    description="Search hotels using Amadeus SDK",
    # parameters=SearchHotelParams,
)
def search_hotel(city_code: str, check_in: str, check_out: str, adults: int):
    # Here, call your actual Amadeus SDK function (async or sync wrapped)
    offers = amadeus_service.search_hotels_by_city(city_code, check_in, check_out, adults)
    return offers

if __name__ == "__main__":
    mcp.run(transport="http", port=9000)

