package com.shangui.userhelp.order.service;

import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.order.mapper.MockOrderMapper;
import com.shangui.userhelp.order.service.impl.OrderServiceImpl;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class OrderServiceTest {

    private final OrderService orderService = new OrderServiceImpl(new MockOrderMapper());

    @Test
    void demoOrderCanBeQueriedByAnyUser() {
        var order = orderService.query("u1", "1001");

        assertEquals("1001", order.orderId());
        assertEquals("u1", order.userId());
        assertNotNull(order.trackingNo());
    }

    @Test
    void missingUserIsRejected() {
        BusinessException exception = assertThrows(BusinessException.class,
                () -> orderService.query("", "1001"));

        assertEquals(400, exception.getCode());
    }

    @Test
    void userOrdersAreOwnedByTheRequestedUser() {
        var orders = orderService.list("u1");

        assertEquals(4, orders.size());
        orders.forEach(order -> assertEquals("u1", order.userId()));
    }
}
