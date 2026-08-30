"""
GitHub OAuth flow.

Flow:
1. Frontend redirects user to GET /api/auth/github/login
2. We redirect to GitHub's authorize URL
3. GitHub redirects back to /api/auth/github/callback with a `code`
4. We exchange the code for an access token, fetch the GitHub user,
   create/find our User + Company, encrypt+store the token, and
   issue our own JWT session token back to the frontend.
"""
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, encrypt_token
from app.models.models import Company, User

router = APIRouter(prefix="/api/auth/github", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/login")
async def github_login():
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
        "scope": "repo read:user user:email",
    }
    return RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        # Step 1: exchange code for access token
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
            },
        )
        token_data = token_resp.json()
        github_token = token_data.get("access_token")
        if not github_token:
            raise HTTPException(status_code=400, detail="GitHub OAuth failed")

        # Step 2: fetch GitHub user profile
        user_resp = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {github_token}"},
        )
        gh_user = user_resp.json()

    email = gh_user.get("email") or f"{gh_user['login']}@users.noreply.github.com"

    # Find or create the user's company + user record
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # First-time login: create a company + user together (MVP: 1 user -> 1 company)
        company = Company(name=gh_user.get("name") or gh_user["login"], slug=gh_user["login"].lower())
        db.add(company)
        await db.flush()  # get company.id before creating user

        user = User(
            company_id=company.id,
            email=email,
            full_name=gh_user.get("name"),
            role="admin",
        )
        db.add(user)

    user.github_access_token = encrypt_token(github_token)
    await db.commit()
    await db.refresh(user)

    session_token = create_access_token(subject=str(user.id))
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={session_token}"
    return RedirectResponse(redirect_url)
