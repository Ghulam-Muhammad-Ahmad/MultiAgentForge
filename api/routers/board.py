from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models import Board, Column
from schemas.common import BoardOut, ColumnOut

router = APIRouter(tags=["board"])


@router.get("/projects/{project_id}/board", response_model=BoardOut)
async def get_board(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Board)
        .where(Board.project_id == project_id)
        .options(
            selectinload(Board.columns).selectinload(Column.tickets)
        )
    )
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(404, "Board not found")
    return board


@router.post("/boards/{board_id}/columns", response_model=ColumnOut, status_code=201)
async def create_column(board_id: str, name: str, position: int, db: AsyncSession = Depends(get_db)):
    import uuid
    col = Column(id=str(uuid.uuid4()), board_id=board_id, name=name, position=position)
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return col


@router.patch("/columns/{column_id}", response_model=ColumnOut)
async def update_column(column_id: str, name: str | None = None, position: int | None = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Column).where(Column.id == column_id))
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(404, "Column not found")
    if name is not None:
        col.name = name
    if position is not None:
        col.position = position
    await db.commit()
    await db.refresh(col)
    return col
