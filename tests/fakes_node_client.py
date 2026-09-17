from __future__ import annotations


class FakeNodeClient:
    def __init__(self):
        self.services = [
            {"_id": "svc1", "name": "Tap & Pipe Leak Repair", "category": "plumbing", "startingPrice": 299},
        ]
        self.professionals = [
            {
                "_id": "prof1",
                "user": {"name": "Ramesh Kumar"},
                "category": "plumbing",
                "rating": 4.5,
                "hourlyRate": 400,
                "location": "Kothrud, Pune",
                "experience": 5,
            }
        ]
        self.customer_bookings = [
            {"_id": "b1", "status": "accepted", "service": {"name": "Tap & Pipe Leak Repair"}, "date": "2026-01-01"}
        ]
        self.cancel_calls: list[str] = []

    async def list_services(self):
        return self.services

    async def list_live_categories(self):
        return sorted({s["category"] for s in self.services})

    async def list_professionals(self, category=None, location=None, available=None):
        return [p for p in self.professionals if not category or p["category"] == category]

    async def get_customer_bookings(self):
        return self.customer_bookings

    async def get_professional_bookings(self):
        return []

    async def cancel_booking(self, booking_id: str):
        self.cancel_calls.append(booking_id)
        for b in self.customer_bookings:
            if b["_id"] == booking_id:
                b["status"] = "cancelled"
                return b
        return {"_id": booking_id, "status": "cancelled"}

    async def update_booking_status(self, booking_id: str, status: str):
        return {"_id": booking_id, "status": status}

    async def decline_booking_request(self, booking_id: str):
        return {"_id": booking_id}
