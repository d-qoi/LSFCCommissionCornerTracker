from pydantic import BaseModel

from fastapi import FastAPI

app = FastAPI()

class Test1(BaseModel):
    a: str

class Test2(BaseModel):
    asdf: str

@app.get("/${t}")
async def test(t: int)-> Test1 | Test2:
    if t > 3:
        return Test1(a="a")
    return Test2(asdf="asdf")
