# PyPI Server Deployment Explained

This document provides a detailed explanation of how the Modal-based PyPI server deployment works. It follows the [Diátaxis documentation framework](https://diataxis.fr/), which separates documentation into tutorials, how-to guides, explanations, and reference material.

## What is the PyPI Server?

The PyPI server is a private Python Package Index that allows you to host and distribute your own Python packages within your organization or team. This implementation uses [Modal](https://modal.com/) as a serverless deployment platform and provides basic authentication for secure package management.

## How the Deployment Works

The deployment is defined in `deployments/pypi_deploy.py` and consists of several key components:

### 1. Base Image Configuration

```python
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("pypiserver[passlib]")
    .apt_install("apache2-utils")
)
```

This code sets up a Debian Slim container with Python 3.12 and installs:

- `pypiserver[passlib]`: The PyPI server implementation with password hashing capabilities
- `apache2-utils`: Provides the `htpasswd` utility for managing user credentials

### 2. Modal App and Volume Configuration

```python
app = modal.App(name="pypiserver")

data_volume = modal.Volume.from_name("pypiserver-data", create_if_missing=True)
credentials_volume = modal.Volume.from_name(
    "pypiserver-credentials", create_if_missing=True
)
```

This section:

- Creates a Modal app named "pypiserver"
- Sets up two persistent volumes:
  - `pypiserver-data`: Stores the actual Python packages
  - `pypiserver-credentials`: Stores the `.htpasswd` file containing user credentials

When Modal creates these volumes (if they don't exist), they persist across deployments. This means your packages and user credentials are preserved even when you update the application code.

### 3. PyPI Server Function

```python
@app.function(
    image=image,
    volumes={"/data/packages": data_volume, "/credentials": credentials_volume},
)
@modal.web_server(8080)
def server():
    """Run the pypi server."""
    import subprocess

    subprocess.Popen(
        "pypi-server run -a 'download, list, update' -p 8080 /data/packages -P /credentials/.htpasswd",
        shell=True,
    )
```

This function:

- Mounts the volumes at `/data/packages` and `/credentials`
- Exposes a web server on port 8080
- Runs the PyPI server with these operations requiring authentication:
  - `download`: Authentication required to download packages
  - `list`: Authentication required to list available packages
  - `update`: Authentication required to upload/update packages
- Points to the package storage at `/data/packages`
- Uses HTTP Basic Authentication with credentials from `/credentials/.htpasswd`

Modal handles all the infrastructure needed to expose this as a public web service, so there's no need to manage servers, URLs, or domain names.

### 4. User Registration Endpoint

```python
@app.function(
    image=image,
    volumes={"/credentials": credentials_volume},
    secrets=[modal.Secret.from_name("pypi-auth-token")],
)
@modal.fastapi_endpoint(docs=True)
async def register_user(
    username: str,
    password: str,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """Register a new user."""
    # Implementation details...
```

This FastAPI endpoint provides an API for registering new users. It:

- Requires an admin authentication token for security
- Takes a username and password as parameters
- Creates or updates the `.htpasswd` file with the new user credentials
- Provides a simple way for administrators to add users without direct access to the server

The admin token is stored as a Modal secret, ensuring it's not hardcoded in your source code.

## Continuous Deployment with GitHub Actions

To ensure the PyPI server is always up-to-date with the latest code changes, this project includes a GitHub Actions workflow for continuous deployment. The workflow is defined in `.github/workflows/deploy-modal.yaml`:

```yaml
name: CI/CD

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    env:
      MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
      MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Install the latest version of uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
          enable-cache: true

      - name: Deploy
        run: |
          uvx modal deploy deployments/pypi_deploy.py
```

### How the CI/CD Pipeline Works

1. **Trigger**: The workflow is triggered automatically whenever code is pushed to the `main` branch.

2. **Environment Setup**:
   - The workflow runs on an Ubuntu latest runner.
   - It uses GitHub Secrets to securely store and access Modal authentication tokens.
   - The `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` are essential for authenticating with Modal's API.

3. **Code Checkout**:
   - The workflow checks out the latest version of the repository code.

4. **Tool Installation**:
   - It installs the latest version of [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.
   - Caching is enabled to speed up subsequent workflow runs.

5. **Deployment**:
   - The workflow uses `uvx modal deploy` to deploy the PyPI server application to Modal.
   - The `deployments/pypi_deploy.py` script is the entry point for deployment.

### Benefits of Continuous Deployment

- **Automation**: Code changes are automatically deployed without manual intervention.
- **Consistency**: Every deployment uses the same process, reducing human error.
- **Auditability**: Deployment history is tracked in GitHub Actions logs.
- **Security**: Sensitive credentials are stored as GitHub Secrets, not in the code.

## Security Considerations

The deployment includes these security measures:

1. **HTTP Basic Authentication**: Users must provide a username and password to access the PyPI server
2. **Admin Token Authentication**: A separate token is required to register new users
3. **Persistent Volumes**: Credentials and packages are stored in persistent Modal volumes
4. **Limited Permissions**: The PyPI server is configured to allow only specific operations
5. **Secret Management**: Sensitive credentials are stored in Modal secrets and GitHub Secrets

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     GitHub Repository                       │
│                                                            │
│  ┌─────────────┐    ┌────────────────┐                     │
│  │ Source Code │───>│ GitHub Actions │                     │
│  └─────────────┘    └────────┬───────┘                     │
└───────────────────────────────│──────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────┐
│                      Modal Platform                        │
│                                                           │
│  ┌─────────────────┐       ┌──────────────────┐          │
│  │   PyPI Server   │◄──────│  CI/CD Pipeline  │          │
│  │    Function     │       └──────────────────┘          │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐    ┌─────────────────────┐         │
│  │ User Register   │    │     Modal Secrets   │         │
│  │    Endpoint     │◄───│  (AUTH_TOKEN, etc.) │         │
│  └────────┬────────┘    └─────────────────────┘         │
│           │                                              │
│  ┌────────▼────────┐    ┌─────────────────────┐         │
│  │ Package Volume  │    │ Credentials Volume  │         │
│  └─────────────────┘    └─────────────────────┘         │
└───────────────────────────────────────────────────────────┘
```

## When to Use This

This deployment is suitable for:

- Teams or organizations that need to host private Python packages
- Situations where you need quick setup of a private PyPI server
- Environments where serverless deployment is preferred over managing infrastructure
- Projects that benefit from continuous deployment of infrastructure changes

For high-security or high-volume production environments, consider additional security measures like HTTPS and more robust authentication mechanisms.
