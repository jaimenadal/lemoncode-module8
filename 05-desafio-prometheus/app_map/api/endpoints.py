from fastapi import APIRouter

router = APIRouter()

@router.get("/api/items/")
async def get_items():
    items = [
        {"name": "Foo1", "description": None, "price": "12", "tax": None},
        {"name": "Foo2", "description": None, "price": "13", "tax": None},
        {"name": "Foo3", "description": None, "price": "15", "tax": None}
    ]
    return items
