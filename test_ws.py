import asyncio
import websockets
import httpx

async def test():
    # create guest
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        res = await client.post("/api/v1/auth/guest")
        token = res.json()["access_token"]
        
        # force a session
        await client.post("/api/v1/matchmaking/join", json={"room_id": "0f090db4-7f82-4c06-8fdf-abbc9c6f6373", "mode": "QUICK"}, headers={"Authorization": f"Bearer {token}"})
        # wait a bit, since no opponent it won't match, so we can't test session WS directly unless we mock it or get one
        
        # let's just connect to a fake session to see if we get 1008 or 403
        try:
            async with websockets.connect(f"ws://localhost:8000/api/v1/sessions/fake-id/ws?token={token}") as ws:
                pass
        except Exception as e:
            print("WS Exception:", e)

asyncio.run(test())
