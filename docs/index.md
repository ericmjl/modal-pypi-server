# Modal PyPI Server

Welcome to the documentation for the Modal PyPI Server! This project allows you to quickly deploy a private PyPI server using Modal's serverless infrastructure.

## Quickstart

### Deploy your PyPI server

```bash
modal deploy deployments/pypi_deploy.py
```

### Register a user

You can register users using the FastAPI endpoint provided. You'll need to have your admin authentication token ready.

```bash
curl -X POST "https://yourusername--pypiserver-register-user.modal.run" \
  -H "Authorization: Bearer your-admin-token" \
  -d '{"username": "newuser", "password": "securepassword"}'
```

### Configure pip to use your PyPI server

Add the following to your `~/.pip/pip.conf` file:

```ini
[global]
index-url = https://your-modal-url.modal.run/simple
# Replace 'yourusername' with your actual Modal username
# This should be the URL of your Modal endpoint + '/simple'
extra-index-url = https://pypi.org/simple
```

## Documentation

For a deeper understanding of how this PyPI server works:

- [Detailed explanation of the deployment script and CI/CD pipeline](pypi_deploy_explanation.md)
- [API reference](api.md)

## Why this project exists

This project exists to provide a simple, serverless solution for hosting private Python packages. It leverages Modal's infrastructure to:

- Avoid the need to manage your own server
- Provide persistent storage for packages and user credentials
- Offer a quick way to set up a private PyPI server
- Enable secure package distribution within teams and organizations
