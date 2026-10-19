class BusinessRpcError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.error_code = error_code
        self.message = message


class OrderNotFoundError(BusinessRpcError):
    pass


class OrderNotOwnedError(BusinessRpcError):
    pass


class RefundNotAllowedError(BusinessRpcError):
    pass


class IdempotencyKeyRequiredError(BusinessRpcError):
    pass


class RpcTimeoutError(BusinessRpcError):
    def __init__(self, message: str = "业务服务调用超时") -> None:
        super().__init__("RPC_TIMEOUT", message)


class RpcUnavailableError(BusinessRpcError):
    def __init__(self, message: str = "业务服务暂不可用") -> None:
        super().__init__("RPC_UNAVAILABLE", message)


def raise_for_business_error(error_code: str, message: str) -> None:
    if error_code == "ORDER_NOT_FOUND":
        raise OrderNotFoundError(error_code, message)
    elif error_code == "ORDER_NOT_OWNED":
        raise OrderNotOwnedError(error_code, message)
    elif error_code == "REFUND_NOT_ALLOWED":
        raise RefundNotAllowedError(error_code, message)
    elif error_code == "IDEMPOTENCY_KEY_REQUIRED":
        raise IdempotencyKeyRequiredError(error_code, message)
    else:
        raise BusinessRpcError(error_code, message)
