## Background
FastAPI project using PostgreSQL and async SQLAlchemy.
Auth is handled via JWT. All endpoints return Pydantic schemas.

## Examples
Input:  'get user by id'
Output: async def get_user(user_id: int, db: AsyncSession) -> UserSchema: ...

## Constraints
- Always use async/await
- No raw SQL, use ORM only
- Return Pydantic-serialisable types
- Max function length: 30 lines