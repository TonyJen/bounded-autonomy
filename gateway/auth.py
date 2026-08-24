import hmac

from fastapi import Header, HTTPException, Query, Request

# In-process test client counts as local: it never traverses a network.
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def make_device_auth(expected_token: str):
    async def device_auth(x_device_token: str = Header(default="")):
        if not hmac.compare_digest(x_device_token, expected_token):
            raise HTTPException(status_code=401, detail="bad device token")
    return device_auth


def make_operator_auth(expected_token: str):
    """Operator endpoints (status/history/sim/evals/ws) serve the dashboard.
    Loopback clients are always allowed — the local demo must work
    zero-config. Remote clients (LAN, cloudflared tunnel) need
    OPERATOR_TOKEN; with the token unset, remote access is denied outright
    so a published repo can never ship an open control surface."""
    async def operator_auth(request: Request,
                            x_operator_token: str = Header(default=""),
                            token: str = Query(default="")):
        host = request.client.host if request.client else ""
        if host in _LOCAL_HOSTS:
            return
        presented = x_operator_token or token
        if expected_token and hmac.compare_digest(presented, expected_token):
            return
        raise HTTPException(status_code=403,
                            detail="operator token required for remote access")
    return operator_auth
