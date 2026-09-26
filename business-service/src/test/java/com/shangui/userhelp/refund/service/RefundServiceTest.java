package com.shangui.userhelp.refund.service;

import com.shangui.userhelp.order.mapper.MockOrderMapper;
import com.shangui.userhelp.order.service.OrderService;
import com.shangui.userhelp.order.service.impl.OrderServiceImpl;
import com.shangui.userhelp.refund.mapper.MockRefundMapper;
import com.shangui.userhelp.refund.service.impl.RefundServiceImpl;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

class RefundServiceTest {

    private final RefundService refundService = new RefundServiceImpl(
            new OrderServiceImpl(new MockOrderMapper()), new MockRefundMapper());

    @Test
    void sameIdempotencyKeyReturnsTheSameRefund() {
        var orderService = new OrderServiceImpl(new MockOrderMapper());
        String orderId = orderService.list("u1").stream()
                .filter(order -> !"待付款".equals(order.status()) && !"已签收".equals(order.status()))
                .map(order -> order.orderId())
                .findFirst()
                .orElseThrow();

        var first = refundService.submit("u1", orderId, "不想要了", "conv-1-tool-1");
        var second = refundService.submit("u1", orderId, "不想要了", "conv-1-tool-1");

        assertSame(first, second);
        assertEquals(first.refundId(), second.refundId());
    }
}
