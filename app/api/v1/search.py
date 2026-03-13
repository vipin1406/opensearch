from fastapi import APIRouter
from app.services.search_service import search_products

router = APIRouter()

@router.get("/search")
def search(q: str):

    print("\n========== API LAYER ==========")
    print("Incoming Query:", q)

    results = search_products(q)

    print("Returned Results:", len(results))
    print("================================\n")

    print("\n========== API LAYER ==========")
    print("Incoming Query:",q)
    print("Type:", type(q))
    print("Length:", len(q))
    print("================================")

    return results