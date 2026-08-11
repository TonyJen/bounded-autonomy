from fastapi import Header, HTTPException


def make_device_auth(expected_token: str):
    async def device_auth(x_device_token: str = Header(default="")):
        if x_device_token != expected_token:
            raise HTTPException(status_code=401, detail="bad device token")
    return device_auth
