"""Handle everything related to the state endpoint

The state route will support two methods, both of
which will have specific works
"""

from uuid import uuid4
from fastapi.param_functions import Depends
from pymongo import MongoClient
from simber import Logger
from pydantic import BaseModel, parse_obj_as
from fastapi import APIRouter, Header, HTTPException
from typing import Dict, List
from jwt.exceptions import DecodeError

from utils.repostatus import SessionState
from utils.github import get_username, get_repos_authenticated
from routers.repo_handler import Repo
from utils.auth_handler import get_jwt_content
from config import get_settings


logger = Logger("state_handler")
router = APIRouter()

REPOSTATUSDB_URI = get_settings().repostatusdb_uri

client = MongoClient(REPOSTATUSDB_URI)
db = client.repostatus


class State(BaseModel):
    state: str


class UserRepo(BaseModel):
    state: str
    username: str
    repos: List[Repo] = []


def create_state() -> str:
    """Create a session state that will be unique.

    Once the state is created, store it in the database
    and return it to the user.
    """
    unique_state = str(uuid4())
    session_state = SessionState(
        state=unique_state
    )

    if hasattr(session_state, "id"):
        delattr(session_state, "id")

    db.sessionstate.insert_one(session_state.dict(by_alias=True))

    return State(state=unique_state)


def get_user_and_repo(jwt_data: Dict) -> UserRepo:
    """Extract the content from the jwt passed and accordingly
    find the username and repo of the user and return.

    if the token is wrong, raise an exception.
    """
    # The jwt_data should contain one field with the state
    # We will use this state to extract the rest of the data
    if "state" not in jwt_data:
        raise HTTPException(status_code=206, detail="Not enough data")

    session_state = db.sessionstate.find_one({"state": jwt_data["state"]})

    if session_state is None:
        raise HTTPException(status_code=404, detail="Invalid state passed")

    # Parse the data into SessionState
    session_state = parse_obj_as(SessionState, session_state)

    if session_state.token is None:
        raise HTTPException(status_code=400,
                            detail="OAuth not yet done for the state")

    # Finally we should have the token.
    # Use the token to get the username
    token = session_state.token
    username_extracted = get_username(token)
    repos = get_repos_authenticated(token)

    user_repo = UserRepo(
        state=jwt_data["state"],
        username=username_extracted,
        repos=repos
    )

    return user_repo


def get_authorization_header(authorization: str = Header(None)):
    """Verify if the authorization header is passed or not"""
    if authorization is None:
        raise HTTPException(status_code=401, detail="No token passed")
    return authorization


@router.get("", response_model=State)
def get_state():
    state = create_state()
    return state


@router.post("", response_model=UserRepo)
def get_content(authorization: str = Depends(get_authorization_header)):
    try:
        content = get_jwt_content(authorization)
        user_repo = get_user_and_repo(content)
        return user_repo
    except DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")
