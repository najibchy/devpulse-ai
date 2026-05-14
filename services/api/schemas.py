
from pydantic import BaseModel


class GithubUser(BaseModel):
    login: str


class GithubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    owner: GithubUser


class GithubPullRequest(BaseModel):
    number: int
    title: str
    html_url: str
    user: GithubUser
    base: dict
    head: dict
    state: str


class WebhookPayload(BaseModel):
    action: str
    pull_request: GithubPullRequest
    repository: GithubRepo


class PRResponse(BaseModel):
    message: str
    pr_id: int
    task_id: str


class HealthResponse(BaseModel):
    status: str
    service: str
