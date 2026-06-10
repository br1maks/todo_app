import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Category).where(Category.id == current_user.id))
    return list(result.scalars().all())

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def crearte_category(data: CategoryCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    category = Category(name=data.name, owner_id=current_user.id)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_current_user), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Category).where(Category.id == category_id, Category.owner_id == current_user.id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.commit()