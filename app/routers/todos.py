from fastapi import Depends, HTTPException, status, APIRouter
from app.database import get_db
from app.schemas.todo import TodoCreate, TodoUpdate, TodoResponse, TodoListResponse
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user
from app.models.todo import Todo
from app.models.user import User
from sqlalchemy import select

router = APIRouter(prefix="/todos", tags=["Todos"])

@router.get("/", response_model=TodoListResponse)
async def get_todos(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Todo).where(Todo.owner_id==current_user.id))
    todos = list(result.scalars().all())
    return TodoListResponse(items=todos, total=len(todos))

@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todos_by_id(todo_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.owner_id==current_user.id))
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return todo

@router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(data: TodoCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    todo = Todo(
        title=data.title,
        description=data.description,
        owner_id=current_user.id,
        category_id=data.category_id,
    )

    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo

@router.put("/{todo_id}", response_model=TodoResponse, status_code=status.HTTP_200_OK)
async def update_todo(todo_id: uuid.UUID, data: TodoUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.owner_id==current_user.id))
    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    update_todo = data.model_dump(exclude_unset=True)
    for key, value in update_todo.items():
        setattr(todo, key, value)

    await db.commit()
    await db.refresh(todo)
    return todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.owner_id==current_user.id))
    todo_for_delete = result.scalar_one_or_none()

    if todo_for_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    await db.delete(todo_for_delete)
    await db.commit()

