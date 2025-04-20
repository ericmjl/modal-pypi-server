"""Deploy the pypi server."""

import modal
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("pypiserver[passlib]")
    .apt_install("apache2-utils")
)

app = modal.App(name="pypiserver")

data_volume = modal.Volume.from_name("pypiserver-data", create_if_missing=True)
credentials_volume = modal.Volume.from_name(
    "pypiserver-credentials", create_if_missing=True
)

auth_scheme = HTTPBearer()


@app.function(
    image=image,
    volumes={"/data/packages": data_volume, "/credentials": credentials_volume},
)
@modal.web_server(8080)
def server():
    """Run the pypi server."""
    import subprocess

    subprocess.Popen(
        "pypi-server run -a 'download, list, update' -p 8080 /data/packages -P /credentials/.htpasswd",  # noqa: E501
        shell=True,
    )


@app.function(
    image=image,
    volumes={"/credentials": credentials_volume},
    secrets=[modal.Secret.from_name("pypi-auth-token")],
)
@modal.fastapi_endpoint(docs=True)
async def register_user(
    username: str,
    password: str,
    # request: Request,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """Register a new user."""
    import os
    import subprocess
    from pathlib import Path

    print(os.environ["AUTH_TOKEN"])

    if token.credentials != os.environ["AUTH_TOKEN"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    htpasswd_path = Path("/credentials/.htpasswd")

    # Check if .htpasswd file exists
    if htpasswd_path.exists():
        # Append user to existing file (use -b for batch mode)
        cmd = f"htpasswd -b /credentials/.htpasswd {username} {password}"
    else:
        # Create new file with first user (use -c to create file)
        cmd = f"htpasswd -c -b /credentials/.htpasswd {username} {password}"
    subprocess.Popen(
        cmd,
        shell=True,
    )
