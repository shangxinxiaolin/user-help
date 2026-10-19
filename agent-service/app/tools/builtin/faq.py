FAQS = [
    {
        "question": "运费怎么计算？",
        "answer": "全场实付满 99 元包邮，不足 99 元收取 8 元运费。新疆、西藏等偏远地区按实际包裹重量收取首重 15 元运费。",
        "keywords": ["运费", "包邮", "邮费", "配送费"],
    },
    {
        "question": "发货时间是多久？",
        "answer": "正常订单支付成功后 48 小时内发货；预售商品以商品详情页标注的发货时间为准。",
        "keywords": ["发货", "发货时间", "什么时候发货"],
    },
    {
        "question": "支持七天无理由退货吗？",
        "answer": "支持。在商品签收之日起 7 天内，商品保持完好、配件齐全、未经使用且不影响二次销售的前提下，可申请七天无理由退货。",
        "keywords": ["无理由退货", "7天", "七天", "退货条件"],
    },
    {
        "question": "怎么开具发票？",
        "answer": "订单确认收货后，可在「我的订单-申请开票」中选择开具增值税电子普通发票或专用发票，开票将在 1-3 个工作日内发送到您的电子邮箱。",
        "keywords": ["发票", "开票", "普票", "专票"],
    },
    {
        "question": "商品保修期多久？",
        "answer": "电子数码类商品享受国家三包服务，自签收之日起提供 1 年全国联保；配件类提供 6 个月质保。",
        "keywords": ["保修", "质保", "保修期", "三包"],
    },
]


async def query_faq_fn(keyword: str) -> list[dict]:
    kw = (keyword or "").strip().lower()
    if not kw:
        return FAQS[:3]

    matched = []
    for item in FAQS:
        if any(k in kw or kw in k for k in item["keywords"]) or kw in item["question"].lower() or kw in item["answer"].lower():
            matched.append(item)

    return matched if matched else [{"question": "无完全匹配FAQ", "answer": f"未找到关于「{keyword}」的常见问题，您可以转人工咨询。"}]
