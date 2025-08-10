from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
class AmadeusHotelService:
    def __init__(self):
        self.amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

    def search_hotels_by_city(self, city_code, check_in_date, check_out_date, adults):
        try:
             # Step 1: Get hotel list by city
            logger.info("Entering search_hotels_by_city with parameters: ")
            hotel_response = self.amadeus.reference_data.locations.hotels.by_city.get(
            cityCode=city_code)
            hotel_ids = [hotel["hotelId"] for hotel in hotel_response.data[:10]]  # limit to 10 for brevity

            if not hotel_ids:
                print("No hotels found in city.")
                return None

            logger.info("Using Amadeus' API to search for hotel offers.")
            offers_response = self.amadeus.shopping.hotel_offers_search.get(
            hotelIds=','.join(hotel_ids),
            checkInDate=check_in_date,
            checkOutDate=check_out_date,
            adults=adults
        )
            return offers_response.data
        except ResponseError as error:
            print(f"[API Error]: {error}")
            return None
