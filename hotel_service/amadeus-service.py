from amadeus import Client, ResponseError
import os
from datetime import datetime, timedelta
import re 

class AmadeusHotelService:
    def __init__(self):
        self.amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

    def search_hotel_offers(self, hotel_id, adults, check_in_date, check_out_date):
        try:
            response = self.amadeus.shopping.hotel_offers_search.get(
                hotelIds=hotel_id,
                adults=adults,
                checkInDate=check_in_date,
                checkOutDate=check_out_date
            )
            return response.data
        except ResponseError as error:
            print(f"Error searching hotel offers: {error}")
            return None