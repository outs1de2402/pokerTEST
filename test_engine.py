"""Перевірка рушія: симуляція роздач тільки з ботами, фішки не мають зникати чи зʼявлятись."""
import asyncio, random, engine
engine.SPEED = 0
async def main():
    for n in range(2, 10):
        t = engine.Table('T', 'x', 1000, 0); t.P = [engine.player(f'b{i}') for i in range(n)]
        for p in t.P: p.chips = 1000
        for h in range(120):
            if sum(p.chips > 0 for p in t.P) < 2: break
            await t.hand()
            assert sum(p.chips for p in t.P) == 1000 * n, (n, h)
            for p in t.P: p.total = 0
    print('OK')
asyncio.run(main())
