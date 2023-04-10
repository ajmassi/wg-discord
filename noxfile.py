import os
import tempfile
from typing import Any

import nox
from nox.sessions import Session

"""
Credit to this article: https://cjolowicz.github.io/posts/hypermodern-python-03-linting/#managing-dependencies-in-nox-sessions-with-poetry
"""

PYTHON_VERSION = "3.11"

nox.options.reuse_existing_virtualenvs = True
locations = "."


@nox.session(python=PYTHON_VERSION)
def tests(session: Session) -> None:
    # install_with_constraints(session, "pytest")
    session.run("poetry", "install")
    session.run("pytest")


@nox.session(python=PYTHON_VERSION)
def isort(session: Session) -> None:
    args = session.posargs or locations
    # install_with_constraints(session, "isort")
    session.run("poetry", "install")
    session.run("isort", *args)


@nox.session(python=PYTHON_VERSION)
def flake8(session: Session) -> None:
    args = session.posargs or locations
    # install_with_constraints(session, "flake8")
    session.run("poetry", "install")
    session.run("flake8", *args)


@nox.session(python=PYTHON_VERSION)
def black(session: Session) -> None:
    args = session.posargs or locations
    # install_with_constraints(session, "black")
    session.run("poetry", "install")
    session.run("black", *args)


@nox.session(python=PYTHON_VERSION)
def bandit(session: Session) -> None:
    session.run("poetry", "install")
    session.run("bandit", "-c", "pyproject.toml", "--recursive", ".")
