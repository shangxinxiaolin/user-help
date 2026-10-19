package com.shangui.userhelp.common.error;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RpcErrorMapperTest {

    @Test
    void mapOrderErrors() {
        assertEquals("ORDER_NOT_FOUND", RpcErrorMapper.mapOrderError(new BusinessException(ErrorCode.NOT_FOUND, "not found")));
        assertEquals("ORDER_NOT_OWNED", RpcErrorMapper.mapOrderError(new BusinessException(ErrorCode.FORBIDDEN, "forbidden")));
        assertEquals("INVALID_ARGUMENT", RpcErrorMapper.mapOrderError(new BusinessException(ErrorCode.BAD_REQUEST, "bad request")));
        assertEquals("INTERNAL_ERROR", RpcErrorMapper.mapOrderError(new RuntimeException("crash")));
    }

    @Test
    void mapRefundErrors() {
        assertEquals("REFUND_NOT_ALLOWED", RpcErrorMapper.mapRefundError(new BusinessException(ErrorCode.BAD_REQUEST, "当前订单状态不允许退款")));
        assertEquals("IDEMPOTENCY_KEY_REQUIRED", RpcErrorMapper.mapRefundError(new BusinessException(ErrorCode.BAD_REQUEST, "idempotency_key 不能为空")));
        assertEquals("ORDER_NOT_FOUND", RpcErrorMapper.mapRefundError(new BusinessException(ErrorCode.NOT_FOUND, "not found")));
        assertEquals("INTERNAL_ERROR", RpcErrorMapper.mapRefundError(new RuntimeException("crash")));
    }

    @Test
    void mapTicketAndGenericErrors() {
        assertEquals("INVALID_ARGUMENT", RpcErrorMapper.mapTicketError(new BusinessException(ErrorCode.BAD_REQUEST, "工单参数不完整")));
        assertEquals("NOT_FOUND", RpcErrorMapper.mapGenericError(new BusinessException(ErrorCode.NOT_FOUND, "not found")));
        assertEquals("INTERNAL_ERROR", RpcErrorMapper.mapTicketError(new RuntimeException("crash")));
    }
}
