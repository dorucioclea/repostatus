"""Handle internal requests that are to be made in order
to get GitHub related data.
"""

from requests import get
from routers.repo_handler import Repo
from typing import List
from requests import Session

from repostatus.url_handler import URLHandler


def get_username(token: str) -> str:
    """Use the passed token to get the username
    of the user that gave us access.

    This username is necessary because we will need to
    use it along with the repo to get the details.
    """
    HEADERS = {
        "Authorization": "token {}".format(token)
    }
    usernameURL = "https://api.github.com/user"

    response = get(usernameURL, headers=HEADERS)

    if response.status_code != 200:
        return "Not Found"

    return response.json()["login"]


def get_repos_authenticated(token: str) -> List:
    """Get the repo's for the authenticated user using
    the token.
    """
    REPO_URL = "https://api.github.com/user/repos"
    HEADERS = {
        "Authorization": "token {}".format(token),
    }
    PARAMS = {
        "visibility": "all",
        "per_page": 100
    }

    response = get(REPO_URL, headers=HEADERS, params=PARAMS)

    if response.status_code != 200:
        return []

    repos = []
    for repo in response.json():
        repos.append(Repo(
            name=repo["name"],
            full_name=repo["full_name"],
            language=repo["language"],
            stars=repo["stargazers_count"],
            url=repo["html_url"]))

    # Sort on the basis of stars
    repos.sort(reverse=True, key=lambda repo: repo.stars)

    return repos


def is_repo_public(repo: str) -> bool:
    """Check if the passed repo is public or not."""
    check_request = URLHandler(repo).check_request
    response = Session().send(check_request)

    return True if response.status_code == 200 else False
