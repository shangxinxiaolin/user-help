from typing import Any

from app.core.retrieval import hybrid_search

DEFAULT_KNOWLEDGE_CHUNKS = [
    {
        "id": 1,
        "title": "七天无理由退货政策",
        "category": "退换货",
        "is_key_clause": True,
        "content": "自签收次日起 7 天内，在商品完好、包装及配件齐全、未激活使用且不影响二次销售的情况下，可申请七天无理由退换货。已拆封贴身衣物及定制商品不支持无理由退货。",
    },
    {
        "id": 2,
        "title": "退款审核与到账时效",
        "category": "退换货",
        "is_key_clause": True,
        "content": "未发货订单申请退款后系统自动极速退款；已发货订单需拦截物流或退货寄回，仓库验货无误后 24 小时内原路退回支付账户，微信/支付宝 1-3 个工作日到账，银行卡 3-5 个工作日到账。",
    },
    {
        "id": 3,
        "title": "商城配送与运费标准",
        "category": "物流",
        "is_key_clause": True,
        "content": "全场订单实付满 99 元享受包邮服务；不足 99 元收取基础运费 8 元。新疆、西藏、青海、内蒙古等偏远地区按包裹重量收取首重 15 元运费，续重 8 元/kg。",
    },
    {
        "id": 4,
        "title": "发货时效说明",
        "category": "物流",
        "is_key_clause": False,
        "content": "现货商品在支付成功后 48 小时内发出，大促活动期间 72 小时内发货。预售商品发货时间以商品详情页承诺的预计发货日期为准。",
    },
    {
        "id": 5,
        "title": "全国联保与三包政策",
        "category": "售后",
        "is_key_clause": True,
        "content": "电子数码类商品严格执行国家三包政策：签收 7 天内出现非人为性能故障包退，15 天内包换，1 年内免费保修。配件类提供 6 个月质保服务。",
    },
    {
        "id": 6,
        "title": "发票开具与修改规范",
        "category": "发票",
        "is_key_clause": False,
        "content": "订单确认收货后可在订单详情页面自助申请开具增值税电子普通发票或专用发票。电子发票将在申请后 1-3 个工作日开出并发送至用户预留邮箱。",
    },
]


class KnowledgeStore:
    def __init__(self, repository: Any | None = None) -> None:
        self._repository = repository
        self._chunks: list[dict] = list(DEFAULT_KNOWLEDGE_CHUNKS)

    async def initialize(self) -> None:
        if self._repository is not None:
            try:
                db_chunks = await self._repository.list_chunks(limit=500)
                if db_chunks:
                    self._chunks = [
                        {
                            "id": c.id,
                            "title": c.title,
                            "content": c.content,
                            "category": c.category,
                            "is_key_clause": c.is_key_clause,
                        }
                        for c in db_chunks
                    ]
                else:
                    # Seed default chunks into repository
                    for dc in DEFAULT_KNOWLEDGE_CHUNKS:
                        await self._repository.add_chunk(
                            title=dc["title"],
                            content=dc["content"],
                            category=dc["category"],
                            is_key_clause=dc["is_key_clause"],
                            source="seed",
                        )
            except Exception:
                pass

    async def search(self, query: str, top_k: int = 4) -> list[dict]:
        return hybrid_search(query, self._chunks, top_k=top_k)

    def list_all(self) -> list[dict]:
        return list(self._chunks)

    def add_chunk(self, chunk: dict) -> None:
        self._chunks.append(chunk)


default_kb_store = KnowledgeStore()
